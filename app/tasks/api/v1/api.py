import logging

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter

from app.tasks.models import Task
from app.tasks.api.v1.serializers import (
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer
)
from app.tasks.services.task_service import delete_task
from app.tasks.filters import TaskFilter

from core.constants.project_constant import PROJECT_ROLE_HIERARCHY, PROJECT_ACTION_POLICIES
from core.pagination import StandardPagination
from core.permissions.resolver import effective_role

from app.governance.services.rules_engine import GovernanceResolver
from core.permissions.mixins import RoleCheckerMixin
from core.permissions.project import IsProjectMember, IsProjectManager, IsProjectOwner
from core.utils.task_utils import get_task, get_all_task
from core.utils.project_utils import get_project

logger = logging.getLogger(__name__)


class TaskAPI(viewsets.ViewSet, RoleCheckerMixin):
    """
    Task API (v1)
    """
    queryset = Task.objects.all()
    pagination_class = StandardPagination()
    filterset_class = TaskFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "due_date", "priority"]
    
    def get_permissions(self):
        if self.action in ["list", "retrieve", "create", "update"]:
            permissions = [IsAuthenticated, IsProjectMember]
        elif self.action == "destroy":
            permissions = [IsAuthenticated, IsProjectManager]
        else:
            permissions = [IsAuthenticated]
            
        return [permission() for permission in permissions]
    
    def check_role_permissions(self, request, project, task=None):
        if self.action in ["create", "update", "destroy"] and task is not None:
            if request.user == task.created_by or request.user == task.assigned_to:
                return True
            
        role = effective_role(request.user, project)

        if role == "OWNER":
            return True
        elif self.action == "create":
            if project.settings.allow_task_creation == False:
                raise PermissionDenied("You are not allowed to create tasks.")

            policy_action = "create_task"
        elif self.action == "update":
            if project.settings.allow_task_updates == False:
                raise PermissionDenied("You are not allowed to update tasks.")

            policy_action = "update_task"
        elif self.action == "destroy":
            if project.settings.allow_task_deletions == False:
                raise PermissionDenied("You are not allowed to delete tasks.")

            policy_action = "delete_task"
        else:
            return

        # Clamp the configured minimum role to the action's system min/max bounds.
        minimum_role = GovernanceResolver.resolve_action_min_role(
            project.settings, policy_action, PROJECT_ACTION_POLICIES, PROJECT_ROLE_HIERARCHY
        )
        if not self.has_minimum_role(role, minimum_role, PROJECT_ROLE_HIERARCHY):
            raise PermissionDenied(f"You must have at least {minimum_role} role to perform this action.")
        else:
            return True
    
    def get_serializer_class(self):
        if self.action == "create":
            return TaskCreateSerializer
        if self.action == "update":
            return TaskUpdateSerializer
        else:
            return TaskSerializer
    
    def apply_filters(self, request, queryset):
        django_filter = DjangoFilterBackend()
        queryset = django_filter.filter_queryset(request, queryset, self)
        
        search_filter = SearchFilter()
        queryset = search_filter.filter_queryset(request, queryset, self)
        
        ordering_filter = OrderingFilter()
        queryset = ordering_filter.filter_queryset(request, queryset, self)
        
        return queryset
        
    def list(self, request):
        project_id = request.query_params.get("project_id")
        logger.info(f"Listing tasks for project: {project_id} by user: {request.user.email}")
        project = get_project(project_id)
        self.check_object_permissions(request, project)

        tasks = self.apply_filters(request, get_all_task(project))

        page = self.pagination_class.paginate_queryset(tasks, request)
        logger.debug(f"Found {len(page)} tasks for project: {project.name}")

        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": TaskSerializer(page, many=True).data}
        )

    def my_tasks(self, request):
        logger.info(f"Listing my tasks for user: {request.user.email}")

        tasks = self.apply_filters(
            request,
            Task.objects.filter(
                assigned_to=request.user,
                is_deleted=False,
                project__is_deleted=False,
            ).select_related("project", "parent", "assigned_to", "created_by").order_by("-created_at")
        )

        page = self.pagination_class.paginate_queryset(tasks, request)
        logger.debug(f"Found {len(page)} tasks assigned to user: {request.user.email}")

        return self.pagination_class.get_paginated_response({
            "message": "Success",
            "data": TaskSerializer(page, many=True).data}
        )
    
    def create(self, request):
        logger.info(f"Creating task by user: {request.user.email}, title: {request.data.get('title')}")
        project = get_project(request.data.get("project_id"))
        
        task = None
        if request.data.get("parent_id"):
            task = get_task(request.data.get("parent_id"))
        
        self.check_object_permissions(request, project)
        self.check_role_permissions(request, project, task)
        
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            data=request.data, 
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        
        task = serializer.save()
        logger.info(f"Task created successfully: {task.title} by {request.user.email}")
        
        return Response({
            "message": "Task created successfully",
            "data": TaskSerializer(task).data}, 
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request):
        task_id = request.query_params.get("task_id")
        logger.info(f"Retrieving task: {task_id} by user: {request.user.email}")
        task = get_task(task_id)
        self.check_object_permissions(request, task.project)
        logger.debug(f"Task retrieved: {task.title}")
        
        return Response({
            "message": "Success",
            "data": TaskSerializer(task).data}, 
            status=status.HTTP_200_OK
        )
    
    def update(self, request):
        task_id = request.query_params.get("task_id")
        logger.info(f"Updating task: {task_id} by user: {request.user.email}")
        task = get_task(task_id)
        self.check_object_permissions(request, task.project)
        self.check_role_permissions(request, task.project, task)
        
        serializer_class = TaskUpdateSerializer
        serializer = serializer_class(
            task,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Task updated successfully: {task.title}")
        
        return Response({
            "message": "Task updated successfully",
            "data": TaskSerializer(task).data},
            status=status.HTTP_200_OK
        )
        
    def destroy(self, request):
        task_id = request.query_params.get("task_id")
        logger.info(f"Deleting task: {task_id} by user: {request.user.email}")
        task = get_task(task_id)
        self.check_object_permissions(request, task.project)
        self.check_role_permissions(request, task.project, task)
        
        delete_task(
            task=task, 
            performed_by=request.user
        )
        logger.info(f"Task deleted successfully: {task.title}")
        
        return Response(
            {"message": "Task deleted successfully"},
            status=status.HTTP_200_OK
        )
        
    
    
        
    

