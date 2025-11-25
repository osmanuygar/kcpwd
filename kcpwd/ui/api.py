"""
kcpwd.ui.api - Web UI Backend
FastAPI-based REST API for password management
"""

from fastapi import FastAPI, HTTPException, Depends, Security, status
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
    description="Password Manager Web Interface",
    version="0.6.1",
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
        "version": "0.6.1",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/debug")
async def debug_info():
    """Debug information (only in debug mode)"""
    if not UIConfig.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "secret_set": _ui_secret is not None,
        "secret_length": len(_ui_secret) if _ui_secret else 0,
        "active_sessions": len(_sessions),
        "config": {
            "HOST": UIConfig.HOST,
            "PORT": UIConfig.PORT,
            "DEBUG": UIConfig.DEBUG,
            "SECRET_ENV_SET": UIConfig.SECRET is not None
        }
    }


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


@app.post("/api/check-strength")
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

    if not secret and not UIConfig.SECRET:
        print("\n⚠️  Using temporary secret (will change on restart)")
        print("   Set KCPWD_UI_SECRET env var for persistent secret")

    print("\n💡 Tips:")
    print("   • Keep your UI secret safe")
    print(f"   • Access from: http://{host}:{port}")
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