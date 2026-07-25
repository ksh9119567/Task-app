import logging

from rest_framework.exceptions import ValidationError, PermissionDenied

from app.projects.models import ProjectMembership

from core.utils.project_utils import count_explicit_members
from core.permissions.resolver import effective_role
from core.constants.project_constant import PROJECT_ROLE_HIERARCHY

logger = logging.getLogger(__name__)


def add_project_member(*, project, user, role):
    logger.info(f"Adding member {user.email} to project: {project.name} with role: {role}")
    if ProjectMembership.objects.filter(project=project, user=user).exists():
        logger.warning(f"User {user.email} already a member of project: {project.name}")
        raise ValidationError("User already a member")

    if count_explicit_members(project) >= project.settings.max_members:
        logger.warning(f"Project has reached maximum member limit: {project.name}")
        raise ValidationError("Project has reached maximum member limit.")

    membership = ProjectMembership.objects.create(
        project=project,
        user=user,
        role=role
    )
    logger.info(f"Member {user.email} added successfully to project: {project.name}")
    return membership


def remove_project_member(*, project, user, performed_by):
    logger.info(f"Removing member {user.email} from project: {project.name}")
    if user == project.created_by:
        logger.warning(f"Attempt to remove project creator from project: {project.name}")
        raise PermissionDenied("Cannot remove project creator")

    try:
        membership = ProjectMembership.objects.get(project=project, user=user)
    except ProjectMembership.DoesNotExist:
        logger.warning(f"Attempt to remove non-explicit member {user.email} from project: {project.name}")
        raise ValidationError(
            "This user's access comes from their assigned team, not an explicit membership - "
            "remove them from the team instead."
        )

    target_user_role = effective_role(user, project)
    action_user_role = effective_role(performed_by, project)

    if PROJECT_ROLE_HIERARCHY.get(target_user_role, -1) >= PROJECT_ROLE_HIERARCHY.get(action_user_role, -1):
        logger.warning(f"Attempt to remove user with equal or higher role from project: {project.name}")
        raise PermissionDenied("Cannot remove user with equal or higher role")

    if target_user_role == "MANAGER":
        manager_count = project.memberships.filter(role="MANAGER").count()
        if manager_count == 1:
            logger.warning(f"Attempt to remove last manager from project: {project.name}")
            raise PermissionDenied("Last manager cannot be removed.")

    membership.delete()
    logger.info(f"Member {user.email} removed successfully from project: {project.name}")


def self_remove_project_member(*, project, user):
    logger.info(f"Self-remove requested by {user.email} from project: {project.name}")

    if not project.settings.allow_self_removal:
        logger.warning(f"Self-remove not allowed for project: {project.name}")
        raise PermissionDenied("Self removal not allowed")

    if user == project.created_by:
        logger.warning(f"Project owner attempted self-remove from project: {project.name}")
        raise PermissionDenied("Project owner cannot remove themselves. Must transfer ownership first.")

    try:
        membership = ProjectMembership.objects.get(project=project, user=user)
    except ProjectMembership.DoesNotExist:
        logger.warning(f"Self-remove attempted by team-derived-only user {user.email} from project: {project.name}")
        raise ValidationError(
            "Your access comes from your assigned team, not an explicit membership - leave the team instead."
        )

    user_role = effective_role(user, project)
    if user_role == "MANAGER":
        manager_count = project.memberships.filter(role="MANAGER").count()
        if manager_count == 1:
            logger.warning(f"Last manager attempted self-remove from project: {project.name}")
            raise PermissionDenied("Last manager cannot remove themselves.")

    membership.delete()
    logger.info(f"User {user.email} self-removed successfully from project: {project.name}")


def update_project_member_role(*, project, user, role):
    """
    Upserts the membership rather than requiring an existing row - this is
    the mechanism for elevating a team-derived-only participant into an
    explicit member (per the doc's own build note for team-project links).
    """
    logger.info(f"Updating role for {user.email} in project: {project.name} to {role}")
    membership, _ = ProjectMembership.objects.update_or_create(
        project=project,
        user=user,
        defaults={"role": role},
    )
    logger.info(f"Role updated successfully for {user.email} in project: {project.name}")
    return membership
