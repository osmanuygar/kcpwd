"""
kcpwd.ui.api - Web UI Backend
FastAPI-based REST API for password management
UPDATED: Now includes password sharing functionality
"""

from fastapi import FastAPI, HTTPException, Depends, Security, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uvicorn
import secrets
import os
from pathlib import Path

from ..core import (
    set_password, get_password, delete_password,
    list_all_keys, generate_password, export_passwords,
    import_passwords, get_backend_info
)
from ..strength import check_password_strength, PasswordStrength
from ..master_protection import (
    set_master_password, get_master_password,
    list_master_keys, has_master_password
)
from ..platform_utils import check_platform_requirements
from .config import UIConfig

# Import sharing functionality
try:
    from .sharing import (
        ShareCreate, ShareAccess, SharedPassword, ShareDuration,
        ShareAccessType, generate_share_id, hash_password,
        get_duration_timedelta, get_share_manager, get_client_ip
    )
    SHARING_ENABLED = True
except ImportError:
    SHARING_ENABLED = False
    print("⚠️ Sharing module not available")

# ============= Security =============

security = HTTPBearer()

# Session management (in-memory for now, use Redis in production)
_sessions: Dict[str, Dict[str, Any]] = {}

# Store the UI secret globally (generated once on startup)
_ui_secret: Optional[str] = None

def cleanup_expired_sessions():
    """Remove expired sessions"""
    now = datetime.now()
    expired = [
        token for token, data in _sessions.items()
        if data['expires'] < now
    ]
    for token in expired:
        del _sessions[token]

def create_session() -> str:
    """Create new session token"""
    cleanup_expired_sessions()

    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        'created': datetime.now(),
        'expires': datetime.now() + timedelta(seconds=UIConfig.SESSION_TIMEOUT),
        'last_activity': datetime.now()
    }
    return token

def verify_session(token: str) -> bool:
    """Verify session token is valid"""
    cleanup_expired_sessions()

    if token not in _sessions:
        return False

    # Update last activity
    _sessions[token]['last_activity'] = datetime.now()
    return True


# ============= FastAPI App =============

app = FastAPI(
    title="kcpwd Web UI",
    description="Password Manager Web Interface with Sharing",
    version="0.8.1",
    docs_url="/api/docs" if UIConfig.DEBUG else None,
    redoc_url="/api/redoc" if UIConfig.DEBUG else None,
)

# CORS (if enabled)
if UIConfig.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=UIConfig.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Static files
UI_DIR = Path(__file__).parent / "static"
if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


# ============= Models =============

class PasswordCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    use_master: bool = False
    master_password: Optional[str] = None

    @validator('key')
    def validate_key(cls, v):
        # No special chars that might cause issues
        if any(c in v for c in ['\n', '\r', '\t', '\0']):
            raise ValueError('Key contains invalid characters')
        return v.strip()

class PasswordGet(BaseModel):
    key: str
    use_master: bool = False
    master_password: Optional[str] = None

class PasswordUpdate(BaseModel):
    new_password: str = Field(..., min_length=1)
    use_master: bool = False
    master_password: Optional[str] = None

class GenerateRequest(BaseModel):
    length: int = Field(16, ge=4, le=128)
    use_uppercase: bool = True
    use_lowercase: bool = True
    use_digits: bool = True
    use_symbols: bool = True
    exclude_ambiguous: bool = False
    save_as: Optional[str] = None
    use_master: bool = False
    master_password: Optional[str] = None

class AuthRequest(BaseModel):
    secret: str = Field(..., min_length=1)

class ExportRequest(BaseModel):
    include_passwords: bool = True

class ImportRequest(BaseModel):
    data: dict
    overwrite: bool = False


