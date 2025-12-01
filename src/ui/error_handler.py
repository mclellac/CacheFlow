"""
This module provides a centralized way to map exceptions to user-friendly
error messages for the UI.
"""

from typing import Tuple


def get_user_friendly_error(exception: Exception) -> Tuple[str, str]:
    """
    Maps an exception to a user-friendly (title, message) tuple.

    Args:
        exception: The exception that occurred.

    Returns:
        A tuple of (title, message).
    """
    msg = str(exception)
    exc_type = str(type(exception))

    # Check for common connection errors
    if "Connection refused" in msg or "ConnectionError" in exc_type:
        return (
            "Connection Failed",
            f"Could not connect to the server. Please check if the server is running and reachable.\n\nDetails: {msg}",
        )

    if (
        "Name or service not known" in msg
        or "DNS" in msg
        or "gaierror" in exc_type
        or "dns.resolver" in exc_type
    ):
        return (
            "DNS Error",
            f"Could not resolve the hostname. Please check the domain name and your internet connection.\n\nDetails: {msg}",
        )

    if "timed out" in msg or "Timeout" in exc_type:
        return (
            "Connection Timed Out",
            f"The request timed out. The server might be slow or unreachable.\n\nDetails: {msg}",
        )

    if "SSL" in msg or "SSLError" in exc_type:
        return (
            "SSL/TLS Error",
            f"A security error occurred during the connection. The certificate may be invalid or untrusted.\n\nDetails: {msg}",
        )

    if "No layers configured" in msg:
        return (
            "Configuration Error",
            "No layers are configured for this domain. Please add layers in the Preferences.",
        )

    # Default fallback
    return (
        "Unexpected Error",
        f"An unexpected error occurred during inspection.\n\nDetails: {msg}",
    )
