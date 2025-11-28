"""
kcpwd.ui.sharing - Password sharing module
Complete implementation with models, manager, and API endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from enum import Enum
from fastapi import HTTPException, Request
import secrets
import hashlib
import threading
import time


# ============= Models =============

class ShareDuration(str, Enum):
    """Available share durations"""
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    THREE_HOURS = "3h"


class ShareAccessType(str, Enum):
    """Access control types"""
    ANYONE = "anyone"  # Anyone with link
    ONCE = "once"  # Only one access
    PASSWORD = "password"  # Require password


class ShareCreate(BaseModel):
    """Request to create a share"""
    key: str = Field(..., min_length=1, description="Password key to share")
    duration: ShareDuration = Field(ShareDuration.ONE_HOUR, description="How long the share is valid")
    access_type: ShareAccessType = Field(ShareAccessType.ANYONE, description="Access control")
    access_password: Optional[str] = Field(None, description="Password to access (if access_type=password)")
    max_views: Optional[int] = Field(None, ge=1, le=100, description="Maximum number of views")
    require_master: bool = Field(False, description="Does this password need master password?")
    master_password: Optional[str] = Field(None, description="Master password if needed")

    @validator('access_password')
    def validate_access_password(cls, v, values):
        if values.get('access_type') == ShareAccessType.PASSWORD and not v:
            raise ValueError('Access password required when access_type is password')
        return v


class ShareAccess(BaseModel):
    """Request to access a shared password"""
    access_password: Optional[str] = None


# ============= Data Structure =============

class SharedPassword:
    """Shared password data structure"""

    def __init__(
            self,
            share_id: str,
            password: str,
            key_name: str,
            created_at: datetime,
            expires_at: datetime,
            access_type: ShareAccessType,
            access_password_hash: Optional[str] = None,
            max_views: Optional[int] = None,
            creator_ip: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ):
        self.share_id = share_id
        self.password = password
        self.key_name = key_name
        self.created_at = created_at
        self.expires_at = expires_at
        self.access_type = access_type
        self.access_password_hash = access_password_hash
        self.max_views = max_views
        self.view_count = 0
        self.creator_ip = creator_ip
        self.metadata = metadata or {}
        self.access_log: list = []

    def is_expired(self) -> bool:
        """Check if share has expired"""
        return datetime.now() >= self.expires_at

    def can_access(self) -> bool:
        """Check if share can be accessed"""
        if self.is_expired():
            return False

        if self.access_type == ShareAccessType.ONCE and self.view_count >= 1:
            return False

        if self.max_views and self.view_count >= self.max_views:
            return False

        return True

    def verify_access_password(self, password: str) -> bool:
        """Verify access password if required"""
        if self.access_type != ShareAccessType.PASSWORD:
            return True

        if not self.access_password_hash:
            return False

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.access_password_hash

    def record_access(self, ip: str, user_agent: Optional[str] = None):
        """Record an access to this share"""
        self.view_count += 1
        self.access_log.append({
            'timestamp': datetime.now().isoformat(),
            'ip': ip,
            'user_agent': user_agent,
            'view_number': self.view_count
        })

    def to_dict(self, include_password: bool = False) -> dict:
        """Convert to dictionary"""
        result = {
            'share_id': self.share_id,
            'key_name': self.key_name,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'access_type': self.access_type.value,
            'max_views': self.max_views,
            'view_count': self.view_count,
            'is_expired': self.is_expired(),
            'can_access': self.can_access(),
            'creator_ip': self.creator_ip,
            'time_remaining': str(self.expires_at - datetime.now()) if not self.is_expired() else "expired"
        }

        if include_password:
            result['password'] = self.password

        return result


# ============= Manager =============

class ShareManager:
    """Manager for shared passwords with automatic cleanup"""

    def __init__(self):
        self._shares: Dict[str, SharedPassword] = {}
        self._lock = threading.Lock()
        self._cleanup_thread = None
        self._running = False

    def start(self):
        """Start automatic cleanup thread"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        print("🔗 Share manager started with auto-cleanup")

    def stop(self):
        """Stop cleanup thread"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def _cleanup_loop(self):
        """Background cleanup of expired shares"""
        while self._running:
            try:
                self.cleanup_expired()
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Cleanup error: {e}")

    def cleanup_expired(self):
        """Remove expired shares"""
        with self._lock:
            expired = [
                share_id for share_id, share in self._shares.items()
                if share.is_expired() or not share.can_access()
            ]

            for share_id in expired:
                del self._shares[share_id]

            if expired:
                print(f"🧹 Cleaned up {len(expired)} expired shares")

    def add_share(self, share: SharedPassword) -> str:
        """Add a new share"""
        with self._lock:
            self._shares[share.share_id] = share
        return share.share_id

    def get_share(self, share_id: str) -> Optional[SharedPassword]:
        """Get a share by ID"""
        with self._lock:
            return self._shares.get(share_id)

    def remove_share(self, share_id: str) -> bool:
        """Remove a share"""
        with self._lock:
            if share_id in self._shares:
                del self._shares[share_id]
                return True
        return False

    def list_active_shares(self) -> List[dict]:
        """List all active shares (without passwords)"""
        with self._lock:
            return [
                share.to_dict(include_password=False)
                for share in self._shares.values()
                if not share.is_expired()
            ]

    def get_stats(self) -> dict:
        """Get statistics"""
        with self._lock:
            total = len(self._shares)
            expired = sum(1 for s in self._shares.values() if s.is_expired())
            active = total - expired

            total_views = sum(s.view_count for s in self._shares.values())

            by_type = {}
            for share in self._shares.values():
                share_type = share.access_type.value
                by_type[share_type] = by_type.get(share_type, 0) + 1

            return {
                'total_shares': total,
                'active_shares': active,
                'expired_shares': expired,
                'total_views': total_views,
                'by_access_type': by_type
            }


# ============= Utilities =============

def generate_share_id() -> str:
    """Generate a unique share ID"""
    return secrets.token_urlsafe(16)


def hash_password(password: str) -> str:
    """Hash password for access control"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_duration_timedelta(duration: ShareDuration) -> timedelta:
    """Convert ShareDuration to timedelta"""
    duration_map = {
        ShareDuration.FIVE_MINUTES: timedelta(minutes=5),
        ShareDuration.FIFTEEN_MINUTES: timedelta(minutes=15),
        ShareDuration.THIRTY_MINUTES: timedelta(minutes=30),
        ShareDuration.ONE_HOUR: timedelta(hours=1),
        ShareDuration.THREE_HOURS: timedelta(hours=3),
    }
    return duration_map[duration]


def get_client_ip(request: Request) -> str:
    """Get client IP from request"""
    # Check X-Forwarded-For header (for proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection
    if request.client:
        return request.client.host

    return "unknown"


# Global instance
_share_manager: Optional[ShareManager] = None


def get_share_manager() -> ShareManager:
    """Get or create global share manager"""
    global _share_manager
    if _share_manager is None:
        _share_manager = ShareManager()
        _share_manager.start()
    return _share_manager