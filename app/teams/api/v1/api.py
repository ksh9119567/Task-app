import logging

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from app.teams.models import Team
from app.teams.api.v1.serializers import (
    TeamSerializer, TeamCreateSerializer, TeamMembershipSerializer, TeamUpdateSerializer, 
    TeamMemberUpdateSerializer, InviteMemberSerializer,
)
from app.teams.filters import TeamFilter, TeamMembershipFilter
from app.teams.services.team_invite_service import send_team_invite
from app.teams.services.team_membership_service import (
    remove_team_member, self_remove_team_member, update_team_member_role,
)
from app.teams.services.team_service import (
    transfer_team_ownership, delete_team,
)

from app.accounts.models import User

from services.invite_token_service import verify_invite_token

from core.utils.base_utils import get_user, add_member
from core.utils.org_utils import get_org, get_org_membership
from core.utils.team_utils import get_team, get_all_team_memberships, get_team_membership
from core.pagination import StandardPagination
from core.constants.team_constant import TEAM_ROLE_HIERARCHY, TEAM_ACTION_POLICIES
from core.constants.org_constant import ORG_ROLE_HIERARCHY
from core.permissions.base import get_team_role, get_org_role

from app.governance.services.rules_engine import GovernanceResolver
from core.permissions.mixins import RoleCheckerMixin, EnforceObjectPermissionsMixin
from core.permissions.organization import IsOrganizationPart
from core.permissions.team import IsTeamMember
from core.permissions.combined import IsOrgOwnerOrTeamManager, IsOrgOwnerOrTeamOwner

logger = logging.getLogger(__name__)


