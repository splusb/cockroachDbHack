"""
Self-healing module - applies code patches automatically when confidence is high.

The agent reads the buggy code, diagnoses the issue, and if confident,
applies the fix directly to the source file.

Usage:
    from agent.heal import apply_patch, read_app_file
    code = read_app_file("app.py")
    # ... agent reasons and returns code_patch ...
    success = apply_patch(code_patch)
"""

import os
from typing import Dict, Optional

from agent.config import BUGGY_APP_PATH


def read_app_file(filename: str) -> Optional[str]:
    """
    Read a source file from the demo app directory.

    Args:
        filename: Name of the file to read (e.g., "app.py", "auth.py")

    Returns:
        File contents as string, or None if file doesn't exist.
    """
    filepath = os.path.join(BUGGY_APP_PATH, filename)
    if not os.path.exists(filepath):
        print(f"[heal] File not found: {filepath}")
        return None

    with open(filepath, "r") as f:
        return f.read()


def list_app_files() -> list:
    """List all files in the demo app directory."""
    if not os.path.exists(BUGGY_APP_PATH):
        return []
    files = []
    for root, dirs, filenames in os.walk(BUGGY_APP_PATH):
        for fname in filenames:
            if fname.endswith(('.py', '.js', '.html', '.css')):
                rel_path = os.path.relpath(os.path.join(root, fname), BUGGY_APP_PATH)
                files.append(rel_path)
    return files


def apply_patch(code_patch: Dict[str, str]) -> bool:
    """
    Apply a code patch to the demo app.

    Args:
        code_patch: Dict with keys:
            - file: filename to modify
            - find: exact string to find in the file
            - replace: string to replace it with

    Returns:
        True if patch was applied successfully, False otherwise.
    """
    if not code_patch:
        print("[heal] No patch to apply")
        return False

    filename = code_patch.get("file")
    find_str = code_patch.get("find")
    replace_str = code_patch.get("replace")

    if not all([filename, find_str, replace_str]):
        print("[heal] Invalid patch: missing file, find, or replace")
        return False

    filepath = os.path.join(BUGGY_APP_PATH, filename)

    if not os.path.exists(filepath):
        print(f"[heal] Target file not found: {filepath}")
        return False

    # Read the file
    with open(filepath, "r") as f:
        content = f.read()

    # Check if the target string exists
    if find_str not in content:
        print(f"[heal] Could not find target string in {filename}")
        print(f"[heal] Looking for: {find_str[:100]}...")
        return False

    # Apply the patch
    new_content = content.replace(find_str, replace_str, 1)

    # Write back
    with open(filepath, "w") as f:
        f.write(new_content)

    print(f"[heal] ✓ Patch applied to {filename}")
    print(f"[heal]   Replaced: {find_str[:60]}...")
    print(f"[heal]   With:     {replace_str[:60]}...")
    return True


def revert_patch(code_patch: Dict[str, str]) -> bool:
    """
    Revert a previously applied patch (swap find and replace).

    Useful for re-injecting bugs for demo purposes.
    """
    if not code_patch:
        return False

    reverted = {
        "file": code_patch["file"],
        "find": code_patch["replace"],
        "replace": code_patch["find"],
    }
    return apply_patch(reverted)
