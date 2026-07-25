import logging

from django.db import transaction, IntegrityError

from rest_framework.exceptions import ValidationError, NotFound

from app.projects.models import Project, ProjectTeam

logger = logging.getLogger(__name__)


def _invalidate_team_cache(project):
    if hasattr(project, "_team_links_cache"):
        del project._team_links_cache


def assign_team(*, project, team, role, is_owning, assigned_by):
    """
    Assigns a team to a project with the given role, creating the link or
    promoting an existing non-owning assignment (update_or_create, not
    create - the team may already be linked non-owning, and a plain create
    would collide with the (project, team) uniqueness constraint). The
    first team ever assigned to a project always becomes owning regardless
    of the `is_owning` argument, so a project with teams is never left
    without one accountable.

    Locks the project row for the duration - without it, two concurrent
    assignments could both read "who's currently owning" before either
    commits and both try to become the owning team; the partial unique
    constraint stops the second write but as a raw IntegrityError, not a
    clean error, and doesn't prevent the race itself.
    """
    logger.info(f"Assigning team {team.name} to project {project.name} (role={role})")
    with transaction.atomic():
        locked_project = Project.objects.select_for_update().get(pk=project.pk)
        make_owning = bool(is_owning) or not ProjectTeam.objects.filter(project=locked_project).exists()

        if make_owning:
            ProjectTeam.objects.filter(project=locked_project, is_owning=True).update(is_owning=False)

        try:
            link, _created = ProjectTeam.objects.update_or_create(
                project=locked_project,
                team=team,
                defaults={"role": role, "is_owning": make_owning, "assigned_by": assigned_by},
            )
        except IntegrityError:
            logger.error(f"Conflicting owning-team update while assigning {team.name} to project {project.name}")
            raise ValidationError("Could not assign team - conflicting update, please retry.")

    _invalidate_team_cache(project)
    logger.info(f"Team {team.name} assigned to project {project.name} successfully (owning={make_owning})")
    return link


def update_team_link(*, project, team, role=None, is_owning=None):
    """
    Updates an existing team-project link's role and/or owning flag.
    Refuses to unflag the sole owning team without a replacement - the
    partial unique constraint only bounds the owning count from above (at
    most one), never from below, so a project could otherwise silently end
    up with no accountable team.
    """
    logger.info(f"Updating team link {team.name} on project {project.name}")
    with transaction.atomic():
        locked_project = Project.objects.select_for_update().get(pk=project.pk)
        try:
            link = ProjectTeam.objects.get(project=locked_project, team=team)
        except ProjectTeam.DoesNotExist:
            raise NotFound("This team is not assigned to the project.")

        if is_owning is False and link.is_owning:
            raise ValidationError(
                "Cannot unflag the owning team without promoting another - "
                "assign a different team as owning first, or unassign this team instead."
            )

        if is_owning is True and not link.is_owning:
            ProjectTeam.objects.filter(project=locked_project, is_owning=True).update(is_owning=False)
            link.is_owning = True

        if role is not None:
            link.role = role

        try:
            link.save()
        except IntegrityError:
            logger.error(f"Conflicting owning-team update for {team.name} on project {project.name}")
            raise ValidationError("Could not update team - conflicting update, please retry.")

    _invalidate_team_cache(project)
    logger.info(f"Team link {team.name} updated on project {project.name}")
    return link


def unassign_team(*, project, team):
    """
    Removes a team's link to a project. If the removed team was the owning
    one and other teams remain assigned, the earliest-assigned remaining
    team is automatically promoted to owning - a project with teams should
    never end up with none flagged accountable.
    """
    logger.info(f"Unassigning team {team.name} from project {project.name}")
    with transaction.atomic():
        locked_project = Project.objects.select_for_update().get(pk=project.pk)
        try:
            link = ProjectTeam.objects.get(project=locked_project, team=team)
        except ProjectTeam.DoesNotExist:
            raise NotFound("This team is not assigned to the project.")

        was_owning = link.is_owning
        link.delete()

        if was_owning:
            next_link = ProjectTeam.objects.filter(project=locked_project).order_by("created_at").first()
            if next_link:
                next_link.is_owning = True
                next_link.save(update_fields=["is_owning"])

    _invalidate_team_cache(project)
    logger.info(f"Team {team.name} unassigned from project {project.name} successfully")
