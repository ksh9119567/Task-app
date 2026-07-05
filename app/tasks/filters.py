import django_filters
from app.tasks.models import Task

class TaskFilter(django_filters.FilterSet):
    status = django_filters.CharFilter()
    priority = django_filters.CharFilter()
    assigned_to = django_filters.UUIDFilter(field_name="assigned_to_id")
    parent = django_filters.UUIDFilter(field_name="parent_id")
    project = django_filters.UUIDFilter(field_name="project_id")

    class Meta:
        model = Task
        fields = ["status", "priority", "assigned_to", "parent", "project"]