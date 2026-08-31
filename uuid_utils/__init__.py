"""
Stand-in for the real `uuid_utils` package.

Why this exists: `langsmith` (pulled in as a side-dependency of
langgraph/langchain_core -- NOMAD doesn't use langsmith directly) tries to
import the real `uuid_utils` package's compiled extension
(`_uuid_utils.cp313-win_amd64.pyd`) for a fast UUIDv7 implementation. On
this machine, a Windows Application Control policy blocks that specific
file from both running AND being deleted/uninstalled -- the same class of
issue that hit npm/rollup earlier in this project.

Because this repo's root is inserted at the front of `sys.path` (see
backend/app/main.py), Python finds THIS package before it ever reaches the
real, blocked one in site-packages -- so the blocked file is simply never
touched. This shim only implements the one thing langsmith actually calls
(`uuid_utils.compat.uuid7`), using pure Python -- no compiled extension,
nothing for the Application Control policy to block.

Safe to remove once/if `uuid-utils` installs and imports cleanly again on
this machine (e.g. after an IT policy change) -- nothing else in this repo
imports `uuid_utils` directly.
"""

from .compat import uuid7

__all__ = ["uuid7"]
