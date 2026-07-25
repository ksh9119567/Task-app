from rest_framework import serializers

from app.projects.models import Project, ProjectMembership, ProjectTeam
from app.projects.services.project_team_service import assign_team, update_team_link, unassign_team

from app.organizations.models import Organization
from app.teams.models import Team

from core.permissions.base import get_org_role, get_team_role
from core.permissions.resolver import effective_role
from core.utils.project_utils import get_project
from core.constants.project_constant import PROJECT_ROLES, PROJECT_ROLE_HIERARCHY
from core.constants.org_constant import ORG_ROLE_HIERARCHY
from core.constants.team_constant import TEAM_ROLE_HIERARCHY

# Roles a team link may carry. OWNER is excluded - a whole team becoming
# "Owner" via most-permissive-wins would conflict with the single permanent
# Owner principle. GUEST is excluded - it's an individual-explicit-member
# concept, not a team-wide one.
TEAM_ASSIGNABLE_ROLES = [r[0] for r in PROJECT_ROLES if r[0] not in ("OWNER", "GUEST")]


class ProjectTeamSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    assigned_by_email = serializers.EmailField(source="assigned_by.email", read_only=True)

    class Meta:
        model = ProjectTeam
        fields = ["team", "team_name", "role", "is_owning", "assigned_by", "assigned_by_email", "created_at"]


class AssignTeamSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=TEAM_ASSIGNABLE_ROLES)
    is_owning = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        request = self.context["request"]
        project = self.context["project"]

        try:
            team = Team.objects.get(id=attrs["team_id"])
        except Team.DoesNotExist:
            raise serializers.ValidationError("Team not found.")

        if project.organization_id and team.organization_id != project.organization_id:
            raise serializers.ValidationError("Team and Project does not belong to same organization.")

        team_role_check = get_team_role(request.user, team)
        team_min_role = team.settings.create_project_min_role
        if TEAM_ROLE_HIERARCHY.get(team_role_check, -1) < TEAM_ROLE_HIERARCHY[team_min_role]:
            raise serializers.ValidationError("You do not have permission to assign this team to the project.")

        attrs["team"] = team
        return attrs


class UpdateTeamRoleSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=TEAM_ASSIGNABLE_ROLES, required=False)
    is_owning = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if "role" not in attrs and "is_owning" not in attrs:
            raise serializers.ValidationError("Provide at least role or is_owning to update.")

        try:
            team = Team.objects.get(id=attrs["team_id"])
        except Team.DoesNotExist:
            raise serializers.ValidationError("Team not found.")

        attrs["team"] = team
        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    team = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()
    team_role = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "organization", "organization_name",
            "team", "team_name", "team_role", "status", "created_by", "created_by_email", "member_count",
            "created_at"
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_team(self, obj):
        link = obj.team_link
        return link.team_id if link else None

    def get_team_name(self, obj):
        link = obj.team_link
        return link.team.name if link else None

    def get_team_role(self, obj):
        link = obj.team_link
        return link.role if link else None


class ProjectCreateSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(write_only=True, required = False, allow_null=True)
    team_id = serializers.UUIDField(write_only=True, required = False, allow_null=True)
    team_role = serializers.ChoiceField(choices=TEAM_ASSIGNABLE_ROLES, write_only=True, required=False)

    class Meta:
        model=Project
        fields = ["name", "description", "organization_id", "team_id", "team_role"]

    def validate(self, attrs):
        request = self.context["request"]
        org_id = attrs.get("organization_id", None)
        team_id = attrs.get("team_id", None)

        if attrs.get("team_role") and not team_id:
            raise serializers.ValidationError("team_role requires a team_id.")

        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
                if org.settings.max_projects == org.projects.count():
                    raise serializers.ValidationError("Organization has reached maximum project limit.")
                
            except Organization.DoesNotExist:
                raise serializers.ValidationError("Organization not found.")
            
            role = get_org_role(request.user, org)
            min_role = org.settings.create_project_min_role
            if ORG_ROLE_HIERARCHY[role] < ORG_ROLE_HIERARCHY[min_role]:
                raise serializers.ValidationError("You do not have permission to create a project in this organization.")
            
            attrs["organization"] = org
            
            if team_id:
                try:
                    team = Team.objects.get(id=team_id)
                    if team.organization != org:
                        raise serializers.ValidationError("Team and Project does not belong to same organization.")

                except Team.DoesNotExist:
                    raise serializers.ValidationError("Team not found.")

                team_role_check = get_team_role(request.user, team)
                team_min_role = team.settings.create_project_min_role
                if TEAM_ROLE_HIERARCHY.get(team_role_check, -1) < TEAM_ROLE_HIERARCHY[team_min_role]:
                    raise serializers.ValidationError("You do not have permission to assign this team to the project.")

                attrs["team"] = team
        
        elif team_id:
            try:
                team = Team.objects.get(id=team_id)
                if team.settings.max_projects == team.projects.count():
                    raise serializers.ValidationError("Team has reached maximum project limit.")
                
            except Team.DoesNotExist:
                raise serializers.ValidationError("Team not found.")
            
            role = get_team_role(request.user, team)
            min_role = team.settings.create_project_min_role
            
            if TEAM_ROLE_HIERARCHY[role] < TEAM_ROLE_HIERARCHY[min_role]:
                raise serializers.ValidationError("You do not have permission to create a project in this team.")
            
            attrs["team"] = team
        
        return attrs
    
    def create(self, validated_data):
        request = self.context["request"]
        org = validated_data.pop("organization", None)
        team = validated_data.pop("team", None)
        team_role = validated_data.pop("team_role", None)
        validated_data.pop("team_id", None)

        project = Project.objects.create(created_by = request.user, **validated_data)

        if org:
            project.organization = org
            project.save()

        if team:
            # is_owning=True: the first (and here, only) team assigned to a
            # new project is always its owning team.
            assign_team(
                project=project, team=team, role=team_role or "CONTRIBUTOR",
                is_owning=True, assigned_by=request.user,
            )

        ProjectMembership.objects.create(user=request.user, project = project, role="OWNER")
        return project
                                                             

class ProjectMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    
    class Meta:
        model = ProjectMembership
        fields = ["user", "user_email", "role", "joined_at"]
        read_only_fields = ["joined_at"]
        
        
class ProjectUpdateSerializer(serializers.ModelSerializer):
    team_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    team_role = serializers.ChoiceField(choices=TEAM_ASSIGNABLE_ROLES, write_only=True, required=False)

    class Meta:
        model = Project
        fields = ["name", "description", "status", "team_id", "team_role"]

    def validate(self, attrs):
        project = self.instance
        team_id_provided = "team_id" in attrs
        team_id = attrs.get("team_id", None)

        if team_id_provided and team_id:
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                raise serializers.ValidationError("Team not found.")
            if team.organization_id != project.organization_id:
                raise serializers.ValidationError("Team and Project does not belong to same organization.")
            attrs["team"] = team
        elif attrs.get("team_role") and not project.team_link:
            raise serializers.ValidationError("team_role requires an assigned team.")

        return attrs

    def update(self, instance, validated_data):
        # This endpoint only ever manages the OWNING team (a single, named
        # `team_id` field, matching the pre-multi-team API shape) - other
        # assigned teams (Phase C) are untouched here; use the dedicated
        # assign_team/update_team_role/unassign_team actions for those.
        team_id_provided = "team_id" in validated_data
        team = validated_data.pop("team", None)
        team_role = validated_data.pop("team_role", None)
        validated_data.pop("team_id", None)

        instance = super().update(instance, validated_data)

        if team_id_provided:
            current_owning = instance.team_link
            if team is not None:
                assign_team(
                    project=instance, team=team, role=team_role or "CONTRIBUTOR",
                    is_owning=True, assigned_by=self.context["request"].user,
                )
            elif current_owning is not None:
                unassign_team(project=instance, team=current_owning.team)
        elif team_role:
            link = instance.team_link
            if link:
                update_team_link(project=instance, team=link.team, role=team_role)

        return instance
        
class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        request = self.context["request"]
        if request.user.email == value:
            raise serializers.ValidationError("You cannot invite yourself.")
        return value
    
    
class ProjectMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[r[0] for r in PROJECT_ROLES], required=False)
    
    def validate(self, attrs):
        request = self.context["request"]
        project = self.context["project"]
        target_user = self.context["member_user"]

        acting_role = effective_role(request.user, project)
        target_role = effective_role(target_user, project)

        new_role = attrs.get("role")

        min_role = project.settings.update_member_min_role
        if PROJECT_ROLE_HIERARCHY.get(acting_role, -1) < PROJECT_ROLE_HIERARCHY[min_role]:
            raise serializers.ValidationError("You do not have permission to modify team members.")

        # Manager cannot change equal/higher roles
        if target_role and PROJECT_ROLE_HIERARCHY[target_role] >= PROJECT_ROLE_HIERARCHY.get(acting_role, -1):
            raise serializers.ValidationError("You cannot modify a member with equal or higher role.")

        if PROJECT_ROLE_HIERARCHY[new_role] >= PROJECT_ROLE_HIERARCHY.get(acting_role, -1):
            raise serializers.ValidationError("You cannot assign a role equal or higher than your own.")

        # Prevent downgrading the last manager
        if target_role == "MANAGER" and new_role != "MANAGER":
            manager_count = project.memberships.filter(role="MANAGER").count()
            if manager_count == 1:
                raise serializers.ValidationError("Cannot change the role of last remaining Manager.")
            
        return attrs