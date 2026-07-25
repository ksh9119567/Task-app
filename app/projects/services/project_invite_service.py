import logging

from rest_framework.exceptions import ValidationError

from app.projects.models import ProjectMembership

from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email

from core.constants.project_constant import PROJECT_ROLES
from core.utils.project_utils import count_explicit_members

logger = logging.getLogger(__name__)


def send_project_invite(*, project, user, invited_by, role):
    """
    Create invite token and send project invite email
    """
    logger.info(f"Sending project invite to {user.email} for project: {project.name}")

    if count_explicit_members(project) >= project.settings.max_members:
        raise ValidationError("Project has reached maximum member limit.")


    if ProjectMembership.objects.filter(project=project, user=user).exists():
        logger.warning(f"User {user.email} already a member of project: {project.name}")
        raise ValidationError("User already a member")

    if role not in [r[0] for r in PROJECT_ROLES]:
        logger.error(f"Invalid role '{role}' provided for project invite to {user.email}")
        raise ValidationError("Invalid role specified")
    
    invite_token = store_invite_token(
        user_id=user.id,
        invite_type="project",
        invited_by=invited_by.email,
        entity=project,
        role=role
    )

    send_invite_email(
        email=user.email,
        invite_type="Project",
        name=project.name,
        sender=invited_by.email
    )

    logger.info(f"Project invite sent successfully to {user.email}")
    return invite_token
