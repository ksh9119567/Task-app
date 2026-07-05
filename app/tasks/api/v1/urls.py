from django.urls import path

from .api import TaskAPI

urlpatterns = [
    path("get-project-tasks/", TaskAPI.as_view({"get": "list"}), name="get_project_tasks"),
    path("get-my-tasks/", TaskAPI.as_view({"get": "my_tasks"}), name="get_my_tasks"),
    path("create-task/", TaskAPI.as_view({"post": "create"}), name= "create_task"),
    path("get_task_details/", TaskAPI.as_view({"get": "retrieve"}), name="get_task_details"),
    path("update-task/", TaskAPI.as_view({"put": "update"}), name="update_task"),
    path("delete-task/", TaskAPI.as_view({"delete": "destroy"}), name="delete_task")
]
