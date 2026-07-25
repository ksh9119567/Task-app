from django.urls import path

from .api import ProjectAPI

urlpatterns = [
    path('get-user-projects/', ProjectAPI.as_view({'get': 'list'}), name='project_list'),
    path('create-project/', ProjectAPI.as_view({'post': 'create'}), name='project_create'),
    path('get_org-projects/', ProjectAPI.as_view({'get': 'org_projects'}), name='org_projects'),
    path('get-team-projects/', ProjectAPI.as_view({'get': 'team_projects'}), name='team_projects'),
    path('get-project-details/', ProjectAPI.as_view({'get': 'retrieve'}), name='project_details'),
    path('get-project-members/', ProjectAPI.as_view({'get': 'members'}), name='project_members'),
    path('self-remove-member/', ProjectAPI.as_view({'delete': 'self_remove_member'}), name='self_remove'),
    path('update-project/', ProjectAPI.as_view({'put': 'update'}), name='project_update'),
    path('send-invite/', ProjectAPI.as_view({'post': 'send_invite'}), name='project_send_invite'),
    path('accept-project-invite/', ProjectAPI.as_view({'post': 'accept_invite'}), name='project_accept_invite'),
    path('update-member/', ProjectAPI.as_view({'put': 'update_member'}), name='project_update_member'),
    path('remove-member/', ProjectAPI.as_view({'delete': 'remove_member'}), name='project_remove_member'),
    path('transfer-owner/', ProjectAPI.as_view({'put': 'transfer_owner'}), name='project_transfer_owner'),
    path('delete-project/', ProjectAPI.as_view({'delete': 'destroy'}), name='project_delete'),
    path('get-project-teams/', ProjectAPI.as_view({'get': 'teams'}), name='project_teams'),
    path('get-stale-members/', ProjectAPI.as_view({'get': 'stale_members'}), name='project_stale_members'),
    path('assign-team/', ProjectAPI.as_view({'post': 'assign_team'}), name='project_assign_team'),
    path('update-team-role/', ProjectAPI.as_view({'put': 'update_team_role'}), name='project_update_team_role'),
    path('unassign-team/', ProjectAPI.as_view({'delete': 'unassign_team'}), name='project_unassign_team'),
]
