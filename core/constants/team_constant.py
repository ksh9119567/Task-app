from core.constants.role_ladder import build_hierarchy

TEAM_ROLES = [
    ("OWNER", "Owner"),             # Root-level access
    ("MANAGER", "Manager"),        # Manages team, invites members
    ("LEAD", "Lead"),              # Can assign tasks, manage team workflows
    ("MEMBER", "Member"),          # Normal team member
    ("VIEWER", "Viewer"),          # Read-only
]

TEAM_ROLE_HIERARCHY = build_hierarchy(TEAM_ROLES)

TEAM_ACTION_POLICIES = {
    "invite_member": {
        "system_min_role": "MANAGER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
    "remove_member": {
        "system_min_role": "MANAGER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
    "update_member": {
        "system_min_role": "MANAGER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
}
