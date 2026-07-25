import logging

from rest_framework.exceptions import ValidationError

from app.organizations.models import OrganizationMembership

from services.invite_token_service import store_invite_token
from services.notification_services import send_invite_email

from core.constants.org_constant import ORG_ROLES

logger = logging.getLogger(__name__)


def send_organization_invite(*, organization, user, invited_by, role):
    """
    Create invite token and send organization invite email
    """
    logger.info(f"Sending organization invite to {user.email} for org: {organization.name}")
    
    if organization.memberships.count() >= organization.settings.max_members:
        raise ValidationError("Organization has reached maximum member limit.")

    if OrganizationMembership.objects.filter(organization=organization, user=user).exists():
        logger.warning(f"User {user.email} already a member of org: {organization.name}")
        raise ValidationError("User already a member")

    if role not in [r[0] for r in ORG_ROLES]:
        logger.error(f"Invalid role '{role}' provide for organization invite to {user.email}")
        raise ValidationError("Invalid role specified")

    invite_token = store_invite_token(
        user_id=user.id,
        invite_type="organization",
        invited_by=invited_by.email,
        entity=organization,
        role=role
    )

    send_invite_email(
        email=user.email,
        invite_type="Organization",
        name=organization.name,
        sender=invited_by.email
    )

    logger.info(f"Organization invite sent successfully to {user.email}")
    return invite_token
