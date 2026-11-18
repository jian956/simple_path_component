"""OS-aware validation for individual path components.

A *path component* is a single segment of a path, e.g. the ``foo`` in
``a/foo/b``.  Filesystem calls reject some components on some platforms for
reasons that are not obvious from the bytes alone: Windows reserves device
names, macOS folds case by default, POSIX forbids ``/`` and NUL, and every
platform imposes a length limit.  This module keeps those rules in one place so
callers can check a component *before* touching the disk.

The rules are intentionally conservative.  For example, Windows also forbids
trailing spaces and dots in the *Win32* API, so we reject them even though NTFS
itself can store them.  Rejecting is cheaper than debugging a file that cannot
be opened later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


class ComponentError(ValueError):
    """Raised by :func:`validate_component` when a component is invalid.

    Subclassing ``ValueError`` means callers that already catch ``ValueError``
    for bad arguments keep working.
    """

    def __init__(self, component: str, reason: str) -> None:
        self.component = component
        self.reason = reason
        super().__init__(f"invalid path component {component!r}: {reason}")


@dataclass(frozen=True)
class PathRules:
    """Immutable description of the rules for one operating system family.

    ``max_length`` is the maximum number of characters allowed in a single
    component.  ``reserved_names`` are compared case-insensitively when
    ``case_insensitive`` is true, which matches how Windows and default macOS
    filesystems behave.  ``illegal_chars`` is a string of characters that may
    not appear anywhere in the component; NUL is always illegal and is added
    by the validator rather than listed here.
    """

    name: str
    max_length: int
    reserved_names: Tuple[str, ...]
    illegal_chars: str
    case_insensitive: bool


# Windows: 255 UTF-16 code units per component, reserved device names, and the
# set of characters Win32 forbids in a filename.  We include both slash
# variants because a component is sometimes handed to us with a separator
# still attached by a caller who split on the wrong character.
WINDOWS_RULES = PathRules(
    name="windows",
    max_length=255,
    reserved_names=(
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ),
    illegal_chars='<>:"/\\|?*',
    case_insensitive=True,
)

# POSIX (Linux, BSD, and the bytes-level view of macOS): only NUL and slash are
# illegal, and the limit is 255 bytes.  We count characters here because the
# public API takes ``str``; callers with byte strings should encode first.
POSIX_RULES = PathRules(
    name="posix",
    max_length=255,
    reserved_names=(),
    illegal_chars="/",
    case_insensitive=False,
)


@dataclass(frozen=True)
class ComponentResult:
    """Outcome of validating one component.

    ``valid`` is true when the component may be used as-is.  When false,
    ``reason`` explains why and ``folded`` holds the case-folded form that
    would collide with the component on a case-insensitive filesystem (or
    ``None`` when case folding is not applicable).
    """

    valid: bool
    component: str
    reason: Optional[str]
    folded: Optional[str]


_ALWAYS_ILLEGAL = "\x00"


def _is_reserved(component: str, rules: PathRules) -> bool:
    """Return True when ``component`` is a reserved device name.

    Windows reserves the name with or without an extension, so ``CON.txt`` is
    just as reserved as ``CON``.  We therefore compare the part before the
    first dot.
    """
    if not rules.reserved_names:
        return False
    stem = component.split(".", 1)[0]
    if rules.case_insensitive:
        stem = stem.upper()
    return stem in rules.reserved_names


def validate_component(component: str, rules: PathRules = POSIX_RULES) -> ComponentResult:
    """Validate a single path component against ``rules``.

    Returns a :class:`ComponentResult` rather than raising so callers can
    collect every problem in a path.  Use :func:`validate_path` for that, or
    call :meth:`ComponentResult.raise_for_error` if you prefer exceptions.

    The empty string is rejected: a path component must name something.
    """
    if not isinstance(component, str):
        raise TypeError("component must be a str")

    folded: Optional[str] = None
    if rules.case_insensitive:
        folded = component.casefold()

    if component == "":
        return ComponentResult(False, component, "empty component", folded)

    if len(component) > rules.max_length:
        return ComponentResult(
            False,
            component,
            f"length {len(component)} exceeds {rules.max_length}",
            folded,
        )

    for ch in component:
        if ch in _ALWAYS_ILLEGAL or ch in rules.illegal_chars:
            return ComponentResult(
                False,
                component,
                f"illegal character {ch!r}",
                folded,
            )

    if _is_reserved(component, rules):
        return ComponentResult(False, component, "reserved device name", folded)

    # Win32 strips trailing spaces and dots before resolving a name, so two
    # different-looking components can refer to the same file.  Rejecting them
    # keeps the mapping from component to file one-to-one.
    if rules.name == "windows" and component[-1] in ". ":
        return ComponentResult(
            False,
            component,
            "trailing space or dot is not allowed on Windows",
            folded,
        )

    return ComponentResult(True, component, None, folded)


def validate_path(
    path: str,
    rules: PathRules = POSIX_RULES,
    *,
    separator: str = "/",
) -> List[ComponentResult]:
    """Validate every component of ``path`` and return one result per segment.

    ``separator`` defaults to ``/``; pass ``"\\"`` for Windows-style input.
    The result list is in path order and has the same length as ``path`` split
    on ``separator``.  An empty path yields an empty list; a path with a
    trailing separator yields a final empty component, which will be reported
    as invalid.
    """
    if not isinstance(path, str):
        raise TypeError("path must be a str")
    if not isinstance(separator, str) or len(separator) != 1:
        raise ValueError("separator must be a single character")
    if path == "":
        return []
    return [validate_component(part, rules) for part in path.split(separator)]


def _raise_for_error(self: ComponentResult) -> None:
    """Raise :class:`ComponentError` when ``self.valid`` is false."""
    if not self.valid:
        raise ComponentError(self.component, self.reason or "invalid")


# Attach as a method without importing functools; keeps the dataclass frozen.
ComponentResult.raise_for_error = _raise_for_error  # type: ignore[attr-defined]
