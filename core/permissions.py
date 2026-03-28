from rest_framework import permissions

class IsGlobalAdmin(permissions.BasePermission):
    """Allows access only to global admins."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')

class IsCompanyUser(permissions.BasePermission):
    """Allows access to company users (tenant-specific)."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'company'

class IsAuthenticatedUser(permissions.BasePermission):
    """Enforces authentication and role assignment."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['admin', 'company']
