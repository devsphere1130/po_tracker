from rest_framework.permissions import BasePermission


def user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile else "staff"


class RoleBasedPermission(BasePermission):
    """Authenticated users may read/create/update. DELETE needs Admin.
    A view may set admin_only = True to restrict the whole view to Admin."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        role = user_role(request.user)
        if role is None:
            return False
        if getattr(view, "admin_only", False):
            return role == "admin"
        if request.method == "DELETE":
            return role == "admin"
        return True
