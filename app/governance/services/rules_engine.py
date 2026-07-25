from core.constants.org_constant import ORG_ACTION_POLICIES, ORG_ROLE_HIERARCHY
from core.constants.team_constant import TEAM_ACTION_POLICIES, TEAM_ROLE_HIERARCHY
from core.constants.project_constant import PROJECT_ACTION_POLICIES, PROJECT_ROLE_HIERARCHY


class GovernanceResolver:

    BASE_FIELDS = [
        "allow_member_invites",
        "allow_member_updates",
        "allow_member_removal",
        "allow_self_removal",
        "require_approval_for_invites",
        "require_approval_for_updates",
        "require_approval_for_removal",
    ]

    @staticmethod
    def get_effective_project_base_rules(project):
        project_settings = project.settings

        effective = {}

        # 1️⃣ Start with project local rules
        for field in GovernanceResolver.BASE_FIELDS:
            effective[field] = getattr(project_settings, field)

        # 2️⃣ Override from team (if enabled)
        if project.team and project_settings.inherit_base_rules_from_team:
            team_settings = project.team.settings
            for field in GovernanceResolver.BASE_FIELDS:
                effective[field] = getattr(team_settings, field)

        # 3️⃣ Override from org (highest priority)
        if project.organization and project_settings.inherit_base_rules_from_org:
            org_settings = project.organization.settings
            for field in GovernanceResolver.BASE_FIELDS:
                effective[field] = getattr(org_settings, field)

        return effective


    # -----------------------------------------------------
    # TEAM RULE RESOLUTION
    # -----------------------------------------------------

    @staticmethod
    def get_effective_team_base_rules(team):
        """
        Team → Org
        """
        team_settings = team.settings
        effective_rules = {}

        base_fields = [
            "allow_member_invites",
            "allow_self_removal",
            "require_approval_for_invites",
        ]

        for field in base_fields:
            effective_rules[field] = getattr(team_settings, field)

        if team.organization and team_settings.inherit_base_rules_from_org:
            org_settings = team.organization.settings
            for field in base_fields:
                effective_rules[field] = getattr(org_settings, field)

        return effective_rules
    
    
    # -----------------------------------------------------
    # GENERIC ACTION POLICY RESOLUTION
    # -----------------------------------------------------

    @staticmethod
    def resolve_action_min_role(entity_settings, action_name, policy_dict, hierarchy):
        """
        Returns the effective minimum role required to perform an action.
        Enforces system bounds and configurable settings.
        """

        if action_name not in policy_dict:
            raise ValueError(f"Unknown action policy: {action_name}")

        policy = policy_dict[action_name]

        system_min = policy["system_min_role"]
        system_max = policy["system_max_role"]
        configurable = policy["configurable"]
        default = policy["default"]

        # If not configurable → always use default
        if not configurable:
            return default

        # Get configured min role from settings
        configured_value = getattr(entity_settings, f"{action_name}_min_role", default)

        # Enforce lower bound
        if hierarchy[configured_value] < hierarchy[system_min]:
            configured_value = system_min

        # Enforce upper bound
        if hierarchy[configured_value] > hierarchy[system_max]:
            configured_value = system_max

        return configured_value