# ============= Auth Dependency =============

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify session token"""
    token = credentials.credentials

    if not verify_session(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    return token


# ============= Error Handlers =============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global error handler"""
    if UIConfig.DEBUG:
        import traceback
        detail = {
            "error": str(exc),
            "traceback": traceback.format_exc()
        }
    else:
        detail = {"error": "Internal server error"}

    return JSONResponse(
        status_code=500,
        content=detail
    )


# ============= Routes =============

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main UI"""
    index_file = UI_DIR / "index.html"

    if not index_file.exists():
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>kcpwd UI - Setup Required</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 50px;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    max-width: 600px;
                }
                h1 { color: #667eea; }
                code {
                    background: #f5f5f5;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-family: monospace;
                }
                .warning {
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 kcpwd Web UI</h1>
                <div class="warning">
                    <strong>⚠️ UI Files Not Found</strong>
                    <p>The static UI files are missing.</p>
                </div>
                <p>This might happen if you installed kcpwd from source without UI files.</p>
                <p><strong>Solution:</strong></p>
                <ol>
                    <li>Make sure UI files are in: <code>kcpwd/ui/static/</code></li>
                    <li>Or reinstall: <code>pip install --upgrade kcpwd[ui]</code></li>
                </ol>
            </div>
        </body>
        </html>
        """)

    return FileResponse(index_file)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.8.0",
        "sharing_enabled": SHARING_ENABLED,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/debug")
async def debug_info():
    """Debug information (only in debug mode)"""
    if not UIConfig.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    info = {
        "secret_set": _ui_secret is not None,
        "secret_length": len(_ui_secret) if _ui_secret else 0,
        "active_sessions": len(_sessions),
        "sharing_enabled": SHARING_ENABLED,
        "config": {
            "HOST": UIConfig.HOST,
            "PORT": UIConfig.PORT,
            "DEBUG": UIConfig.DEBUG,
            "SECRET_ENV_SET": UIConfig.SECRET is not None
        }
    }

    if SHARING_ENABLED:
        try:
            manager = get_share_manager()
            info["share_stats"] = manager.get_stats()
        except:
            pass

    return info


@app.post("/api/auth")
async def authenticate(auth: AuthRequest):
    """Authenticate and create session"""
    global _ui_secret

    # Get or generate secret
    if _ui_secret is None:
        _ui_secret = UIConfig.get_secret()

    if auth.secret != _ui_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret"
        )

    token = create_session()

    return {
        "token": token,
        "expires_in": UIConfig.SESSION_TIMEOUT,
        "message": "Authenticated successfully"
    }


@app.post("/api/logout")
async def logout(token: str = Depends(verify_token)):
    """Logout and destroy session"""
    if token in _sessions:
        del _sessions[token]

    return {"message": "Logged out successfully"}


@app.get("/api/info")
async def get_info(token: str = Depends(verify_token)):
    """Get platform and backend info"""
    platform_info = check_platform_requirements()
    backend_info = get_backend_info()

    return {
        "platform": {
            "name": platform_info['platform_name'],
            "supported": platform_info['supported'],
            "clipboard": platform_info['clipboard_available'],
            "clipboard_tool": platform_info.get('clipboard_tool')
        },
        "backend": {
            "type": backend_info['type'],
            "name": backend_info.get('name'),
            "description": backend_info.get('description')
        },
        "session": {
            "active_sessions": len(_sessions),
            "timeout": UIConfig.SESSION_TIMEOUT
        },
        "features": {
            "sharing": SHARING_ENABLED
        }
    }


