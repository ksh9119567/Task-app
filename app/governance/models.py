from django.db import models

from core.models import TimeStampedModel
from core.constants import org_constant, team_constant, project_constant


class BaseSettings(TimeStampedModel):

    # Membership rules
    allow_member_invites = models.BooleanField(default=False)                     # Whether members other than owner can invite new members
    allow_member_updates = models.BooleanField(default=False)                     # Whether members other than owner can update other members
    allow_member_removal = models.BooleanField(default=False)                     # Whether members other than owner can remove other members
    allow_self_removal = models.BooleanField(default=False)                       # Whether members can remove themselves from the organization/team/project
    
    # Approval rules
    require_approval_for_invites = models.BooleanField(default=False)             # Whether inviting new members requires approval
    require_approval_for_updates = models.BooleanField(default=False)             # Whether updating other members requires approval
    require_approval_for_removal = models.BooleanField(default=False)             # Whether removing other members requires approval
    
    class Meta:
        abstract = True
        
        
class OrganizationSettings(BaseSettings):
    organization = models.OneToOneField(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='settings'
    )
    
    # Limits
    max_members = models.PositiveIntegerField(default=50)                         # Maximum number of members in an organization
    max_teams = models.PositiveIntegerField(default=5)                            # Maximum number of teams in an organization
    max_projects = models.PositiveIntegerField(default=10)                        # Maximum number of projects in an organization
    
    # Default roles
    default_member_role = models.CharField(
        max_length=20, default="MEMBER", 
        choices=org_constant.ORG_ROLES
    )                                                                             # Default role assigned to new members
    
    # Role_based permissions
    invite_member_min_role = models.CharField(
        max_length=20, default="ADMIN", 
        choices=org_constant.ORG_ROLES
    )
    update_member_min_role = models.CharField(
        max_length=20, default="ADMIN", 
        choices=org_constant.ORG_ROLES
    )
    remove_member_min_role = models.CharField(
        max_length=20, default="ADMIN", 
        choices=org_constant.ORG_ROLES
    )
    create_team_min_role = models.CharField(
        max_length=20, default="ADMIN", 
        choices=org_constant.ORG_ROLES
    )
    create_project_min_role = models.CharField(
        max_length=20, default="ADMIN", 
        choices=org_constant.ORG_ROLES
    )
    
    # Creation Controls
    allow_team_creation = models.BooleanField(default=False)                      # Whether teams can be created by members other than owner
    allow_project_creation = models.BooleanField(default=False)                   # Whether projects can be created by members other than owner
    
    # Approval rules
    require_approval_for_team = models.BooleanField(default=False)                # Whether team creation requires Org owner approval
    require_approval_for_project = models.BooleanField(default=False)             # Whether project creation requires Org/Team owner approval

    def __str__(self):
        return f"Org Settings - {self.organization.name}"
    
    
class TeamSettings(BaseSettings):
    team = models.OneToOneField(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='settings'
    )
    
    # Limits
    max_members = models.PositiveIntegerField(default=20)                                 # Maximum number of members in a team
    max_projects = models.PositiveIntegerField(default=10)                        # Maximum number of projects in a team
    
    # Default roles
    default_member_role = models.CharField(
        max_length=20, default="MEMBER", 
        choices=team_constant.TEAM_ROLES
    )                                                                             # Default role assigned to new members
    
    # Role_based permissions
    invite_member_min_role = models.CharField(
        max_length=20, default="MANAGER", 
        choices=team_constant.TEAM_ROLES
    )
    update_member_min_role = models.CharField(
        max_length=20, default="MANAGER", 
        choices=team_constant.TEAM_ROLES
    )
    remove_member_min_role = models.CharField(
        max_length=20, default="MANAGER", 
        choices=team_constant.TEAM_ROLES
    )
    create_project_min_role = models.CharField(
        max_length=20, default="MANAGER", 
        choices=team_constant.TEAM_ROLES
    )
    
    # Creation Controls
    allow_project_creation = models.BooleanField(default=False)                   # Whether user other than Team owner can create projects
    
    # Approval rules
    require_approval_for_project = models.BooleanField(default=False)             # Whether project creation requires Team owner approval
    
    # ---- Inherit Settings ----
    inherit_base_rules_from_org = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Team Settings - {self.team.name}"
    

class ProjectSettings(BaseSettings):
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='settings'
    )
    
    # Task rules
    allow_task_creation = models.BooleanField(default=True)                        # Whether users can other than Project owner can create tasks
    allow_task_updates = models.BooleanField(default=True)                         # Whether users can other than Project owner can update tasks
    allow_task_deletions = models.BooleanField(default=True)                       # Whether users can other than Project owner can delete tasks
    only_assignee_can_update_task = models.BooleanField(default=False)   
    
    create_task_min_role = models.CharField(
        max_length=20, default="MANAGER", 
        choices=project_constant.PROJECT_ROLES
    )
    update_task_min_role = models.CharField(
        max_length=20, default="MANAGER", 
        choices=project_constant.PROJECT_ROLES
    )
    delete_task_min_role = models.CharField(
        max_length=20, default="MANAGER", 
        choices=project_constant.PROJECT_ROLES
    )
    
    # Limits
    max_members = models.PositiveIntegerField(default=20)                         # Maximum number of members in a project
    
    # Default roles
    default_member_role = models.CharField(
        max_length=20, default="CONTRIBUTOR",
        choices=project_constant.PROJECT_ROLES
    )

    # Role_based permissions
    # Note: PROJECT_ROLES now includes GUEST (rank floor, for external
    # collaborators - see Phase B of the Org/Team/Project improvements doc).
    # It's a technically-valid but not especially meaningful floor for
    # these config fields; narrowing their choices is a separate decision.
    invite_member_min_role = models.CharField(
        max_length=20, default="MANAGER",
        choices=project_constant.PROJECT_ROLES
    )
    update_member_min_role = models.CharField(
        max_length=20, default="MANAGER",
        choices=project_constant.PROJECT_ROLES
    )
    remove_member_min_role = models.CharField(
        max_length=20, default="MANAGER",
        choices=project_constant.PROJECT_ROLES
    )
    
    # ---- Inherit Settings ----
    inherit_base_rules_from_team = models.BooleanField(default=False)
    inherit_base_rules_from_org = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Project Settings - {self.project.name}"