import uuid

from django.db import models
from django.utils import timezone

from app.governance.models import TeamSettings

from core.constants.team_constant import TEAM_ROLES
from core.models import TimeStampedModel


class Team(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="teams"
    )

    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_teams"
    )

    members = models.ManyToManyField(
        "accounts.User",
        through="TeamMembership",
        related_name="teams"
    )
    
    is_deleted = models.BooleanField(default=False)  # Soft delete flag

    class Meta:
        ordering = ("name", )

    def __str__(self):
        return self.name

    @property
    def projects(self):
        """
        Projects this team is assigned to via a ProjectTeam link. Replaces
        the old `related_name="projects"` reverse accessor from Project's
        now-removed `team` ForeignKey - kept as a property so existing call
        sites (team.projects.count(), etc.) don't need to change.
        """
        from app.projects.models import Project
        return Project.objects.filter(team_links__team=self, is_deleted=False)


class TeamMembership(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="team_memberships"
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    role = models.CharField(max_length=50, choices=TEAM_ROLES, null=False, blank=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "team"], name="unique_team_user")
        ]
        ordering = ("-joined_at",)
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["team"]),
        ]

    def save(self, *args, **kwargs):
        if not self.role:
            team_settings = TeamSettings.objects.get(team=self.team)
            self.role = team_settings.default_member_role
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.user.email} - {self.team.name}"
