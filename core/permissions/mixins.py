from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class RoleCheckerMixin:
    def has_minimum_role(self, user_role: str, required_role: str, hierarchy: dict) -> bool:
        """
        Safely compare numeric role ranks. Returns False if either role is missing.
        """
        if not user_role or not required_role:
            return False
        # Avoid KeyError if roles are missing from hierarchy
        user_rank = hierarchy.get(user_role)
        required_rank = hierarchy.get(required_role)
        if user_rank is None or required_rank is None:
            return False
        return user_rank >= required_rank


class EnforceObjectPermissionsMixin:
    # Set on `self` once resolved, so action bodies can reuse it instead of
    # re-fetching the same org/team/project a second time.
    permission_object = None

    def get_permission_object(self):
        """
        Return the object to check object-level permissions against for the
        current action. Only called when a configured permission class for
        this action actually needs one. May return None (e.g. missing id
        param) — that's fine, has_object_permission() must handle None safely.
        """
        raise NotImplementedError

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        needs_object_check = any(
            type(perm).has_object_permission is not BasePermission.has_object_permission
            for perm in self.get_permissions()
        )
        if needs_object_check:
            self.permission_object = self.get_permission_object()
            self.check_object_permissions(request, self.permission_object)

        

class OrganizationPermissionMixin:
    """
    Small helper mixin you can use in views. It will look for permission classes
    on the view via `permission_classes` first, and fall back to
    `object_permission_classes` if present (backwards compatibility).
    """

    # legacy-compatible attribute name
    object_permission_classes = []

    def _get_permission_list(self):
        # If the view explicitly sets object_permission_classes — use them
        if getattr(self, "object_permission_classes", None):
            return self.object_permission_classes

        # Otherwise fallback to standard permission_classes
        return getattr(self, "permission_classes", [])


    def check_organization_permission(self, request, organization):
        """
        Iterate the declared permission classes and raise PermissionDenied
        if any fails (so checking is strict).
        """
        for perm_cls in self._get_permission_list():
            # instantiate and evaluate object permission
            perm = perm_cls()
            allowed = perm.has_object_permission(request, self, organization)
            if not allowed:
                # use permission message when available
                msg = getattr(perm, "message", "Permission denied.")
                raise PermissionDenied(detail=msg)