class TeamAPI(EnforceObjectPermissionsMixin, RoleCheckerMixin, viewsets.ViewSet):
    """
    Team API (v1)
    """
    queryset = Team.objects.all()
    pagination_class = StandardPagination()
    search_fields = ["name", "description"]
    
    def get_permissions(self):
        if self.action in ["list", "create", "retrieve", "members"]:
            permissions = [IsAuthenticated]
        elif self.action == "org_teams":
            permissions = [IsAuthenticated, IsOrganizationPart]    
        elif self.action in ["self_remove_member"]:
            permissions = [IsAuthenticated, IsTeamMember]
        elif self.action in ["send_invite", "add_member", "remove_member", "update_member"]:
            permissions = [IsAuthenticated, IsOrgOwnerOrTeamManager]
        elif self.action in ["update", "transfer_owner", "destroy"]:
            permissions = [IsAuthenticated, IsOrgOwnerOrTeamOwner]
        else:
            permissions = [IsAuthenticated]
        
        return [permission() for permission in permissions]
    
    def get_permission_object(self):
        if self.action == "org_teams":
            return get_org(self.request.query_params.get("org_id"))
        # update/destroy/send_invite/remove_member all take team_id in the
        # request body, not as a query param — must match the action bodies
        # below or the automatic check resolves team=None and denies wrongly.
        if self.action in ["update", "destroy", "send_invite", "remove_member"]:
            team_id = self.request.data.get("team_id")
        else:
            team_id = self.request.query_params.get("team_id")
        return get_team(team_id)
    
    def check_role_permissions(self, request, team):
        role = get_team_role(request.user, team)
        
        if role == "OWNER":
            return True
        elif self.action == "send_invite":
            if team.settings.allow_member_invites == False:
                raise ValidationError("You are not allowed to invite members.")

            policy_action = "invite_member"
        elif self.action == "update_member":
            if team.settings.allow_member_updates == False:
                raise ValidationError("You are not allowed to update members.")

            policy_action = "update_member"
        elif self.action == "remove_member":
            if team.settings.allow_member_removal == False:
                raise ValidationError("You are not allowed to remove members.")

            policy_action = "remove_member"
        else:
            return

        # Clamp the configured minimum role to the action's system min/max bounds.
        min_role_required = GovernanceResolver.resolve_action_min_role(
            team.settings, policy_action, TEAM_ACTION_POLICIES, TEAM_ROLE_HIERARCHY
        )
        if not self.has_minimum_role(role, min_role_required, TEAM_ROLE_HIERARCHY):
            raise ValidationError(f"You must have at least {min_role_required} role to perform this action.")

        return True
    
    def check_user_permission(self, org_id, user):
        if self.action == "create" and org_id is not None:
            try:
                org = get_org_membership(org_id, user).organization
            except NotFound as e:
                raise NotFound("Either Organization does not exist or you are not a member of it.")

            org_role = get_org_role(user, org)
            min_role_required = org.settings.create_team_min_role

            # The flag gates non-owners only; the owner can always create.
            if org_role != "OWNER" and org.settings.allow_team_creation == False:
                raise ValidationError("You are not allowed to create teams in this organization.")

            if not self.has_minimum_role(org_role, min_role_required, ORG_ROLE_HIERARCHY):
                raise ValidationError(f"You must have at least {min_role_required} role to perform this action.")

            return True

        else:
            return True
    
    def check_user_team_permission(self, user, team):
        try:
            if get_team_membership(team.id, user):
                return True
        except ValidationError as e:
            if team.organization_id:
                id = team.organization_id
                org = get_org_membership(id, user).organization
                if org:
                    return True
            else:
                raise e
    
    def get_serializer_class(self):
        if self.action == "create":
            return TeamCreateSerializer
        if self.action == "send_invite":
            return InviteMemberSerializer
        if self.action == "update":
            return TeamUpdateSerializer
        if self.action == "update_member":
            return TeamMemberUpdateSerializer
        else:
            return TeamSerializer

    def get_filterset_class(self):
        if self.action == "members":
            return TeamMembershipFilter
        return TeamFilter
    
    def get_ordering_fields(self):
        if self.action == "members":
            return ["joined_at"]
        return ["created_at"]
        
    def apply_filters(self, request, queryset):
        self.ordering_fields = self.get_ordering_fields()
        
        django_filter = DjangoFilterBackend()
        queryset = django_filter.filter_queryset(request, queryset, self)
        
        search_filter = SearchFilter()
        queryset = search_filter.filter_queryset(request, queryset, self)
        
        ordering_filter = OrderingFilter()
        queryset = ordering_filter.filter_queryset(request, queryset, self)
        
        return queryset

    def list(self, request):
        logger.info(f"Listing teams for user: {request.user.email}")
        teams = self.apply_filters(request, Team.objects.filter(memberships__user=request.user, is_deleted=False))
        
        page = self.pagination_class.paginate_queryset(teams, request)
        logger.debug(f"Found {len(page)} teams for user: {request.user.email}")
        
        return self.pagination_class.get_paginated_response({
            "message": "Success", 
            "data": TeamSerializer(page, many=True).data}
        )

    def create(self, request):
        logger.info(f"Creating team by user: {request.user.email}, name: {request.data.get('name')}")
        org_id = request.data.get("organization_id") if request.data.get("organization_id") else None
        self.check_user_permission(org_id, request.user)
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        team = serializer.save()
        logger.info(f"Team created successfully: {team.name} by {request.user.email}")
        return Response({
            "message": "Team created successfully", 
            "data": TeamSerializer(team).data},
            status=status.HTTP_201_CREATED,
        )
    
    def retrieve(self, request):
        team_id = request.query_params.get("team_id")
        logger.info(f"Retrieving team: {team_id} by user: {request.user.email}")
        team = get_team(team_id)
        logger.debug(f"Team retrieved: {team.name}")
        self.check_user_team_permission(request.user, team)

        return Response({
            "message": "Success", 
            "data": TeamSerializer(team).data},
            status=status.HTTP_200_OK,
        )
        
    def update(self, request):
        team_id = request.data.get("team_id")
        logger.info(f"Updating team: {team_id} by user: {request.user.email}")
        team = self.permission_object

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            team,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Team updated successfully: {team.name}")

        return Response({
            "message": "Team updated successfully", 
            "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request):
        team_id = request.data.get("team_id")
        logger.info(f"Deleting team: {team_id} by user: {request.user.email}")
        team = self.permission_object

        delete_team(
            team=team,
            performed_by=request.user,
        )
        logger.info(f"Team deleted successfully: {team.name}")

        return Response({
            "message": "Team deleted successfully"},
            status=status.HTTP_200_OK,
        )
        
    # --------------------------------------------------
    # Custom Actions
    # --------------------------------------------------
    @action(detail=True, methods=["get"])
    def org_teams(self, request):
        org = self.permission_object
        logger.info(f"Gettings all teams for that org: {org.name}")
        teams = Team.objects.filter(organization=org, is_deleted=False)
        
        page = self.pagination_class.paginate_queryset(teams, request)
        logger.debug(f'Found {len(page)} teams for org: {org.name}')
        
        return self.pagination_class.get_paginated_response({
            "message": "Success", 
            "data": TeamSerializer(page, many=True).data}
        )
    
    @action(detail=True, methods=["get"])
    def members(self, request):
        team_id = request.query_params.get("team_id")
        logger.info(f"Listing members for team: {team_id} by user: {request.user.email}")
        team = get_team(team_id)
        self.check_user_team_permission(request.user, team)
        
        members = get_all_team_memberships(team_id)

        page = self.pagination_class.paginate_queryset(members, request)
        logger.debug(f"Found {len(page)} members for team: {team.name}")
        
        return self.pagination_class.get_paginated_response({
            "message": "Success", 
            "data": TeamMembershipSerializer(page, many=True).data}
        )

    @action(detail=True, methods=["delete"])
    def self_remove_member(self, request):
        team_id = request.query_params.get("team_id")
        logger.info(f"Self-remove from team: {team_id} by user: {request.user.email}")
        team = self.permission_object

        self_remove_team_member(
            team=team,
            user=request.user,
        )
        logger.info(f"User self-removed from team: {team.name}")

        return Response({
            "message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )
        
    @action(detail=True, methods=["post"])
    def send_invite(self, request):
        team_id = request.data.get("team_id")
        email = request.data.get("email")
        logger.info(f"Sending invite to {email} for team: {team_id} by user: {request.user.email}")
        team = self.permission_object

        is_org_owner = False
        if team.organization_id:
            org = get_org_membership(team.organization_id, request.user).organization
            is_org_owner = get_org_role(request.user, org) == "OWNER"
        
        if not is_org_owner:
            self.check_role_permissions(request, team)

        
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

        invite_token = send_team_invite(
            team=team,
            user=user,
            invited_by=request.user,
            role=request.data.get("role", "MEMBER"),
        )
        logger.info(f"Invite sent successfully to {email} for team: {team.name}")

        return Response({
            "message": "Invite sent", 
            "invite_token": invite_token},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def accept_invite(self, request):
        logger.info(f"Accepting team invite for user: {request.user.email}")
        invite_token = request.query_params.get('invite_token')
        
        response = verify_invite_token(request_user=request.user, invite_type="team", token=invite_token)
        membership = add_member(payload=response)
        logger.info(f"Team invite accepted successfully for user: {request.user.email}")
        
        return Response({
            "message": "Invite accepted successfully", 
            "data": TeamMembershipSerializer(membership).data}, 
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["put"])
    def update_member(self, request):
        team_id = request.query_params.get("team_id")
        email = request.data.get("email")
        logger.info(f"Updating member {email} in team: {team_id} by user: {request.user.email}")
        team = self.permission_object

        is_org_owner = False
        if team.organization_id:
            org = get_org_membership(team.organization_id, request.user).organization
            is_org_owner = get_org_role(request.user, org) == "OWNER"
        
        if not is_org_owner:
            self.check_role_permissions(request, team)

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
                "team": team,
            },
        )
        serializer.is_valid(raise_exception=True)

        membership = update_team_member_role(
            team=team,
            user=target_user,
            role=serializer.validated_data["role"],
        )
        logger.info(f"Member {email} updated in team: {team.name}")

        return Response({
            "message": "Team member updated successfully",
            "data": TeamMembershipSerializer(membership).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def remove_member(self, request):
        team_id = request.data.get("team_id")
        email = request.data.get("email")
        logger.info(f"Removing member {email} from team: {team_id} by user: {request.user.email}")
        team = self.permission_object

        is_org_owner = False
        if team.organization_id:
            org = get_org_membership(team.organization_id, request.user).organization
            is_org_owner = get_org_role(request.user, org) == "OWNER"
        
        if not is_org_owner:
            self.check_role_permissions(request, team)

        user = get_user(email, kind="email")
        if not user:
            logger.warning(f"User not found for removal: {email}")
            raise NotFound("User not found")

        remove_team_member(
            team=team,
            user=user,
            performed_by=request.user,
        )
        logger.info(f"Member {email} removed from team: {team.name}")

        return Response({
            "message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["put"])
    def transfer_owner(self, request):
        team_id = request.query_params.get("team_id")
        email = request.data.get("email")
        logger.info(f"Transferring manager of team: {team_id} to {email} by user: {request.user.email}")
        team = self.permission_object

        new_owner = get_user(email, kind="email")
        if not new_owner:
            logger.warning(f"User not found for manager transfer: {email}")
            raise NotFound("User not found")

        transfer_team_ownership(
            team=team,
            new_owner=new_owner,
            performed_by=request.user,
        )
        logger.info(f"Manager transferred to {email} for team: {team.name}")

        return Response({
            "message": "Team manager updated successfully", 
            "data": TeamSerializer(team).data},
            status=status.HTTP_200_OK,
        )
