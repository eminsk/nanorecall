"""
Unit Tests for NanoRecall Native MCP Server (JSON-RPC 2.0 stdio)
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from nanorecall import __version__
from nanorecall.mcp_server import (
    LATEST_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    NanoRecallMCPServer,
)


@pytest.fixture
def temp_mcp_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_mcp_initialize_negotiation(temp_mcp_dir):
    server = NanoRecallMCPServer(db_dir=temp_mcp_dir)

    # 1. Request latest supported version
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-11-25"},
    }
    resp = server.handle_request(req)
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == "2025-11-25"
    assert resp["result"]["serverInfo"]["name"] == "nanorecall-mcp"
    assert resp["result"]["serverInfo"]["version"] == __version__
    assert "tools" in resp["result"]["capabilities"]

    # 2. Request older supported version
    req_old = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }
    resp_old = server.handle_request(req_old)
    assert resp_old["result"]["protocolVersion"] == "2024-11-05"

    # 3. Request unknown/unsupported version -> fall back to latest supported version
    req_unknown = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "initialize",
        "params": {"protocolVersion": "9999-99-99"},
    }
    resp_unknown = server.handle_request(req_unknown)
    assert resp_unknown["result"]["protocolVersion"] == LATEST_PROTOCOL_VERSION


def test_mcp_ping_and_notifications(temp_mcp_dir):
    server = NanoRecallMCPServer(db_dir=temp_mcp_dir)

    # Ping
    ping_resp = server.handle_request({"jsonrpc": "2.0", "id": 10, "method": "ping"})
    assert ping_resp == {"jsonrpc": "2.0", "id": 10, "result": {}}

    # Notifications expect no response
    assert server.handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.handle_request({"jsonrpc": "2.0", "method": "initialized"}) is None


def test_mcp_tools_list_schema(temp_mcp_dir):
    server = NanoRecallMCPServer(db_dir=temp_mcp_dir)
    resp = server.handle_request({"jsonrpc": "2.0", "id": 20, "method": "tools/list"})
    assert resp["id"] == 20
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "recall_search" in tool_names
    assert "recall_capture_now" in tool_names
    assert "recall_remember" in tool_names
    assert "recall_get_stats" in tool_names

    # Verify tool metadata (annotations, title, inputSchema, outputSchema)
    for tool in tools:
        assert "name" in tool
        assert "title" in tool
        assert "description" in tool
        assert "annotations" in tool
        assert "readOnlyHint" in tool["annotations"]
        assert "inputSchema" in tool
        assert "outputSchema" in tool


def test_mcp_remember_and_search_flow(temp_mcp_dir):
    server = NanoRecallMCPServer(db_dir=temp_mcp_dir)

    # 1. Store memory via recall_remember
    call_remember = {
        "jsonrpc": "2.0",
        "id": 30,
        "method": "tools/call",
        "params": {
            "name": "recall_remember",
            "arguments": {
                "text": "Fixed SQLFluff Rule CV11 dialect bug for StarRocks parser",
                "title": "PR #8449 Fix",
                "app_name": "VSCode",
            },
        },
    }
    resp_remember = server.handle_request(call_remember)
    assert resp_remember["id"] == 30
    assert resp_remember["result"]["isError"] is False
    content = json.loads(resp_remember["result"]["content"][0]["text"])
    assert content["success"] is True
    assert content["app_name"] == "VSCode"
    assert "PR #8449" in content["title"]

    # 2. Check stats via recall_get_stats
    call_stats = {
        "jsonrpc": "2.0",
        "id": 31,
        "method": "tools/call",
        "params": {"name": "recall_get_stats", "arguments": {}},
    }
    resp_stats = server.handle_request(call_stats)
    stats_content = json.loads(resp_stats["result"]["content"][0]["text"])
    assert stats_content["total_frames"] >= 1

    # 3. Search memory via recall_search
    call_search = {
        "jsonrpc": "2.0",
        "id": 32,
        "method": "tools/call",
        "params": {
            "name": "recall_search",
            "arguments": {
                "query": "StarRocks dialect CV11 sqlfluff bug",
                "top_k": 3,
            },
        },
    }
    resp_search = server.handle_request(call_search)
    assert resp_search["result"]["isError"] is False
    search_content = json.loads(resp_search["result"]["content"][0]["text"])
    assert search_content["count"] >= 1
    top_match = search_content["matches"][0]
    assert top_match["app_name"] == "VSCode"
    assert "StarRocks" in top_match["snippet"]
    assert top_match["score"] > 0.0


def test_mcp_errors(temp_mcp_dir):
    server = NanoRecallMCPServer(db_dir=temp_mcp_dir)

    # Unknown method
    resp_unknown = server.handle_request({"jsonrpc": "2.0", "id": 40, "method": "invalid/method"})
    assert resp_unknown["error"]["code"] == -32601

    # Unknown tool
    resp_tool = server.handle_request({
        "jsonrpc": "2.0",
        "id": 41,
        "method": "tools/call",
        "params": {"name": "non_existent_tool", "arguments": {}},
    })
    assert resp_tool["result"]["isError"] is True
    assert "Unknown tool name" in resp_tool["result"]["content"][0]["text"]
