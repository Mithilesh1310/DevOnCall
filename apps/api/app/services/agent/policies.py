from enum import Enum
from typing import List, Set

class ToolPermission(str, Enum):
    READ_ONLY = "READ_ONLY"
    WRITE_WORKSPACE = "WRITE_WORKSPACE"
    EXECUTE_SANDBOX = "EXECUTE_SANDBOX"
    BROWSER_SANDBOX = "BROWSER_SANDBOX"
    PRODUCTION = "PRODUCTION"

class AgentPolicy:
    """
    Enforces tool execution permissions for DevOnCall agent runtime.
    Phase 3 enables READ_ONLY and WRITE_WORKSPACE permissions.
    Phase 5 enables EXECUTE_SANDBOX.
    Phase 7 enables BROWSER_SANDBOX.
    PRODUCTION remains strictly DENIED.
    """

    def __init__(self, allowed_permissions: List[ToolPermission] | Set[ToolPermission] | None = None):
        if allowed_permissions is None:
            # Default: READ_ONLY and WRITE_WORKSPACE allowed
            self.allowed_permissions = {ToolPermission.READ_ONLY, ToolPermission.WRITE_WORKSPACE}
        else:
            self.allowed_permissions = set(allowed_permissions)

    def is_permission_allowed(self, required_permission: ToolPermission) -> bool:
        return required_permission in self.allowed_permissions

default_phase2_policy = AgentPolicy({ToolPermission.READ_ONLY})
default_phase3_policy = AgentPolicy({ToolPermission.READ_ONLY, ToolPermission.WRITE_WORKSPACE})
default_phase5_policy = AgentPolicy({ToolPermission.READ_ONLY, ToolPermission.WRITE_WORKSPACE, ToolPermission.EXECUTE_SANDBOX})
default_phase7_policy = AgentPolicy({ToolPermission.READ_ONLY, ToolPermission.WRITE_WORKSPACE, ToolPermission.EXECUTE_SANDBOX, ToolPermission.BROWSER_SANDBOX})


