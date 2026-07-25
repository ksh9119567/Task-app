import uuid

from django.db import models

from app.governance.models import ProjectSettings

from core.constants.project_constant import PROJECT_ROLES, PROJECT_STATUS
from core.models import TimeStampedModel


class Project(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="projects"
    )

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_projects"
    )

    description = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=PROJECT_STATUS, default="PLANNING")

    members = models.ManyToManyField(
        "accounts.User",
        through="ProjectMembership",
        related_name="projects"
    )
    
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    
    class Meta:
        ordering = ("name", )

    def __str__(self):
        return self.name

    @property
    def all_team_links(self):
        """
        Every team assigned to this project, cached on the instance for the
        life of the request - effective_role(), count_explicit_members(),
        and team_link would otherwise each issue their own identical query.
        """
        if not hasattr(self, "_team_links_cache"):
            self._team_links_cache = list(self.team_links.select_related("team"))
        return self._team_links_cache

    @property
    def team_link(self):
        """
        The project's owning team link (or None). Used by everything that
        predates multi-team support (governance-rule inheritance, the
        governance-backstop check, ProjectSerializer's team/team_name/
        team_role) - those all mean "the accountable team" specifically,
        not "any assigned team".
        """
        for link in self.all_team_links:
            if link.is_owning:
                return link
        return None

    @property
    def team(self):
        link = self.team_link
        return link.team if link else None

    @property
    def team_id(self):
        link = self.team_link
        return link.team_id if link else None


class ProjectMembership(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="project_memberships"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    role = models.CharField(max_length=50, choices=PROJECT_ROLES, null=False, blank=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "project"], name="unique_project_user")
        ]
        ordering = ("-joined_at",)
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["project"]),
        ]

    def save(self, *args, **kwargs):
        if not self.role:
            project_settings = ProjectSettings.objects.get(project=self.project)
            self.role = project_settings.default_member_role
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.email} - {self.project.name}"


class ProjectTeam(TimeStampedModel):
    """
    A team assigned to a project, carrying its own role. Team members inherit
    this role on the project dynamically through the link - they are never
    written into ProjectMembership. A project may have several team links;
    exactly one may be flagged `is_owning`, for accountability/reporting
    only - it grants no extra authority (see core/permissions/resolver.py,
    which deliberately keys governance-backstop checks off this flag by
    reading Project.team/.team_id, not off every assigned team).
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="team_links"
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="project_links"
    )
    role = models.CharField(max_length=50, choices=PROJECT_ROLES, null=False, blank=False)
    is_owning = models.BooleanField(default=False)
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "team"], name="unique_project_team_pair"),
            models.UniqueConstraint(
                fields=["project"], condition=models.Q(is_owning=True),
                name="unique_owning_team_per_project"
            ),
        ]
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["team"]),
        ]

    def __str__(self):
        return f"{self.team.name} -> {self.project.name} ({self.role})"
