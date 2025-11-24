"""
kcpwd.ui.config - Configuration for UI
"""

import os
from typing import Optional


class UIConfig:
    """UI Configuration"""

    # Server settings
    HOST: str = os.getenv("KCPWD_UI_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("KCPWD_UI_PORT", "8765"))

    # Security
    SECRET: Optional[str] = os.getenv("KCPWD_UI_SECRET")
    SESSION_TIMEOUT: int = 3600  # 1 hour

    # Development
    DEBUG: bool = os.getenv("KCPWD_UI_DEBUG", "false").lower() == "true"
    RELOAD: bool = DEBUG

    # CORS (if needed for separate frontend)
    CORS_ENABLED: bool = os.getenv("KCPWD_UI_CORS", "false").lower() == "true"
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]  # React/Vite

    @classmethod
    def get_secret(cls) -> str:
        """Get or generate UI secret"""
        if cls.SECRET:
            return cls.SECRET

        # Generate temporary secret
        import secrets
        temp_secret = secrets.token_urlsafe(16)
        return temp_secret