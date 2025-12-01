"""
Unit tests for the error handler module.
"""

import pytest
import dns.exception
import requests.exceptions
from src.ui.error_handler import get_user_friendly_error


def test_get_user_friendly_error_connection_refused():
    """Test mapping of connection refused error."""
    # Simulate a connection refused error message
    err = requests.exceptions.ConnectionError(
        "Connection refused by localhost"
    )
    title, msg = get_user_friendly_error(err)
    assert title == "Connection Failed"
    assert "Could not connect" in msg


def test_get_user_friendly_error_dns():
    """Test mapping of DNS error."""
    err = dns.exception.DNSException("The DNS query name does not exist")
    # Our simple check looks for "DNS" in the message or type
    title, msg = get_user_friendly_error(err)
    assert title == "DNS Error"
    assert "Could not resolve" in msg


def test_get_user_friendly_error_timeout():
    """Test mapping of timeout error."""
    err = requests.exceptions.Timeout("Read timed out")
    title, msg = get_user_friendly_error(err)
    assert title == "Connection Timed Out"
    assert "timed out" in msg


def test_get_user_friendly_error_ssl():
    """Test mapping of SSL error."""
    err = requests.exceptions.SSLError("certificate verify failed")
    title, msg = get_user_friendly_error(err)
    assert title == "SSL/TLS Error"
    assert "security error" in msg


def test_get_user_friendly_error_generic():
    """Test fallback for generic error."""
    err = Exception("Something weird happened")
    title, msg = get_user_friendly_error(err)
    assert title == "Unexpected Error"
    assert "Something weird happened" in msg
