from functools import wraps
from django.core.exceptions import PermissionDenied

def role_required(*allowed_roles):
    """
    Decorator for views that checks whether a user has a specific role.
    Usage: @role_required('admin', 'company')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            if request.user.role not in allowed_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_required(view_func):
    """Shorthand for requiring global admin."""
    return role_required('admin')(view_func)
