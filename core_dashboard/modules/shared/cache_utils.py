import hashlib
import os
from typing import Iterable, List


def compute_files_hash(paths: Iterable[str]) -> str:
    """Compute a SHA256 hex digest for the concatenated contents of the given files.

    Returns a short 12-character hex string. Missing files are ignored.
    """
    h = hashlib.sha256()
    any_read = False
    for p in paths:
        try:
            if not os.path.exists(p):
                continue
            with open(p, 'rb') as fh:
                while True:
                    chunk = fh.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
            any_read = True
        except Exception:
            # ignore unreadable files
            continue
    if not any_read:
        return ''
    return h.hexdigest()[:12]


def gather_module_files(module_dir: str) -> List[str]:
    """Return a list of python source files under module_dir to include in hash.

    Only includes .py files at top-level of the module directory (no deep recursion)
    to keep the hash cheap and deterministic.
    """
    files = []
    try:
        for name in os.listdir(module_dir):
            if name.endswith('.py'):
                files.append(os.path.join(module_dir, name))
    except Exception:
        pass
    return files