@app.get("/api/passwords")
async def list_passwords(token: str = Depends(verify_token)):
    """List all password keys"""
    try:
        regular_keys = list_all_keys()
        master_keys = list_master_keys()

        return {
            "regular": sorted(regular_keys),
            "master_protected": sorted(master_keys),
            "total": len(regular_keys) + len(master_keys),
            "counts": {
                "regular": len(regular_keys),
                "master": len(master_keys)
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to list passwords: {str(e)}")


@app.post("/api/passwords")
async def create_password(data: PasswordCreate, token: str = Depends(verify_token)):
    """Store a new password"""
    try:
        # Check if already exists
        existing = get_password(data.key)
        if existing:
            raise HTTPException(400, f"Password '{data.key}' already exists")

        if data.use_master:
            if not data.master_password:
                raise HTTPException(400, "Master password required")

            if len(data.master_password) < 8:
                raise HTTPException(400, "Master password must be at least 8 characters")

            success = set_master_password(
                data.key,
                data.password,
                data.master_password
            )
        else:
            success = set_password(data.key, data.password)

        if not success:
            raise HTTPException(500, "Failed to store password")

        # Get strength
        strength = check_password_strength(data.password)

        return {
            "success": True,
            "key": data.key,
            "master_protected": data.use_master,
            "strength": {
                "score": strength['score'],
                "level": strength['strength_text']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/api/passwords/retrieve")
async def retrieve_password(data: PasswordGet, token: str = Depends(verify_token)):
    """Retrieve a password"""
    try:
        if data.use_master or has_master_password(data.key):
            if not data.master_password:
                raise HTTPException(400, "Master password required")

            password = get_master_password(data.key, data.master_password)
        else:
            password = get_password(data.key)

        if password is None:
            raise HTTPException(404, "Password not found or incorrect master password")

        return {
            "key": data.key,
            "password": password,
            "master_protected": has_master_password(data.key)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.put("/api/passwords/{key}")
async def update_password(
    key: str,
    data: PasswordUpdate,
    token: str = Depends(verify_token)
):
    """Update an existing password"""
    try:
        # Delete old
        if has_master_password(key):
            from ..master_protection import delete_master_password
            delete_master_password(key)
        else:
            if not delete_password(key):
                raise HTTPException(404, "Password not found")

        # Set new
        if data.use_master:
            if not data.master_password:
                raise HTTPException(400, "Master password required")

            success = set_master_password(key, data.new_password, data.master_password)
        else:
            success = set_password(key, data.new_password)

        if not success:
            raise HTTPException(500, "Failed to update password")

        return {"success": True, "key": key, "message": "Password updated"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/api/passwords/{key}")
async def remove_password(key: str, token: str = Depends(verify_token)):
    """Delete a password"""
    try:
        is_master = has_master_password(key)

        if is_master:
            from ..master_protection import delete_master_password
            success = delete_master_password(key)
        else:
            success = delete_password(key)

        if not success:
            raise HTTPException(404, "Password not found")

        return {
            "success": True,
            "deleted": key,
            "was_master_protected": is_master
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/generate")
async def generate_new_password(data: GenerateRequest, token: str = Depends(verify_token)):
    """Generate a random password"""
    try:
        password = generate_password(
            length=data.length,
            use_uppercase=data.use_uppercase,
            use_lowercase=data.use_lowercase,
            use_digits=data.use_digits,
            use_symbols=data.use_symbols,
            exclude_ambiguous=data.exclude_ambiguous
        )

        # Check strength
        strength = check_password_strength(password)

        # Optionally save
        saved = False
        if data.save_as:
            if data.use_master:
                if not data.master_password:
                    raise HTTPException(400, "Master password required for saving")
                success = set_master_password(data.save_as, password, data.master_password)
            else:
                success = set_password(data.save_as, password)

            saved = success

        return {
            "password": password,
            "length": len(password),
            "strength": {
                "score": strength['score'],
                "level": strength['strength_text'],
                "feedback": strength['feedback']
            },
            "saved": saved,
            "saved_as": data.save_as if saved else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/check-strength")
async def check_strength(password: str, token: str = Depends(verify_token)):
    """Check password strength"""
    result = check_password_strength(password)
    return {
        "score": result['score'],
        "strength": result['strength_text'],
        "feedback": result['feedback'],
        "details": result['details']
    }


@app.get("/api/export")
async def export_data(
    include_passwords: bool = True,
    token: str = Depends(verify_token)
):
    """Export passwords (returns JSON)"""
    try:
        import tempfile
        import json

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        # Export
        result = export_passwords(temp_path, include_passwords=include_passwords)

        if not result['success']:
            raise HTTPException(500, result['message'])

        # Read and return
        with open(temp_path, 'r') as f:
            data = json.load(f)

        # Cleanup
        os.unlink(temp_path)

        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/import")
async def import_data(
    data: ImportRequest,
    token: str = Depends(verify_token)
):
    """Import passwords from JSON data"""
    try:
        import tempfile
        import json

        # Create temp file with import data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data.data, f)
            temp_path = f.name

        # Import
        result = import_passwords(temp_path, overwrite=data.overwrite, dry_run=False)

        # Cleanup
        os.unlink(temp_path)

        if not result['success']:
            raise HTTPException(400, result['message'])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/stats")
async def get_statistics(token: str = Depends(verify_token)):
    """Get statistics about stored passwords"""
    try:
        regular = list_all_keys()
        master = list_master_keys()

        return {
            "total": len(regular) + len(master),
            "regular": len(regular),
            "master_protected": len(master),
            "backend": get_backend_info()['type']
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ============= Password Sharing Endpoints =============

if SHARING_ENABLED:

    @app.post("/api/share/create")
    async def create_share(
        data: ShareCreate,
        request: Request,
        token: str = Depends(verify_token)
    ):
        """Create a shareable link for a password"""
        try:
            # Get the password
            if data.require_master or has_master_password(data.key):
                if not data.master_password:
                    raise HTTPException(400, "Master password required")
                password = get_master_password(data.key, data.master_password)
            else:
                password = get_password(data.key)

            if not password:
                raise HTTPException(404, f"Password '{data.key}' not found")

            # Create share
            share_id = generate_share_id()
            now = datetime.now()
            expires_at = now + get_duration_timedelta(data.duration)

            # Hash access password if provided
            access_password_hash = None
            if data.access_type == ShareAccessType.PASSWORD and data.access_password:
                access_password_hash = hash_password(data.access_password)

            # Get client IP
            client_ip = get_client_ip(request)

            # Create shared password object
            shared_password = SharedPassword(
                share_id=share_id,
                password=password,
                key_name=data.key,
                created_at=now,
                expires_at=expires_at,
                access_type=data.access_type,
                access_password_hash=access_password_hash,
                max_views=data.max_views if data.access_type != ShareAccessType.ONCE else 1,
                creator_ip=client_ip,
                metadata={
                    'original_key': data.key,
                    'duration': data.duration.value,
                    'has_master': data.require_master
                }
            )

            # Add to manager
            manager = get_share_manager()
            manager.add_share(shared_password)

            # Build URL
            base_url = str(request.base_url).rstrip('/')
            share_url = f"{base_url}/s/{share_id}"

            return {
                "success": True,
                "share_id": share_id,
                "share_url": share_url,
                "expires_at": expires_at.isoformat(),
                "access_type": data.access_type.value,
                "max_views": shared_password.max_views,
                "duration": data.duration.value,
                "message": f"Share created successfully. Valid for {data.duration.value}"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to create share: {str(e)}")


    @app.get("/api/share/{share_id}")
    async def get_share_info(share_id: str, request: Request):
        """Get information about a share (without the password)"""
        try:
            manager = get_share_manager()
            share = manager.get_share(share_id)

            if not share:
                raise HTTPException(404, "Share not found or expired")

            if not share.can_access():
                raise HTTPException(410, "Share has expired or reached maximum views")

            return {
                "exists": True,
                "key_name": share.key_name,
                "created_at": share.created_at.isoformat(),
                "expires_at": share.expires_at.isoformat(),
                "access_type": share.access_type.value,
                "requires_password": share.access_type.value == "password",
                "view_count": share.view_count,
                "max_views": share.max_views,
                "time_remaining": str(share.expires_at - datetime.now())
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))


    @app.post("/api/share/{share_id}/access")
    async def access_share(
        share_id: str,
        data: ShareAccess,
        request: Request
    ):
        """Access a shared password"""
        try:
            manager = get_share_manager()
            share = manager.get_share(share_id)

            if not share:
                raise HTTPException(404, "Share not found or expired")

            if not share.can_access():
                # Auto-delete if expired or max views reached
                manager.remove_share(share_id)
                raise HTTPException(410, "Share has expired or reached maximum views")

            # Verify access password if required
            if share.access_type == ShareAccessType.PASSWORD:
                if not data.access_password:
                    raise HTTPException(401, "Access password required")

                if not share.verify_access_password(data.access_password):
                    raise HTTPException(401, "Incorrect access password")

            # Record access
            client_ip = get_client_ip(request)
            user_agent = request.headers.get("User-Agent", "Unknown")
            share.record_access(client_ip, user_agent)

            # Get the password
            password = share.password

            # Auto-delete if "once" type or max views reached
            if share.access_type == ShareAccessType.ONCE or (share.max_views and share.view_count >= share.max_views):
                manager.remove_share(share_id)

            return {
                "success": True,
                "password": password,
                "key_name": share.key_name,
                "view_count": share.view_count,
                "remaining_views": share.max_views - share.view_count if share.max_views else None,
                "expires_at": share.expires_at.isoformat(),
                "message": "Password retrieved successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))


    @app.delete("/api/share/{share_id}")
    async def delete_share(share_id: str, token: str = Depends(verify_token)):
        """Delete a share (creator only)"""
        try:
            manager = get_share_manager()
            success = manager.remove_share(share_id)

            if not success:
                raise HTTPException(404, "Share not found")

            return {
                "success": True,
                "message": "Share deleted successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))


    @app.get("/api/shares")
    async def list_shares(token: str = Depends(verify_token)):
        """List all active shares (authenticated users only)"""
        try:
            manager = get_share_manager()
            shares = manager.list_active_shares()

            return {
                "shares": shares,
                "count": len(shares)
            }

        except Exception as e:
            raise HTTPException(500, str(e))


    @app.get("/api/shares/stats")
    async def get_share_stats(token: str = Depends(verify_token)):
        """Get sharing statistics"""
        try:
            manager = get_share_manager()
            stats = manager.get_stats()

            return stats

        except Exception as e:
            raise HTTPException(500, str(e))


    # ============= Share Access Page (Public) =============

    @app.get("/s/{share_id}", response_class=HTMLResponse)
    async def share_access_page(share_id: str, request: Request):
        """Public share access page"""
        try:
            manager = get_share_manager()
            share = manager.get_share(share_id)

            if not share or not share.can_access():
                return HTMLResponse("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Share Not Found - kcpwd</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .container {
                            background: white;
                            padding: 50px;
                            border-radius: 12px;
                            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                            max-width: 500px;
                            text-align: center;
                        }
                        h1 { color: #ef4444; margin-bottom: 20px; }
                        p { color: #666; line-height: 1.6; }
                        .icon { font-size: 4rem; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">⚠️</div>
                        <h1>Share Not Found</h1>
                        <p>This share link has expired, been deleted, or never existed.</p>
                        <p>Shares are temporary and automatically expire after a set duration.</p>
                    </div>
                </body>
                </html>
                """)

            # Build the access page
            requires_password = share.access_type == ShareAccessType.PASSWORD
            time_remaining = str(share.expires_at - datetime.now()).split('.')[0]

            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Access Shared Password - kcpwd</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                        max-width: 500px;
                        width: 100%;
                    }}
                    h1 {{
                        color: #667eea;
                        margin-bottom: 10px;
                        font-size: 2rem;
                    }}
                    .subtitle {{
                        color: #999;
                        margin-bottom: 30px;
                        font-size: 0.9rem;
                    }}
                    .info {{
                        background: #f9fafb;
                        padding: 15px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        border-left: 4px solid #667eea;
                    }}
                    .info-row {{
                        display: flex;
                        justify-content: space-between;
                        margin: 8px 0;
                        font-size: 0.9rem;
                    }}
                    .info-label {{
                        color: #666;
                        font-weight: 600;
                    }}
                    .info-value {{
                        color: #333;
                    }}
                    .warning {{
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 15px;
                        margin-bottom: 20px;
                        border-radius: 4px;
                    }}
                    .warning-title {{
                        font-weight: 600;
                        color: #856404;
                        margin-bottom: 5px;
                    }}
                    .warning-text {{
                        color: #856404;
                        font-size: 0.9rem;
                    }}
                    input {{
                        width: 100%;
                        padding: 12px 16px;
                        margin: 10px 0;
                        border: 2px solid #e5e7eb;
                        border-radius: 6px;
                        font-size: 14px;
                        transition: all 0.3s;
                    }}
                    input:focus {{
                        outline: none;
                        border-color: #667eea;
                        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                    }}
                    button {{
                        width: 100%;
                        padding: 12px 24px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s;
                        margin-top: 10px;
                    }}
                    button:hover {{
                        background: #5568d3;
                        transform: translateY(-2px);
                        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                    }}
                    button:disabled {{
                        opacity: 0.5;
                        cursor: not-allowed;
                        transform: none;
                    }}
                    #result {{
                        margin-top: 20px;
                        padding: 15px;
                        border-radius: 8px;
                        display: none;
                    }}
                    #result.success {{
                        background: #d1fae5;
                        border: 1px solid #10b981;
                        color: #065f46;
                    }}
                    #result.error {{
                        background: #fee;
                        border: 1px solid #ef4444;
                        color: #991b1b;
                    }}
                    .password-display {{
                        background: #f9fafb;
                        padding: 15px;
                        border-radius: 6px;
                        margin: 15px 0;
                        font-family: monospace;
                        font-size: 1.1rem;
                        font-weight: bold;
                        word-break: break-all;
                        border: 2px solid #10b981;
                    }}
                    .copy-btn {{
                        background: #10b981;
                        margin-top: 10px;
                    }}
                    .copy-btn:hover {{
                        background: #059669;
                    }}
                    .hidden {{ display: none; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔐 Shared Password</h1>
                    <p class="subtitle">Secure temporary password sharing via kcpwd</p>
                    
                    <div class="info">
                        <div class="info-row">
                            <span class="info-label">Password Key:</span>
                            <span class="info-value">{share.key_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Expires in:</span>
                            <span class="info-value">{time_remaining}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Views:</span>
                            <span class="info-value">{share.view_count}/{share.max_views if share.max_views else '∞'}</span>
                        </div>
                    </div>
                    
                    <div class="warning">
                        <div class="warning-title">⚠️ Important</div>
                        <div class="warning-text">
                            This is a temporary share link. The password will be shown only once
                            {' and then deleted' if share.access_type == ShareAccessType.ONCE else ''}.
                            Make sure to save it securely.
                        </div>
                    </div>
                    
                    <div id="access-form">
                        {f'''
                        <input 
                            type="password" 
                            id="access-password" 
                            placeholder="Enter access password"
                            onkeypress="if(event.key==='Enter') accessShare()"
                        >
                        ''' if requires_password else ''}
                        
                        <button onclick="accessShare()" id="access-btn">
                            🔓 Reveal Password
                        </button>
                    </div>
                    
                    <div id="result"></div>
                </div>
                
                <script>
                    async function accessShare() {{
                        const btn = document.getElementById('access-btn');
                        const result = document.getElementById('result');
                        const accessForm = document.getElementById('access-form');
                        
                        btn.disabled = true;
                        btn.textContent = 'Loading...';
                        
                        try {{
                            const body = {{}};
                            {'const accessPassword = document.getElementById("access-password").value; body.access_password = accessPassword;' if requires_password else ''}
                            
                            const response = await fetch('/api/share/{share_id}/access', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify(body)
                            }});
                            
                            const data = await response.json();
                            
                            if (!response.ok) {{
                                throw new Error(data.detail || 'Failed to access share');
                            }}
                            
                            // Hide form
                            accessForm.style.display = 'none';
                            
                            // Show password
                            result.className = 'success';
                            result.style.display = 'block';
                            result.innerHTML = `
                                <div style="text-align: center;">
                                    <h3 style="color: #065f46; margin-bottom: 15px;">✓ Password Retrieved</h3>
                                    <div class="password-display" id="password-text">${{data.password}}</div>
                                    <button class="copy-btn" onclick="copyPassword()">
                                        📋 Copy to Clipboard
                                    </button>
                                    ${{data.remaining_views !== null ? 
                                        `<p style="margin-top: 15px; color: #666;">Remaining views: ${{data.remaining_views}}</p>` : ''}}
                                    ${{data.view_count === 1 && '{share.access_type.value}' === 'once' ?
                                        '<p style="margin-top: 15px; color: #ef4444; font-weight: 600;">⚠️ This share link has been consumed and is no longer valid.</p>' : ''}}
                                </div>
                            `;
                            
                        }} catch (error) {{
                            result.className = 'error';
                            result.style.display = 'block';
                            result.innerHTML = `
                                <strong>❌ Error:</strong><br>
                                ${{error.message}}
                            `;
                            btn.disabled = false;
                            btn.textContent = '🔓 Try Again';
                        }}
                    }}
                    
                    function copyPassword() {{
                        const passwordText = document.getElementById('password-text').textContent;
                        navigator.clipboard.writeText(passwordText).then(() => {{
                            alert('✓ Password copied to clipboard!');
                        }});
                    }}
                </script>
            </body>
            </html>
            """)

        except Exception as e:
            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - kcpwd</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 50px;
                        border-radius: 12px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                        max-width: 500px;
                        text-align: center;
                    }}
                    h1 {{ color: #ef4444; }}
                    .error {{ color: #666; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⚠️ Error</h1>
                    <p class="error">{str(e)}</p>
                </div>
            </body>
            </html>
            """)


# ============= Server Start =============

def start_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    secret: Optional[str] = None,
    open_browser: bool = True
):
    """Start UI server"""
    global _ui_secret

    host = host or UIConfig.HOST
    port = port or UIConfig.PORT

    # Set secret
    if secret:
        UIConfig.SECRET = secret
        _ui_secret = secret
    else:
        _ui_secret = UIConfig.get_secret()

    # Display info
    print("\n" + "=" * 60)
    print("🚀 kcpwd Web UI Starting")
    print("=" * 60)
    print(f"📍 URL: http://{host}:{port}")
    print(f"🔐 Backend: {get_backend_info()['description']}")
    print(f"🔑 UI Secret: {_ui_secret}")

    if SHARING_ENABLED:
        print(f"🔗 Sharing: ENABLED")
    else:
        print(f"⚠️  Sharing: DISABLED (module not found)")

    if not secret and not UIConfig.SECRET:
        print("\n⚠️  Using temporary secret (will change on restart)")
        print("   Set KCPWD_UI_SECRET env var for persistent secret")

    print("\n💡 Tips:")
    print("   • Keep your UI secret safe")
    print(f"   • Access from: http://{host}:{port}")
    if SHARING_ENABLED:
        print(f"   • Share passwords via: http://{host}:{port}/s/{{share_id}}")
    print("   • Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    # Open browser
    if open_browser:
        import webbrowser
        import threading

        def open_browser_delayed():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # Start server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info" if UIConfig.DEBUG else "warning",
        reload=UIConfig.RELOAD
    )


if __name__ == "__main__":
    start_server()