"""Connector definitions and construction factory for Synapse."""

from synapse.connectors.base import BaseConnector
from synapse.connectors.factory import make_connector, makeconnectors
from synapse.connectors.gmail import GmailConnector, GmailConnectors
from synapse.connectors.mcp_wrapper import MCPConnector
from synapse.connectors.notion import (
    NotionConnector,
    NotionConnectors,
    NotionsConnector,
)
from synapse.connectors.photos import (
    GooglePhotosConnector,
    GooglePhotosConnectors,
)

__all__ = [
    "BaseConnector",
    "GmailConnector",
    "GmailConnectors",
    "GooglePhotosConnector",
    "GooglePhotosConnectors",
    "MCPConnector",
    "NotionConnector",
    "NotionConnectors",
    "NotionsConnector",
    "make_connector",
    "makeconnectors",
]
