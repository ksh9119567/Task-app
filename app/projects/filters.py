import django_filters

from app.projects.models import Project, ProjectMembership

class ProjectFilter(django_filters.FilterSet):
    status = django_filters.CharFilter()
    team = django_filters.CharFilter(field_name="team_links__team_id")
    
    class Meta:
        model = Project
        fields = ["status", "team"]
        
        
class ProjectMembershipFilter(django_filters.FilterSet):
    role = django_filters.CharFilter()
    
    class Meta:
        model = ProjectMembership
        fields = ["role"]