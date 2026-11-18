# simple_path_component

Validates each segment of a path against OS-specific rules before you hand it to the filesystem.

```python
from simple_path_component import WINDOWS_RULES, validate_component, validate_path

result = validate_component("CON.txt", WINDOWS_RULES)
assert not result.valid
assert result.reason == "reserved device name"

for part in validate_path("docs/report.txt", WINDOWS_RULES, separator="/"):
    part.raise_for_error()
```

The exported names are `ComponentError`, `ComponentResult`, `PathRules`, `POSIX_RULES`, `WINDOWS_RULES`, `validate_component`, and `validate_path`.

## Why this exists

A path that looks fine on Linux can be rejected by Windows or silently collided with on macOS. The rules differ per platform and are easy to get wrong: Windows reserves device names such as `CON` and `NUL` even when an extension is attached, forbids a set of characters including `<>:"/\|?*`, and strips trailing spaces and dots; POSIX forbids only NUL and `/` but limits a component to 255 bytes; macOS folds case by default, so `ReadMe` and `readme` name the same file. Checking these before a filesystem call turns a confusing `OSError` or an overwritten file into a clear message.

The trade-off is that the rules are conservative. Windows also allows some names that Win32 cannot open, so we reject trailing spaces and dots even though NTFS can store them. A caller who needs those names can construct a custom `PathRules` and pass it in; the default `WINDOWS_RULES` is what a normal Win32 program should use.

## The awkward edge

`validate_path` splits on a single separator and returns one result per segment, including an empty final segment when the path ends with the separator. That empty segment is reported as invalid, which is usually what you want: a path that ends in `/` does not name a file. If you are validating a directory prefix, strip the trailing separator first.
