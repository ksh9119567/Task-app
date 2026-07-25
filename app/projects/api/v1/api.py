import logging

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from app.projects.models import Project
from app.projects.api.v1.serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectMembershipSerializer, ProjectUpdateSerializer,
    ProjectMemberUpdateSerializer, InviteMemberSerializer, ProjectTeamSerializer,
    AssignTeamSerializer, UpdateTeamRoleSerializer,
)
from app.projects.filters import ProjectFilter, ProjectMembershipFilter
from app.projects.services.project_invite_service import send_project_invite
from app.projects.services.project_membership_service import (
    remove_project_member, self_remove_project_member, update_project_member_role,
)
from app.projects.services.project_service import (
    transfer_project_ownership, delete_project,
)
from app.projects.services.project_team_service import (
    assign_team as assign_project_team,
    update_team_link as update_project_team_link,
    unassign_team as unassign_project_team,
)

from core.utils.base_utils import get_user, add_member
from core.utils.org_utils import get_org, get_org_membership
from core.utils.team_utils import get_team, get_team_membership
from core.utils.project_utils import (
    get_project, get_all_project_memberships, get_project_membership, get_stale_explicit_members,
)
from core.constants.project_constant import PROJECT_ROLE_HIERARCHY, PROJECT_ACTION_POLICIES
from core.constants.org_constant import ORG_ROLE_HIERARCHY
from core.constants.team_constant import TEAM_ROLE_HIERARCHY
from core.permissions.base import get_org_role, get_team_role
from core.permissions.mixins import RoleCheckerMixin, EnforceObjectPermissionsMixin
from core.permissions.project import IsProjectMember
from core.permissions.organization import IsOrganizationPart
from core.permissions.team import IsTeamMember
from core.permissions.combined import (
    IsOrgOwnerOrProjectLead, IsOrgOwnerOrProjectManager, IsOrgOwnerOrProjectOwner,
)
from core.permissions.resolver import can_override_member_policy, effective_role
from core.pagination import StandardPagination

from app.governance.services.rules_engine import GovernanceResolver

from services.invite_token_service import verify_invite_token


logger = logging.getLogger(__name__)


