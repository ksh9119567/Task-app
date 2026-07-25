import logging

from rest_framework.exceptions import PermissionDenied

from core.permissions.resolver import effective_role
from core.constants.project_constant import PROJECT_ROLE_HIERARCHY

logger = logging.getLogger(__name__)

def delete_task(*, task, performed_by):
    logger.info(f"Deleting task: {task.title} by user: {performed_by.email}")
    
    if task.parent:
        if task.created_by != performed_by:
            logger.warning(f"Non-creator {performed_by.email} attempted to delete subtask: {task.title}")
            raise PermissionDenied("Only subtask creator can delete subtask")
    
    role = effective_role(performed_by, task.project)
    min_role = task.project.settings.delete_task_min_role

    if task.created_by != performed_by and PROJECT_ROLE_HIERARCHY.get(role, -1) < PROJECT_ROLE_HIERARCHY[min_role]:
        logger.warning(f"User {performed_by.email} with role {role} attempted to delete task: {task.title}")
        raise PermissionDenied("You do not have permission to delete this task.")
    
    task.is_deleted = True
    task.save()
    logger.info(f"Task deleted successfully: {task.title}")