import logging

from rest_framework.exceptions import ValidationError

from app.teams.models import TeamMembership

from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email

from core.constants.team_constant import TEAM_ROLES

logger = logging.getLogger(__name__)


def send_team_invite(*, team, user, invited_by, role):
    """
    Create invite token and send team invite email
    """
    logger.info(f"Sending team invite to {user.email} for team: {team.name}")

    if team.memberships.count() >= team.settings.max_members:
        raise ValidationError("Team has reached maximum member limit.")

    if TeamMembership.objects.filter(team=team, user=user).exists():
        logger.warning(f"User {user.email} already a member of team: {team.name}")
        raise ValidationError("User already a member")

    if role not in [r[0] for r in TEAM_ROLES]:
        logger.error(f"Invalid role '{role}' provided for team invite to {user.email}")
        raise ValidationError("Invalid role specified")

    invite_token = store_invite_token(
        user_id=user.id,
        invite_type="team",
        invited_by=invited_by,
        entity=team,
        role=role
    )

    send_invite_email(
        email=user.email,
        invite_type="Team",
        name=team.name,
        sender=invited_by.email
    )

    logger.info(f"Team invite sent successfully to {user.email}")
    return invite_token
