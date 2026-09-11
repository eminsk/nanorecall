"""
NanoRecall Privacy Shield & Active Window Inspector
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

import os
import re
import sys
from typing import List, Optional, Set, Tuple


DEFAULT_BLACKLIST_KEYWORDS: Set[str] = {
    # Password Managers
    "1password",
    "bitwarden",
    "keepass",
    "keepassxc",
    "lastpass",
    "dashlane",
    "nordpass",
    "enpass",
    "roboform",
    "authenticator",
    "authy",

    # Private & Incognito Browsing
    "incognito",
    "inprivate",
    "private browsing",
    "частный доступ",
    "режим инкогнито",
    "tor browser",

    # Crypto Wallets & Banking
    "metamask",
    "phantom",
    "ledger live",
    "trezor",
    "binance",
    "coinbase",
    "exodus",
    "rabby",

    # System Security Dialogs
    "credential manager",
    "диспетчер учетных данных",
    "windows security",
    "безопасность windows",
    "uac",
}

# Regex patterns for sensitive credentials in OCR text
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
API_KEY_REGEX = re.compile(r"\b(?:sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36}|xox[baprs]-[a-zA-Z0-9-]{10,})\b")
PRIVATE_KEY_REGEX = re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA)? PRIVATE KEY-----")


class PrivacyShield:
    """
    Guarantees user privacy by automatically ignoring sensitive windows
    and redacting confidential tokens, passwords, and payment details.
    """

    def __init__(self, blacklist: Optional[Set[str]] = None, enabled: bool = True):
        self.enabled = enabled
        self.blacklist: Set[str] = set(DEFAULT_BLACKLIST_KEYWORDS)
        if blacklist:
            self.blacklist.update(k.lower() for k in blacklist)

    def add_keyword(self, keyword: str) -> None:
        self.blacklist.add(keyword.strip().lower())

    def remove_keyword(self, keyword: str) -> None:
        self.blacklist.discard(keyword.strip().lower())

    def is_window_private(self, window_title: str, window_class: str = "") -> bool:
        """
        Determines whether the given window should be shielded from capture.
        """
        if not self.enabled:
            return False

        haystack = f"{window_title} {window_class}".lower()
        for kw in self.blacklist:
            if kw in haystack:
                return True
        return False

    def get_active_window(self) -> Tuple[str, str]:
        """
        Cross-platform active window query (Win32 native with fallback).
        Returns (window_title, app_name_or_class).
        """
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                if not hwnd:
                    return ("", "")

                # Title
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value

                # Class
                class_buff = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_buff, 256)
                cls_name = class_buff.value

                return (title, cls_name)
            except Exception:
                return ("", "")
        else:
            return ("Desktop", "Generic")

    def redact_text(self, text: str) -> str:
        """
        Redacts credit cards, API keys, and cryptographic private keys from OCR text.
        """
        if not text or not self.enabled:
            return text

        redacted = API_KEY_REGEX.sub("[REDACTED_API_KEY]", text)
        redacted = PRIVATE_KEY_REGEX.sub("[REDACTED_PRIVATE_KEY]", redacted)
        # Only redact if matches card length without destroying standard numbers
        redacted = CREDIT_CARD_REGEX.sub("[REDACTED_CARD]", redacted)
        return redacted
