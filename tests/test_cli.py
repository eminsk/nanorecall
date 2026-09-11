"""
Unit Tests for NanoRecall CLI
"""

import sys
from unittest.mock import patch
import pytest
from nanorecall.cli import main


def test_cli_help(capsys):
    with patch.object(sys, "argv", ["nanorecall", "--help"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "100% Private, Zero-Cloud Desktop Memory" in captured.out


def test_cli_stats(capsys):
    with patch.object(sys, "argv", ["nanorecall", "stats"]):
        main()
        captured = capsys.readouterr()
        assert "NanoRecall Engine Telemetry" in captured.out
