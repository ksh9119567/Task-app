import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from app.governance.api.v1.serializers import (
    OrgSettingsSerializer, TeamSettingsSerializer, ProjectSettingsSerializer,
    OrgSettingsUpdateSerializer, TeamSettingsUpdateSerializer, ProjectSettingsUpdateSerializer
)

from core.utils.org_utils import get_org
from core.utils.team_utils import get_team
from core.utils.project_utils import get_project
from core.permissions import organization, team, project

logger = logging.getLogger(__name__)


class GovernanceAPI(viewsets.ModelViewSet):
    """
    Governance API (v1)
    """
    def get_permissions(self):
        if self.action in ["get_org_settings", "update_org_settings"]:
            permissions = [IsAuthenticated, organization.IsOrganizationOwner]
        elif self.action in ["get_team_settings", "update_team_settings"]:
            permissions = [IsAuthenticated, team.IsTeamOwner]
        elif self.action in ["get_project_settings", "update_project_settings"]:
            permissions = [IsAuthenticated, project.IsProjectOwner]
        else:
            permissions = [IsAuthenticated]
        
        return [permission() for permission in permissions]
    
    def get_serializer_class(self):
        if self.action == "update_org_settings":
            return OrgSettingsUpdateSerializer
        if self.action == "update_team_settings":
            return TeamSettingsUpdateSerializer
        if self.action == "update_project_settings":
            return ProjectSettingsUpdateSerializer
    
    @action(detail=True, methods=["get"])
    def get_org_settings(self, request):
        org_id = request.query_params.get("org_id")
        logger.info(f"Retrieving organization settings for user: {request.user.email}")
        org = get_org(org_id)
        self.check_object_permissions(request, org)
        
        org_settings = org.settings
        logger.debug(f"Organization settings retrieved for organization: {org.name}")
        
        return Response({
            "message": "Success",
            "data": OrgSettingsSerializer(org_settings).data},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["get"])
    def get_team_settings(self, request):
        team_id = request.query_params.get("team_id")
        logger.info(f"Retrieving team settings for user: {request.user.email}")
        team = get_team(team_id)
        self.check_object_permissions(request, team)
        
        team_settings = team.settings
        logger.debug(f"Team settings retrieved for team: {team.name}")
        
        return Response({
            "message": "Success",
            "data": TeamSettingsSerializer(team_settings).data},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["get"])
    def get_project_settings(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Retrieving project settings for user: {request.user.email}")
        project = get_project(project_id)
        self.check_object_permissions(request, project)
        
        project_settings = project.settings
        logger.debug(f"Project settings retrieved for project: {project.name}")
        
        return Response({
            "message": "Success",
            "data": ProjectSettingsSerializer(project_settings).data},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["put"])
    def update_org_settings(self, request):
        org_id = request.query_params.get("org_id")
        logger.info(f"Updating organization settings for user: {request.user.email}")
        org = get_org(org_id)
        self.check_object_permissions(request, org)
        org_settings = org.settings
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            org_settings,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        
        org_settings = serializer.save()
        logger.debug(f"Organization settings updated for organization: {org.name}")
        
        return Response({
            "message": "Success",
            "data": OrgSettingsSerializer(org_settings).data},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["put"])
    def update_team_settings(self, request):
        team_id = request.query_params.get("team_id")
        logger.info(f"Updating team settings for user: {request.user.email}")
        team = get_team(team_id)
        self.check_object_permissions(request, team)
        team_settings = team.settings
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            team_settings,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        
        team_settings = serializer.save()
        logger.debug(f"Team settings updated for team: {team.name}")
        
        return Response({
            "message": "Success",
            "data": TeamSettingsSerializer(team_settings).data},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["put"])
    def update_project_settings(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Updating project settings for user: {request.user.email}")
        project = get_project(project_id)
        self.check_object_permissions(request, project)
        project_settings = project.settings
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            project_settings,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        
        project_settings = serializer.save()
        logger.debug(f"Project settings updated for project: {project.name}")
        
        return Response({
            "message": "Success",
            "data": ProjectSettingsSerializer(project_settings).data},
            status=status.HTTP_200_OK
        )