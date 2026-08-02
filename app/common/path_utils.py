"""Path containment and normalization helpers."""

import os
from pathlib import Path


def normalized_path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
