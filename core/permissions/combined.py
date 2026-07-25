from rest_framework.permissions import BasePermission

from core.permissions.organization import IsOrganizationOwner
from core.permissions.project import IsProjectLead, IsProjectManager, IsProjectOwner
from core.permissions.team import IsTeamManager, IsTeamOwner
from core.permissions.resolver import is_governance_backstop


class IsOrgOwnerOrProjectLead(BasePermission):
    message = "Only the organization/team owner or a project lead can perform this action."

    def has_object_permission(self, request, view, project):
        return bool(
            is_governance_backstop(request.user, project)
            or IsProjectLead().has_object_permission(request, view, project)
        )


class IsOrgOwnerOrProjectManager(BasePermission):
    message = "Only the organization/team owner or project manager can perform this action."

    def has_object_permission(self, request, view, project):
        return bool(
            is_governance_backstop(request.user, project)
            or IsProjectManager().has_object_permission(request, view, project)
        )


class IsOrgOwnerOrTeamOwner(BasePermission):
    message = "Only the organization owner or team owner can perform this action."

    def has_object_permission(self, request, view, team):
        if team is None:
            return False
        org = team.organization

        return bool(
            IsOrganizationOwner().has_object_permission(request, view, org)
            or IsTeamOwner().has_object_permission(request, view, team)
        )


class IsOrgOwnerOrTeamManager(BasePermission):
    message = "Only the organization owner or team manager can perform this action."

    def has_object_permission(self, request, view, team):
        if team is None:
            return False
        org = team.organization

        return bool(
            IsOrganizationOwner().has_object_permission(request, view, org)
            or IsTeamManager().has_object_permission(request, view, team)
        )


class IsOrgOwnerOrProjectOwner(BasePermission):
    message = "Only the organization/team owner or project owner can perform this action."

    def has_object_permission(self, request, view, project):
        return bool(
            is_governance_backstop(request.user, project)
            or IsProjectOwner().has_object_permission(request, view, project)
        )

