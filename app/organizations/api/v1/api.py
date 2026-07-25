import logging

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from app.organizations.models import Organization
from app.organizations.filters import OrganizationFilter, OrganizationMembershipFilter
from app.organizations.services.organization_invite_service import send_organization_invite
from app.organizations.api.v1.serializers import (
    OrganizationSerializer, OrganizationCreateSerializer, OrganizationUpdateSerializer,
    OrganizationMembershipSerializer, InviteMemberSerializer, OrganizationMemberUpdateSerializer,
)
from app.organizations.services.organization_membership_service import (
    remove_member, self_remove, update_role,
)
from app.organizations.services.organization_service import (
    transfer_ownership, delete_organization,
)

from core.utils.base_utils import add_member, get_user
from core.utils.org_utils import get_org, get_all_org_memberships
from core.constants.org_constant import ORG_ROLE_HIERARCHY, ORG_ACTION_POLICIES
from core.permissions.base import get_org_role

from app.governance.services.rules_engine import GovernanceResolver
from core.permissions.mixins import RoleCheckerMixin, EnforceObjectPermissionsMixin
from core.permissions.organization import (
    IsOrganizationMember, IsOrganizationOwner, IsOrganizationPart, IsOrganizationManager
)
from core.pagination import StandardPagination

from services.invite_token_service import verify_invite_token

logger = logging.getLogger(__name__)


