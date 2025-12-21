from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasWriteToken(BasePermission):
    """Simple header-based write protection for lab deployments.

    Allows read-only requests without a token.
    Requires header for write methods:
      X-IVC-Write-Token: <token>

    Disable by leaving WRITE_TOKEN empty.
    """

    message = "Missing or invalid write token."

    def has_permission(self, request, view):
        # Always allow safe/read methods
        if request.method in SAFE_METHODS:
            return True

        token = (getattr(settings, "WRITE_TOKEN", "") or "").strip()
        if not token:
            return True  # disabled

        provided = (request.headers.get("X-IVC-Write-Token", "") or "").strip()
        return provided == token
