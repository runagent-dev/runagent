"""
Local account storage helpers.
"""

import typing as t
from runagent.storage.base import LocalStorage


class ProjectData(LocalStorage):
    """
    Local user data storage.
    """
    name: t.Optional[str] = None
    api_key: t.Optional[str] = None
    username: t.Optional[str] = None

    """
    API key for RunAgent API server
    """
