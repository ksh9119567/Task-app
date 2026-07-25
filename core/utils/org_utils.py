import logging

from rest_framework.exceptions import NotFound, ValidationError

from app.organizations.models import Organization, OrganizationMembership

logger = logging.getLogger(__name__)


def get_org(org_id):
    """
    Returns a organization instance by org_id.
    """
    logger.debug(f"Getting organization: {org_id}")
    if org_id:
        try:
            obj = Organization.objects.filter(id=org_id, is_deleted=False).first()
            if not obj:
                logger.warning(f"Organization not found: {org_id}")
                raise NotFound("Organization not found")
            logger.debug(f"Organization found: {obj.name}")
            return obj
        except Exception as e:
            logger.error(f"Error getting organization {org_id}: {str(e)}")
            raise Exception(e)
    logger.warning("Organization ID is required but not provided")
    raise ValidationError("Organization ID is required")

def get_org_membership(org_id, user):
    """
    Returns a membership instance by org_id and user.
    """
    if org_id and user:
        try:
            return OrganizationMembership.objects.get(organization_id=org_id, user=user)
        except OrganizationMembership.DoesNotExist:
            raise NotFound("Organization membership not found")
    raise ValidationError("Organization ID and user are required")

def get_all_org_memberships(org_id):
    """
    Returns all members of an organization by org_id.
    """
    if org_id:
        try:
            return OrganizationMembership.objects.filter(organization_id=org_id)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Organization ID is required")
