"""Re-export de compatibilidade; preferir `from app.core.settings import settings`."""

from app.core.settings import Settings, settings

__all__ = ["Settings", "settings"]
