import logging

from rest_framework.exceptions import NotFound, ValidationError

from app.teams.models import Team, TeamMembership

logger = logging.getLogger(__name__)


def get_team(team_id):
    """
    Returns a team instance by team_id.
    """
    logger.debug(f"Getting team: {team_id}")
    if team_id:
        try:
            obj = Team.objects.filter(id=team_id, is_deleted=False).first()
            if not obj:
                logger.warning(f"Team not found: {team_id}")
                raise NotFound("Team not found")
            logger.debug(f"Team found: {obj.name}")
            return obj
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {str(e)}")
            raise Exception(e)
    logger.warning("Team ID is required but not provided")
    raise ValidationError("Team ID is required")

def get_all_team_memberships(team_id):
    """
    Returns all members of a team by team_id.
    """
    if team_id:
        try:
            return TeamMembership.objects.filter(team_id=team_id)
        except Exception as e:
            raise Exception(e)
    raise ValidationError("Team ID is required")

def get_team_membership(team_id, user):
    """
    Returns a membership instance by team_id and user.
    """
    if team_id and user:
        try:
            return TeamMembership.objects.get(team_id=team_id, user=user)
        except TeamMembership.DoesNotExist:
            raise NotFound("Team membership not found")
    raise ValidationError("Team ID and user are required")
