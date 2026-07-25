import logging

from rest_framework.exceptions import PermissionDenied, ValidationError

from app.projects.models import ProjectMembership
from app.organizations.models import OrganizationMembership
from core.permissions.resolver import is_governance_backstop

logger = logging.getLogger(__name__)


def transfer_project_ownership(*, project, new_owner, performed_by):
    """
    Transfer project ownership to another user
    """
    logger.info(f"Transferring ownership of project: {project.name} to {new_owner.email}")

    if project.created_by != performed_by and not is_governance_backstop(performed_by, project):
        logger.warning(f"Unauthorized ownership transfer attempt by {performed_by.email} for project: {project.name}")
        raise PermissionDenied("Only the project creator or a governance backstop (org/owning-team owner) can transfer ownership")

    if new_owner == project.created_by:
        logger.warning(f"Attempt to transfer ownership to current creator for project: {project.name}")
        raise ValidationError("User is already project creator")

    if project.organization and not OrganizationMembership.objects.filter(organization=project.organization, user=new_owner).exists():
        logger.warning(f"User {new_owner.email} not a member of organization for project: {project.name}")
        raise ValidationError("User is not a member of the organization")

    if not ProjectMembership.objects.filter(project=project, user=new_owner).exists():
        logger.warning(f"User {new_owner.email} not a member of project: {project.name}")
        raise ValidationError("User is not a member of the project")

    new_owner_membership = ProjectMembership.objects.get(project=project, user=new_owner)
    old_owner_membership = project.memberships.get(user=project.created_by)

    old_owner_membership.role = "MANAGER"
    old_owner_membership.save(update_fields=["role"])
    
    new_owner_membership.role = "OWNER"
    new_owner_membership.save(update_fields=["role"])

    project.created_by = new_owner
    project.save(update_fields=["created_by"])
    logger.info(f"Ownership transferred successfully to {new_owner.email} for project: {project.name}")

def delete_project(*, project, performed_by):
    logger.info(f"Deleting project: {project.name}")
    if project.created_by != performed_by:
        logger.warning(f"Non-creator {performed_by.email} attempted to delete project: {project.name}")
        raise PermissionDenied("Only project creator can delete project")

    project.is_deleted = True
    project.save(update_fields=["is_deleted"])
    logger.info(f"Project deleted successfully: {project.name}")
