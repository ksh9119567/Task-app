from core.permissions.base import get_org_role, get_team_role, get_project_role
from core.constants.project_constant import PROJECT_ROLE_HIERARCHY


def _is_container_owner(user, project):
    """
    True if `user` owns the project's organization or team container.
    Shared logic for the two product-distinct concepts below - they resolve
    identically today but mean different things depending on which action
    they gate, so they're kept as separate, distinctly-named entry points.
    """
    if project is None or user is None or not getattr(user, "is_authenticated", False):
        return False
    if project.organization_id and get_org_role(user, project.organization) == "OWNER":
        return True
    if project.team_id and get_team_role(user, project.team) == "OWNER":
        return True
    return False


def is_governance_backstop(user, project):
    """
    Continuity-only override authority (reassign/delete/dispute resolution).
    NOT for day-to-day actions - never fold this into a rank/max() comparison
    for ordinary permission checks. See effective_role().
    """
    return _is_container_owner(user, project)


def can_override_member_policy(user, project):
    """
    Lets a container (org/team) owner bypass the project's configurable
    member-management policy gate (check_role_permissions), the same way the
    project's own Owner already can. Distinct from is_governance_backstop:
    this is day-to-day member administration, not a continuity action - kept
    separately named so the two doc-level concepts don't blur together.
    """
    return _is_container_owner(user, project)


def _team_derived_role(user, project):
    """
    The best role a user gets on a project purely by being a member of one
    of the project's assigned teams, via that team-project link's own role -
    combined most-permissive-wins across every assigned team (a project can
    have several, per Phase C; which one is flagged `is_owning` is an
    accountability label only and plays no part in this). Never written into
    ProjectMembership - this is computed dynamically.
    """
    roles = [
        link.role for link in project.all_team_links
        if get_team_role(user, link.team) is not None
    ]
    if not roles:
        return None
    return max(roles, key=lambda role: PROJECT_ROLE_HIERARCHY.get(role, -1))


def effective_role(user, project):
    """
    The user's day-to-day operational role on the project: explicit
    membership and team-derived access (via the assigned team's link role),
    combined by most-permissive-wins. Does NOT include governance-backstop
    authority - that's a separate, continuity-only check
    (is_governance_backstop), never merged into rank comparisons for
    ordinary actions.
    """
    if project is None:
        return None
    explicit = get_project_role(user, project)
    team_role = _team_derived_role(user, project)
    ranked = [role for role in (explicit, team_role) if role]
    if not ranked:
        return None
    return max(ranked, key=lambda role: PROJECT_ROLE_HIERARCHY.get(role, -1))


def _team_owner(team):
    from app.teams.models import TeamMembership
    membership = TeamMembership.objects.filter(team=team, role="OWNER").first()
    return membership.user if membership else team.created_by


def resolve_permission_root(entity):
    """
    The User who is the ultimate permission root / billing anchor for
    `entity` (a Project, Team, or Organization) - the owner of its
    top-most existing container: Project -> org owner if in an org, else
    owning-team owner if a team is assigned, else the project creator;
    Team -> org owner if in an org, else the team's own owner; Organization
    -> its own owner (always top-level, nothing to defer to).

    Forward-looking infrastructure per the doc's tiering model (billing
    attaches at the top-most existing container) - nothing in this
    codebase calls it yet, since there's no billing/plan system to wire it
    into.
    """
    from app.projects.models import Project
    from app.teams.models import Team
    from app.organizations.models import Organization

    if isinstance(entity, Project):
        if entity.organization_id:
            return entity.organization.owner
        link = entity.team_link
        if link is not None:
            return _team_owner(link.team)
        return entity.created_by
    if isinstance(entity, Team):
        return entity.organization.owner if entity.organization_id else _team_owner(entity)
    if isinstance(entity, Organization):
        return entity.owner
    raise TypeError(f"Unsupported entity type for permission root resolution: {type(entity)}")