class OrganizationAPI(
        EnforceObjectPermissionsMixin, RoleCheckerMixin, viewsets.ModelViewSet
    ):
    """
    Organization API (v1)
    """
    queryset = Organization.objects.all()
    pagination_class = StandardPagination()
    search_fields = ["name"]

    def get_permissions(self):
        if self.action in ["list", "create"]:
            permissions = [IsAuthenticated]
        elif self.action in ["retrieve", "members"]:
            permissions = [IsAuthenticated, IsOrganizationPart]
        elif self.action == "self_remove_member":
            permissions = [IsAuthenticated, IsOrganizationMember]
        elif self.action in ["send_invite", "add_member", "update_member", "remove_member"]:
            permissions = [IsAuthenticated, IsOrganizationManager]
        elif self.action in ["update", "transfer_owner", "destroy"]:
            permissions = [IsAuthenticated, IsOrganizationOwner]
        else:
            permissions = [IsAuthenticated]

        return [permission() for permission in permissions]
    
    def get_permission_object(self):
        org_id = self.request.query_params.get("org_id")
        return get_org(org_id) if org_id else None
            
    def check_role_permissions(self, request, organization):
        role = get_org_role(request.user, organization)
        
        min_role_required = None
        
        if role == "OWNER":
            return True
        elif self.action == "send_invite":
            if organization.settings.allow_member_invites == False:
                raise ValidationError("You are not allowed to invite members.")

            policy_action = "invite_member"
        elif self.action == "update_member":
            if organization.settings.allow_member_updates == False:
                raise ValidationError("You are not allowed to update members.")

            policy_action = "update_member"
        elif self.action == "remove_member":
            if organization.settings.allow_member_removal == False:
                raise ValidationError("You are not allowed to remove members.")

            policy_action = "remove_member"
        else:
            return

        # Clamp the configured minimum role to the action's system min/max bounds.
        min_role_required = GovernanceResolver.resolve_action_min_role(
            organization.settings, policy_action, ORG_ACTION_POLICIES, ORG_ROLE_HIERARCHY
        )
        if not self.has_minimum_role(role, min_role_required, ORG_ROLE_HIERARCHY):
            raise ValidationError(f"You must have at least {min_role_required} role to perform this action.")

        return True
    
    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationCreateSerializer
        if self.action == "update":
            return OrganizationUpdateSerializer
        if self.action == "send_invite":
            return InviteMemberSerializer
        if self.action == "update_member":
            return OrganizationMemberUpdateSerializer

    def get_filterset_class(self):
        if self.action == "members":
            return OrganizationMembershipFilter
        return OrganizationFilter
    
    def get_ordering_fields(self):
        if self.action == "members":
            return ["joined_at"]
        return ["created_at"]

    def apply_filters(self, request, queryset):
        self.filterset_class = self.get_filterset_class()
        self.ordering_fields = self.get_ordering_fields()
        
        django_filter = DjangoFilterBackend()
        queryset = django_filter.filter_queryset(request, queryset, self)
        
        search_filter = SearchFilter()
        queryset = search_filter.filter_queryset(request, queryset, self)
        
        ordering_filter = OrderingFilter()
        queryset = ordering_filter.filter_queryset(request, queryset, self)
        
        return queryset
        
    def list(self, request):
        logger.info(f"Listing organizations for user: {request.user.email}")
        orgs = self.apply_filters(request, Organization.objects.filter(memberships__user=request.user, is_deleted=False).distinct())
        
        page = self.pagination_class.paginate_queryset(orgs, request)
        logger.debug(f"Found {len(page)} organizations for user: {request.user.email}")
        
        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": OrganizationSerializer(page, many=True).data}
        )

    def create(self, request):
        logger.info(f"Creating organization by user: {request.user.email}, name: {request.data.get('name')}")
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        org = serializer.save()
        logger.info(f"Organization created successfully: {org.name} by {request.user.email}")
        return Response({
            "message": "Organization created successfully",
            "data": OrganizationSerializer(org).data},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request):
        org_id = request.query_params.get("org_id")
        logger.info(f"Retrieving organization: {org_id} by user: {request.user.email}")
        org = self.permission_object
        logger.debug(f"Organization retrieved: {org.name}")
        
        return Response({
            "message": "Success",
            "data": OrganizationSerializer(org).data}, 
            status=status.HTTP_200_OK
        )

    def update(self, request):
        org_id = request.query_params.get("org_id")
        logger.info(f"Updating organization: {org_id} by user: {request.user.email}")
        org = self.permission_object

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            org,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Organization updated successfully: {org.name}")

        return Response({
            "message": "Organization updated successfully", 
            "data": OrganizationSerializer(org).data}, 
            status=status.HTTP_200_OK
        )

    def destroy(self, request):
        org_id = request.query_params.get("org_id")
        logger.info(f"Deleting organization: {org_id} by user: {request.user.email}")
        org = self.permission_object

        delete_organization(
            organization=org,
            performed_by=request.user,
        )
        logger.info(f"Organization deleted successfully: {org.name}")

        return Response(
            {"message": "Organization deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )

    # --------------------------------------------------
    # Custom Actions
    # --------------------------------------------------
    @action(detail=True, methods=["get"])
    def members(self, request):
        org_id = request.query_params.get("org_id")
        logger.info(f"Listing members for organization: {org_id} by user: {request.user.email}")
        org = self.permission_object

        members = get_all_org_memberships(org.id)

        page = self.pagination_class.paginate_queryset(members, request)
        logger.debug(f"Found {len(page)} members for organization: {org.name}")
        
        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": OrganizationMembershipSerializer(page, many=True).data}
        )

    @action(detail=True, methods=["delete"])
    def self_remove_member(self, request):
        org_id = request.query_params.get("org_id")
        logger.info(f"Self-remove from organization: {org_id} by user: {request.user.email}")
        org = self.permission_object

        self_remove(
            organization=org,
            user=request.user,
        )
        logger.info(f"User self-removed from organization: {org.name}")

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def send_invite(self, request):
        org_id = request.query_params.get("org_id")
        email = request.data.get("email")
        logger.info(f"Sending invite to {email} for organization: {org_id} by user: {request.user.email}")
        org = self.permission_object
        self.check_role_permissions(request, org)
                
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

        invite_token = send_organization_invite(
            organization=org,
            user=user,
            invited_by=request.user,
            role=request.data.get("role", "MEMBER"),
        )
        logger.info(f"Invite sent successfully to {email} for organization: {org.name}")

        return Response({
            "message": "Invite sent successfully",
            "invite_token": invite_token},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def accept_invite(self, request):
        logger.info(f"Accepting organization invite for user: {request.user.email}")
        invite_token = request.query_params.get('invite_token')
        
        response = verify_invite_token(request_user=request.user, invite_type="organization", token=invite_token)
        membership = add_member(payload=response)
        logger.info(f"Organization invite accepted successfully for user: {request.user.email}")
        
        return Response({
            "message": "Invite accepted successfully", 
            "data": OrganizationMembershipSerializer(membership).data}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["patch"])
    def update_member(self, request):
        org_id = request.query_params.get("org_id")
        email = request.data.get("email")
        logger.info(f"Updating member {email} in organization: {org_id} by user: {request.user.email}")
        org = self.permission_object
        self.check_role_permissions(request, org)
        
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
                "organization": org,
            },
        )
        serializer.is_valid(raise_exception=True)

        membership = update_role(
            organization=org,
            user=target_user,
            role=serializer.validated_data["role"],
        )
        logger.info(f"Member {email} updated in organization: {org.name}")

        return Response({
            "message": "Member updated successfully",
            "data": OrganizationMembershipSerializer(membership).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def transfer_owner(self, request):
        org_id = request.query_params.get("org_id")
        email = request.data.get("email")
        logger.info(f"Transferring ownership of organization: {org_id} to {email} by user: {request.user.email}")
        org = self.permission_object

        new_owner = get_user(email, kind="email")
        if not new_owner:
            logger.warning(f"User not found for ownership transfer: {email}")
            raise NotFound("User not found")

        transfer_ownership(
            organization=org,
            new_owner=new_owner,
            performed_by=request.user,
        )
        logger.info(f"Ownership transferred to {email} for organization: {org.name}")

        return Response(
            {"message": "Ownership transferred successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"])
    def remove_member(self, request):
        org_id = request.query_params.get("org_id")
        email = request.data.get("email")
        logger.info(f"Removing member {email} from organization: {org_id} by user: {request.user.email}")
        org = self.permission_object
        self.check_role_permissions(request, org)
        
        user = get_user(email, kind="email")
        if not user:
            logger.warning(f"User not found for removal: {email}")
            raise NotFound("User not found")

        remove_member(
            organization=org,
            user=user,
            performed_by=request.user,
        )
        logger.info(f"Member {email} removed from organization: {org.name}")

        return Response(
            {"message": "Member removed successfully"},
            status=status.HTTP_200_OK,
        )
