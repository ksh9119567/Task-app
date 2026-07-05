from rest_framework import serializers

from app.projects.models import Project, ProjectMembership

from app.organizations.models import Organization
from app.teams.models import Team

from core.permissions.base import get_org_role, get_team_role, get_project_role
from core.utils.project_utils import get_project
from core.constants.project_constant import PROJECT_ROLES, PROJECT_ROLE_HIERARCHY
from core.constants.org_constant import ORG_ROLE_HIERARCHY
from core.constants.team_constant import TEAM_ROLE_HIERARCHY

class ProjectSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    
    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "organization", "organization_name",
            "team", "team_name", "status", "created_by", "created_by_email", "member_count",
            "created_at"
        ]
        
    def get_member_count(self, obj):
        return obj.members.count()
    

class ProjectCreateSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(write_only=True, required = False, allow_null=True)
    team_id = serializers.UUIDField(write_only=True, required = False, allow_null=True)
    
    class Meta:
        model=Project
        fields = ["name", "description", "organization_id", "team_id"]
        
    def validate(self, attrs):
        request = self.context["request"]
        org_id = attrs.get("organization_id", None)
        team_id = attrs.get("team_id", None)
        
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
        
        project = Project.objects.create(created_by = request.user, **validated_data)
        
        if org:
            project.organization = org
            project.save()
        
        if team:
            project.team = team
            project.save()
            
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
    class Meta:
        model = Project
        fields = ["name", "description", "status", "team_id"]
        
    def validate(self, attrs):
        request = self.context["request"]
        team_id = attrs.get("team_id", None)
        project = self.instance
        
        if team_id:
            try:
                team = Team.objects.get(id=team_id)
                if team.organization != project.organization:
                    raise serializers.ValidationError("Team and Project does not belong to same organization.")
            except Team.DoesNotExist:
                raise serializers.ValidationError("Team not found.")
    
            attrs["team"] = team
        
        return attrs
        
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

        acting_role = get_project_role(request.user, project)
        target_role = get_project_role(target_user, project)

        new_role = attrs.get("role")
        
        min_role = project.settings.update_member_min_role
        if PROJECT_ROLE_HIERARCHY[acting_role] < PROJECT_ROLE_HIERARCHY[min_role]:
            raise serializers.ValidationError("You do not have permission to modify team members.")

        # Manager cannot change equal/higher roles
        if target_role and PROJECT_ROLE_HIERARCHY[target_role] >= PROJECT_ROLE_HIERARCHY[acting_role]:
            raise serializers.ValidationError("You cannot modify a member with equal or higher role.")

        if PROJECT_ROLE_HIERARCHY[new_role] >= PROJECT_ROLE_HIERARCHY[acting_role]:
            raise serializers.ValidationError("You cannot assign a role equal or higher than your own.")

        # Prevent downgrading the last manager
        if target_role == "MANAGER" and new_role != "MANAGER":
            manager_count = project.memberships.filter(role="MANAGER").count()
            if manager_count == 1:
                raise serializers.ValidationError("Cannot change the role of last remaining Manager.")
            
        return attrs