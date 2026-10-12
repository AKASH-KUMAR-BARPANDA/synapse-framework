"""OAuth and token authentication services for Synapse connectors."""

from synapse.oauth.google import GoogleOAuthService
from synapse.oauth.notion import NotionAuthService

# Re-export GoogleOAuthService matching the user's requested naming
__all__ = ["GoogleOAuthService", "NotionAuthService"]
