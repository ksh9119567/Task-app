from django.urls import path

from app.governance.api.v1.api import GovernanceAPI

urlpatterns = [
    path('get-org-settings/', GovernanceAPI.as_view({'get': 'get_org_settings'}), name='get_org_settings'),
    path('get-team-settings/', GovernanceAPI.as_view({'get': 'get_team_settings'}), name='get_org_settings'),
    path('get-project-settings/', GovernanceAPI.as_view({'get': 'get_project_settings'}), name='get_org_settings'),
    path('update-org-settings/', GovernanceAPI.as_view({'put': 'update_org_settings'}), name='update_org_settings'),
    path('update-team-settings/', GovernanceAPI.as_view({'put': 'update_team_settings'}), name='update_team_settings'),
    path('update-project-settings/', GovernanceAPI.as_view({'put': 'update_project_settings'}), name='update_project_settings'),
]