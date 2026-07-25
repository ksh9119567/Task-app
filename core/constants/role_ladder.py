"""
Single shared ordering for every role name used across Org/Team/Project scopes.
Each scope keeps its own ROLES choices list (which roles exist at that scope) but
rank comes from here, so precedence comparisons stay consistent everywhere and every
scope's hierarchy dict is guaranteed to have an entry for each of its own roles.
"""

ROLE_LADDER = {
    "GUEST": 0,
    "VIEWER": 10,
    "CONTRIBUTOR": 20,
    "MEMBER": 20,       # same tier as CONTRIBUTOR - scope-specific synonyms
    "LEAD": 30,
    "MANAGER": 40,
    "ADMIN": 50,
    "OWNER": 100,
}


def build_hierarchy(roles_choices):
    """
    roles_choices: a scope's ROLES list, e.g. [("OWNER", "Owner"), ...].
    Returns {role: rank} for that scope's own roles, ranked from ROLE_LADDER.
    Raises at import time if a role has no ladder entry, instead of KeyError-ing
    at request time later.
    """
    hierarchy = {}
    for role, _ in roles_choices:
        if role not in ROLE_LADDER:
            raise ValueError(f"Role '{role}' has no entry in ROLE_LADDER")
        hierarchy[role] = ROLE_LADDER[role]
    return hierarchy
