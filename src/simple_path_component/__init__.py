"""Public exports for simple_path_component.

Only the names re-exported here are considered part of the stable API.
"""

from .core import (
    ComponentError,
    ComponentResult,
    PathRules,
    POSIX_RULES,
    WINDOWS_RULES,
    validate_component,
    validate_path,
)

__all__ = [
    "ComponentError",
    "ComponentResult",
    "PathRules",
    "POSIX_RULES",
    "WINDOWS_RULES",
    "validate_component",
    "validate_path",
]
