"""
Unit Tests for NanoRecall Privacy Shield
"""

import pytest
from nanorecall.privacy import PrivacyShield


def test_blacklist_detection():
    shield = PrivacyShield()

    assert shield.is_window_private("1Password — Personal Vault", "Chrome_WidgetWin_1") is True
    assert shield.is_window_private("Bitwarden Password Manager") is True
    assert shield.is_window_private("Google Chrome - Incognito Tab") is True
    assert shield.is_window_private("KeePassXC - Passwords.kdbx") is True
    assert shield.is_window_private("MetaMask Notification") is True

    # Non-private windows should pass
    assert shield.is_window_private("Visual Studio Code - nanovector.c") is False
    assert shield.is_window_private("GitHub: Where the world builds software") is False
    assert shield.is_window_private("Terminal - PowerShell") is False


def test_custom_keywords():
    shield = PrivacyShield()
    assert shield.is_window_private("Secret Project Apollo") is False

    shield.add_keyword("apollo")
    assert shield.is_window_private("Secret Project Apollo") is True

    shield.remove_keyword("apollo")
    assert shield.is_window_private("Secret Project Apollo") is False


def test_text_redaction():
    shield = PrivacyShield()

    raw = "My OpenAI API key is sk-1234567890abcdef1234567890abcdef1234 and payment card 4532 1234 5678 9012"
    redacted = shield.redact_text(raw)

    assert "sk-1234567890abcdef" not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "4532 1234 5678 9012" not in redacted
    assert "[REDACTED_CARD]" in redacted


def test_disabled_shield():
    shield = PrivacyShield(enabled=False)
    assert shield.is_window_private("1Password") is False
    assert shield.redact_text("sk-1234567890abcdef1234567890abcdef1234") == "sk-1234567890abcdef1234567890abcdef1234"
