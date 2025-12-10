class NeewerError(Exception):
    """Base exception for NeewerLite."""

class ConnectionError(NeewerError):
    """Raised when connection fails."""

class ProtocolError(NeewerError):
    """Raised when protocol handshake fails."""