class ProjectAPI(EnforceObjectPermissionsMixin, RoleCheckerMixin, viewsets.ModelViewSet):
    """
    Project API (v1)
    """
    queryset = Project.objects.all()
    pagination_class = StandardPagination()
    search_fields = ["name", "description"]

    
    def get_permissions(self):
        if self.action in ["list", "create", "retrieve", "members", "teams"]:
            permissions = [IsAuthenticated]
        elif self.action in ["org_projects"]:
            permissions = [IsAuthenticated, IsOrganizationPart]
        elif self.action in ["team_projects"]:
            permissions = [IsAuthenticated, IsTeamMember]
        elif self.action in ["self_remove_member"]:
            permissions = [IsAuthenticated, IsProjectMember]
        elif self.action == "send_invite":
            # Invites are configurable down to LEAD (PROJECT_ACTION_POLICIES),
            # so the structural gate must admit Leads too; the exact per-project
            # threshold is enforced by check_role_permissions() below.
            permissions = [IsAuthenticated, IsOrgOwnerOrProjectLead]
        elif self.action in [
            "add_member", "update_member", "remove_member",
            "assign_team", "update_team_role", "unassign_team", "stale_members",
        ]:
            permissions = [IsAuthenticated, IsOrgOwnerOrProjectManager]
        elif self.action in ["update", "transfer_owner", "destroy"]:
            permissions = [IsAuthenticated, IsOrgOwnerOrProjectOwner]
        else:
            permissions = [IsAuthenticated]

        return [permission() for permission in permissions]

    def get_permission_object(self):
        if self.action == "org_projects":
            return get_org(self.request.query_params.get("org_id"))
        if self.action == "team_projects":
            return get_team(self.request.query_params.get("team_id"))
        if self.action in ["update", "destroy"]:
            project_id = self.request.data.get("project_id")
        else:
            project_id = self.request.query_params.get("project_id")
        return get_project(project_id)

    def check_role_permissions(self, request, project):
        role = effective_role(request.user, project)

        if role == "OWNER":
            return True
        elif self.action == "send_invite":
            if project.settings.allow_member_invites == False:
                raise ValidationError("You are not allowed to invite members.")

            policy_action = "invite_member"
        elif self.action == "update_member":
            if project.settings.allow_member_updates == False:
                raise ValidationError("You are not allowed to update members.")

            policy_action = "update_member"
        elif self.action == "remove_member":
            if project.settings.allow_member_removal == False:
                raise ValidationError("You are not allowed to remove members.")

            policy_action = "remove_member"
        else:
            return

        # Resolve the configured minimum role through the governance rules engine,
        # which clamps it to the action's system min/max bounds — a mis-set settings
        # value can never drop below (or exceed) the safe band.
        min_role_required = GovernanceResolver.resolve_action_min_role(
            project.settings, policy_action, PROJECT_ACTION_POLICIES, PROJECT_ROLE_HIERARCHY
        )
        if not self.has_minimum_role(role, min_role_required, PROJECT_ROLE_HIERARCHY):
            raise ValidationError(f"You must have at least {min_role_required} role to perform this action.")

        return True
    
    def check_user_permission(self, user, id):
        if self.action != "create" or id is None:
            return True

        # Resolve the scope (organization first, then team) and the acting role.
        try:
            org = get_org_membership(id, user).organization
            role = get_org_role(user, org)
            hierarchy = ORG_ROLE_HIERARCHY
            min_role_required = org.settings.create_project_min_role
            # The flag gates non-owners only; the owner can always create.
            if role != "OWNER" and org.settings.allow_project_creation == False:
                raise ValidationError("You are not allowed to create projects in this organization.")
        except NotFound:
            try:
                team = get_team_membership(id, user).team
                role = get_team_role(user, team)
                hierarchy = TEAM_ROLE_HIERARCHY
                min_role_required = team.settings.create_project_min_role
                if role != "OWNER" and team.settings.allow_project_creation == False:
                    raise ValidationError("You are not allowed to create projects in this team.")
            except NotFound:
                return True

        if not self.has_minimum_role(role, min_role_required, hierarchy):
            raise ValidationError(f"You must have at least {min_role_required} role to perform this action.")

        return True
            
    
    def check_user_project_permission(self, user, project):
        try:
            if get_project_membership(project.id, user):
                return True
        except ValidationError as e:
            if project.organization_id:
                id = project.organization_id
                org = get_org_membership(id, user).organization
                if org:
                    return True
            elif project.team_id:
                id = project.team_id
                team = get_team_membership(id, user).team
                if team and project.team_id == team.id:
                    return True
            else:
                raise e
            
    def get_serializer_class(self):
        if self.action == "create":
            return ProjectCreateSerializer
        if self.action == "update":
            return ProjectUpdateSerializer
        if self.action == "send_invite":
            return InviteMemberSerializer
        if self.action == "update_member":
            return ProjectMemberUpdateSerializer
        else:
            return ProjectSerializer

    def get_filterset_class(self):
        if self.action == "members":
            return ProjectMembershipFilter
        return ProjectFilter

    def get_search_fields(self):
        if self.action == "members":
            return ["user__email"]
        return self.search_fields
    
    def get_ordering_fields(self):
        if self.action == "members":
            return ["joined_at", "role"]
        return ["created_at"]
    
    def apply_filters(self, request, queryset):
        self.filterset_class = self.get_filterset_class()
        self.ordering_fields = self.get_ordering_fields()
        self.search_fields = self.get_search_fields()

        django_filter = DjangoFilterBackend()
        queryset = django_filter.filter_queryset(request, queryset, self)
        
        search_filter = SearchFilter()
        queryset = search_filter.filter_queryset(request, queryset, self)
        
        ordering_filter = OrderingFilter()
        queryset = ordering_filter.filter_queryset(request, queryset, self)
        
        return queryset
        
    def list(self, request):
        logger.info(f"Listing projects for user: {request.user.email}")
        projects = self.apply_filters(request, Project.objects.filter(members=request.user, is_deleted=False).distinct())

        page = self.pagination_class.paginate_queryset(projects, request)
        logger.debug(f"Found {len(page)} projects for user: {request.user.email}")
        
        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": ProjectSerializer(page, many=True).data}
        )

    def create(self, request):
        logger.info(f"Creating project by user: {request.user.email}, name: {request.data.get('name')}")
        id = request.data.get("organization_id") or request.data.get("team_id") if request.data.get("organization_id") or request.data.get("team_id") else None
        self.check_user_permission(request.user, id)
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        project = serializer.save()
        logger.info(f"Project created successfully: {project.name} by {request.user.email}")
        return Response({
            "message": "Project created successfully",    
            "data": ProjectSerializer(project).data},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Retrieving project: {project_id} by user: {request.user.email}")
        project = get_project(project_id)
        logger.debug(f"Project retrieved: {project.name}")
        self.check_user_project_permission(request.user, project)
        
        return Response({
            "message": "Success", 
            "data": ProjectSerializer(project).data},
            status=status.HTTP_200_OK,
        )

    def update(self, request):
        project_id = request.data.get("project_id")
        logger.info(f"Updating project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            project,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Project updated successfully: {project.name}")

        return Response({
            "message": "Project updated successfully",
            "data": ProjectSerializer(project).data},
            status=status.HTTP_200_OK,
        )
    
    def destroy(self, request):
        project_id = request.data.get("project_id")
        logger.info(f"Deleting project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        delete_project(
            project=project,
            performed_by=request.user,
        )
        logger.info(f"Project deleted successfully: {project.name}")

        return Response({
            "message": "Project deleted successfully"},
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------
    # Custom Actions
    # --------------------------------------------------
    @action(detail=False, methods=["get"])
    def org_projects(self, request):
        org = self.permission_object
        logger.info(f"Getting all projects for org: {org.name} by user: {request.user.email}")
        projects = Project.objects.filter(organization=org, is_deleted=False)
        
        page = self.pagination_class.paginate_queryset(projects, request)
        logger.debug(f"Found {len(page)} projects for org: {org.name}")
        return self.pagination_class.get_paginated_response({
            "message": "Success", 
            "data": ProjectSerializer(page, many=True).data}
        )
    
    @action(detail=False, methods=["get"])
    def team_projects(self, request):
        team = self.permission_object
        logger.info(f"Getting all projects for team: {team.name} by user: {request.user.email}")
        projects = Project.objects.filter(team_links__team_id=team.id, is_deleted=False)
        
        page = self.pagination_class.paginate_queryset(projects, request)
        logger.debug(f"Found {len(page)} projects for team: {team.name}")
        return self.pagination_class.get_paginated_response({
            "message": "Success", 
            "data": ProjectSerializer(page, many=True).data}
        )
    
    @action(detail=True, methods=["get"])
    def members(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Listing members for project: {project_id} by user: {request.user.email}")
        project = get_project(project_id)
        self.check_user_project_permission(request.user, project)

        members = self.apply_filters(request, get_all_project_memberships(project.id))

        page = self.pagination_class.paginate_queryset(members, request)
        logger.debug(f"Found {len(page)} members for project: {project.name}")
        
        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": ProjectMembershipSerializer(page, many=True).data}
        )

    @action(detail=True, methods=["get"])
    def teams(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Listing teams for project: {project_id} by user: {request.user.email}")
        project = get_project(project_id)
        self.check_user_project_permission(request.user, project)

        links = project.team_links.select_related("team").order_by("-is_owning", "created_at")

        return Response({
            "message": "Success",
            "data": ProjectTeamSerializer(links, many=True).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def stale_members(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Listing stale explicit members for project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        stale = get_stale_explicit_members(project)
        page = self.pagination_class.paginate_queryset(stale, request)

        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": ProjectMembershipSerializer(page, many=True).data}
        )

    @action(detail=True, methods=["post"])
    def assign_team(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Assigning team to project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        serializer = AssignTeamSerializer(data=request.data, context={"request": request, "project": project})
        serializer.is_valid(raise_exception=True)
        team = serializer.validated_data["team"]

        link = assign_project_team(
            project=project,
            team=team,
            role=serializer.validated_data["role"],
            is_owning=serializer.validated_data.get("is_owning", False),
            assigned_by=request.user,
        )
        logger.info(f"Team {team.name} assigned to project: {project.name}")

        return Response({
            "message": "Team assigned successfully",
            "data": ProjectTeamSerializer(link).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["put"])
    def update_team_role(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Updating team link for project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        serializer = UpdateTeamRoleSerializer(data=request.data, context={"project": project})
        serializer.is_valid(raise_exception=True)
        team = serializer.validated_data["team"]

        link = update_project_team_link(
            project=project,
            team=team,
            role=serializer.validated_data.get("role"),
            is_owning=serializer.validated_data.get("is_owning"),
        )
        logger.info(f"Team {team.name} link updated for project: {project.name}")

        return Response({
            "message": "Team updated successfully",
            "data": ProjectTeamSerializer(link).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def unassign_team(self, request):
        project_id = request.query_params.get("project_id")
        team_id = request.data.get("team_id")
        logger.info(f"Unassigning team {team_id} from project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        team = get_team(team_id)
        unassign_project_team(project=project, team=team)
        logger.info(f"Team {team.name} unassigned from project: {project.name}")

        return Response({
            "message": "Team unassigned successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def self_remove_member(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Self-remove from project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        self_remove_project_member(
            project=project,
            user=request.user,
        )
        logger.info(f"User self-removed from project: {project.name}")

        return Response({
            "message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def send_invite(self, request):
        project_id = request.query_params.get("project_id")
        email = request.data.get("email")
        logger.info(f"Sending invite to {email} for project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        if not can_override_member_policy(request.user, project):
            self.check_role_permissions(request, project)
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = get_user(serializer.validated_data["email"], kind="email")
        if not user:
            logger.warning(f"User not found for invite: {email}")
            raise NotFound("User not found")

        invite_token = send_project_invite(
            project=project,
            user=user,
            invited_by=request.user,
            role=request.data.get("role", "CONTRIBUTOR"),
        )
        logger.info(f"Invite sent successfully to {email} for project: {project.name}")

        return Response({
            "message": "Invite sent", 
            "invite_token": invite_token},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def accept_invite(self, request):
        logger.info(f"Accepting project invite for user: {request.user.email}")
        invite_token = request.query_params.get('invite_token')
        
        response = verify_invite_token(request_user=request.user, invite_type="project", token=invite_token)
        membership = add_member(payload=response)
        logger.info(f"Project invite accepted successfully for user: {request.user.email}")
        
        return Response({
            "message": "Invite accepted successfully", 
            "data": ProjectMembershipSerializer(membership).data}, 
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["put"])
    def update_member(self, request):
        project_id = request.query_params.get("project_id")
        email = request.data.get("email")
        logger.info(f"Updating member {email} in project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        if not can_override_member_policy(request.user, project):
            self.check_role_permissions(request, project)

        target_user = get_user(email, kind="email")
        if not target_user:
            logger.warning(f"User not found for update: {email}")
            raise NotFound("User not found")

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data={"role": request.data.get("role")},
            context={
                "request": request,
                "member_user": target_user,
                "project": project,
            },
        )
        serializer.is_valid(raise_exception=True)

        membership = update_project_member_role(
            project=project,
            user=target_user,
            role=serializer.validated_data["role"],
        )
        logger.info(f"Member {email} updated in project: {project.name}")

        return Response({
            "message": "Project member updated successfully",
            "data": ProjectMembershipSerializer(membership).data},
            status=status.HTTP_200_OK,
        )
        
    @action(detail=True, methods=["delete"])
    def remove_member(self, request):
        project_id = request.query_params.get("project_id")
        email = request.data.get("email")
        logger.info(f"Removing member {email} from project: {project_id} by user: {request.user.email}")
        project = self.permission_object

        if not can_override_member_policy(request.user, project):
            self.check_role_permissions(request, project)
        
        user = get_user(email, kind="email")
        if not user:
            logger.warning(f"User not found for removal: {email}")
            raise NotFound("User not found")

        remove_project_member(
            project=project,
            user=user,
            performed_by=request.user,
        )
        logger.info(f"Member {email} removed from project: {project.name}")

        return Response({
            "message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["put"])
    def transfer_owner(self, request):
        project_id = request.query_params.get("project_id")
        email = request.data.get("email")
        logger.info(f"Transferring ownership of project: {project_id} to {email} by user: {request.user.email}")
        project = self.permission_object

        new_owner = get_user(email, kind="email")
        if not new_owner:
            logger.warning(f"User not found for ownership transfer: {email}")
            raise NotFound("User not found")

        transfer_project_ownership(
            project=project,
            new_owner=new_owner,
            performed_by=request.user,
        )
        logger.info(f"Ownership transferred to {email} for project: {project.name}")

        return Response({
            "message": "Project owner updated successfully"},
            status=status.HTTP_200_OK,
        )

