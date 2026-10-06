"""
Native Model Context Protocol (MCP) Server for NanoRecall.
Exposes private desktop screen memory search, screen capture indexing,
episodic fact recall, and database stats to Claude Desktop, Cursor,
Windsurf, Antigravity, and any MCP-compatible AI agent over JSON-RPC 2.0 stdio.

Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from nanorecall import __version__
from nanorecall.capture import ScreenCaptureEngine
from nanorecall.memory import RecallMemory
from nanorecall.ocr import OCREngine
from nanorecall.privacy import PrivacyShield

SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2024-11-05")
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

MCP_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "recall_search",
        "title": "Search Desktop Screen Memory & Semantic History",
        "description": (
            "Semantic vector search across indexed desktop screens, OCR text, and application "
            "windows. Returns ranked memory matches with application names, window titles, OCR text "
            "snippets, timestamps, and similarity scores."
        ),
        "annotations": {
            "readOnlyHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search phrase (e.g. 'pull request comments', 'docker-compose error', 'zoom meeting action items')",
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of memory results to return (default: 5)",
                },
                "app_name": {
                    "type": "string",
                    "description": "Optional application filter (e.g. 'Code', 'Chrome', 'WindowsTerminal', 'Slack')",
                },
            },
            "required": ["query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer"},
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "score": {"type": "number"},
                            "timestamp": {"type": "string"},
                            "app_name": {"type": "string"},
                            "window_title": {"type": "string"},
                            "snippet": {"type": "string"},
                            "image_path": {"type": "string"},
                            "thumb_path": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
    {
        "name": "recall_capture_now",
        "title": "Capture & Index Current Desktop Screen",
        "description": (
            "Instantly captures the user's active desktop screen, runs offline privacy-shielded OCR "
            "text extraction, and indexes the screen frame into NanoRecall episodic vector memory."
        ),
        "annotations": {
            "readOnlyHint": False,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Force save even if screen content appears identical to the previous frame",
                },
                "app_override": {
                    "type": "string",
                    "description": "Optional application name override",
                },
                "title_override": {
                    "type": "string",
                    "description": "Optional window title override",
                },
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "frame_id": {"type": "string"},
                "app_name": {"type": "string"},
                "window_title": {"type": "string"},
                "snippet": {"type": "string"},
                "diff_score": {"type": "number"},
            },
        },
    },
    {
        "name": "recall_remember",
        "title": "Store Custom Text Note or Fact into Memory",
        "description": (
            "Manually store a custom fact, user preference, workflow note, or code snippet into "
            "NanoRecall's persistent episodic vector index without capturing screen."
        ),
        "annotations": {
            "readOnlyHint": False,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Fact, preference, or text content to store",
                },
                "title": {
                    "type": "string",
                    "default": "User Note",
                    "description": "Context title or description (default: 'User Note')",
                },
                "app_name": {
                    "type": "string",
                    "default": "Assistant",
                    "description": "Associated application or category tag (default: 'Assistant')",
                },
            },
            "required": ["text"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "frame_id": {"type": "string"},
                "title": {"type": "string"},
                "app_name": {"type": "string"},
                "snippet": {"type": "string"},
            },
        },
    },
    {
        "name": "recall_get_stats",
        "title": "Get NanoRecall Memory Database Statistics",
        "description": (
            "Retrieve memory statistics: total indexed screen frames, vector dimension, "
            "backend engine (NanoVector AVX2/NEON vs Fallback), database size in KB, and storage path."
        ),
        "annotations": {
            "readOnlyHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total_frames": {"type": "integer"},
                "vector_dim": {"type": "integer"},
                "backend": {"type": "string"},
                "file_size_kb": {"type": "number"},
                "file_path": {"type": "string"},
            },
        },
    },
]


class NanoRecallMCPServer:
    """Model Context Protocol (MCP) JSON-RPC 2.0 stdio server for NanoRecall."""

    def __init__(
        self,
        db_dir: Optional[Path] = None,
        memory: Optional[RecallMemory] = None,
        capture_engine: Optional[ScreenCaptureEngine] = None,
        ocr_engine: Optional[OCREngine] = None,
        privacy_shield: Optional[PrivacyShield] = None,
    ):
        self.db_dir = Path(db_dir) if db_dir else None
        self._memory = memory
        self._capture_engine = capture_engine
        self._ocr_engine = ocr_engine
        self._privacy_shield = privacy_shield

    @property
    def memory(self) -> RecallMemory:
        if self._memory is None:
            self._memory = RecallMemory(db_dir=self.db_dir)
        return self._memory

    @property
    def capture_engine(self) -> ScreenCaptureEngine:
        if self._capture_engine is None:
            frames_dir = (self.db_dir / "frames") if self.db_dir else None
            self._capture_engine = ScreenCaptureEngine(storage_dir=frames_dir)
        return self._capture_engine

    @property
    def ocr_engine(self) -> OCREngine:
        if self._ocr_engine is None:
            self._ocr_engine = OCREngine()
        return self._ocr_engine

    @property
    def privacy_shield(self) -> PrivacyShield:
        if self._privacy_shield is None:
            self._privacy_shield = PrivacyShield()
        return self._privacy_shield

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single JSON-RPC 2.0 message and return a response dict (or None for notifications)."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params") or {}

        # Notifications have no id and expect no response
        if req_id is None and (method.startswith("notifications/") or method == "initialized"):
            return None

        try:
            if method == "initialize":
                requested_version = params.get("protocolVersion")
                negotiated_version = (
                    requested_version
                    if isinstance(requested_version, str) and requested_version in SUPPORTED_PROTOCOL_VERSIONS
                    else LATEST_PROTOCOL_VERSION
                )
                result = {
                    "protocolVersion": negotiated_version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "nanorecall-mcp",
                        "version": __version__,
                    },
                    "instructions": (
                        "NanoRecall provides 100% private desktop screen memory search and episodic "
                        "knowledge recall. Use 'recall_search' to find past screen contexts, notes, or "
                        "windows, 'recall_capture_now' to index the active display, and 'recall_remember' "
                        "to persist custom facts without cloud telemetry."
                    ),
                }
                return {"jsonrpc": "2.0", "id": req_id, "result": result}

            if method == "ping":
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}

            if method == "tools/list":
                return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS_SCHEMA}}

            if method == "tools/call":
                tool_name = params.get("name", "")
                args = params.get("arguments") or {}
                with contextlib.redirect_stdout(sys.stderr):
                    tool_output = self._call_tool(tool_name, args)
                call_result: dict[str, Any] = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_output, ensure_ascii=False, indent=2),
                        }
                    ],
                    "isError": False,
                }
                if isinstance(tool_output, dict):
                    call_result["structuredContent"] = tool_output
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": call_result,
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            }

    def _call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        if name == "recall_search":
            query = str(args.get("query", "")).strip()
            top_k = int(args.get("top_k", 5))
            app_filter = args.get("app_name")
            matches = self.memory.search(query=query, top_k=top_k, app_filter=app_filter)
            return {
                "query": query,
                "count": len(matches),
                "matches": [
                    {
                        "id": m.id,
                        "score": round(float(m.score), 4),
                        "timestamp": m.timestamp,
                        "app_name": m.app_name,
                        "window_title": m.window_title,
                        "snippet": m.snippet,
                        "image_path": m.image_path,
                        "thumb_path": m.thumb_path,
                    }
                    for m in matches
                ],
            }

        if name == "recall_capture_now":
            force = bool(args.get("force", False))
            title_override = args.get("title_override")
            app_override = args.get("app_override")

            active_title, active_cls = self.privacy_shield.get_active_window()
            window_title = title_override or active_title or "Active Window"
            app_name = app_override or active_cls or "Desktop"

            if self.privacy_shield.is_window_private(window_title, app_name):
                return {
                    "success": False,
                    "message": f"Window '{window_title}' [{app_name}] is shielded as private. Capture skipped.",
                    "app_name": app_name,
                    "window_title": window_title,
                }

            frame = self.capture_engine.capture_frame(force_save=force)
            if frame.is_duplicate and not force:
                return {
                    "success": True,
                    "message": "Screen unchanged from previous capture. Duplicate frame skipped to save storage.",
                    "diff_score": round(float(frame.diff_score), 4),
                    "timestamp": frame.timestamp,
                }

            if frame.image is None:
                return {
                    "success": False,
                    "message": "Failed to capture display screen (headless environment or display unavailable).",
                }

            ocr_res = self.ocr_engine.extract_text(frame.image)
            clean_text = self.privacy_shield.redact_text(ocr_res.full_text)

            self.memory.index_frame(
                frame_id=frame.timestamp,
                text=clean_text,
                app_name=app_name,
                window_title=window_title,
                image_path=frame.image_path or "",
                thumb_path=frame.thumb_path or "",
                timestamp=frame.timestamp,
            )
            self.memory.save()

            snippet = " ".join(clean_text.split())[:160]
            return {
                "success": True,
                "message": "Screen frame captured and indexed successfully.",
                "frame_id": frame.timestamp,
                "app_name": app_name,
                "window_title": window_title,
                "snippet": snippet,
                "diff_score": round(float(frame.diff_score), 4),
            }

        if name == "recall_remember":
            text = str(args.get("text", "")).strip()
            if not text:
                raise ValueError("Parameter 'text' is required and cannot be empty.")

            title = str(args.get("title", "User Note")).strip()
            app_name = str(args.get("app_name", "Assistant")).strip()
            frame_id = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            now_iso = datetime.now().isoformat()

            self.memory.index_frame(
                frame_id=frame_id,
                text=text,
                app_name=app_name,
                window_title=title,
                timestamp=now_iso,
            )
            self.memory.save()

            return {
                "success": True,
                "frame_id": frame_id,
                "title": title,
                "app_name": app_name,
                "snippet": text[:160],
            }

        if name == "recall_get_stats":
            return self.memory.get_stats()

        raise ValueError(f"Unknown tool name: {name}")

    def run_stdio(self) -> None:
        """Run the JSON-RPC stdio event loop."""
        if sys.platform == "win32":
            try:
                import msvcrt
                msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            except Exception:
                pass

        buffer = ""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                buffer += line
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                try:
                    request = json.loads(line_stripped)
                except json.JSONDecodeError:
                    continue

                response = self.handle_request(request)
                if response is not None:
                    out = json.dumps(response, ensure_ascii=False) + "\n"
                    sys.stdout.write(out)
                    sys.stdout.flush()

            except (KeyboardInterrupt, BrokenPipeError):
                break
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                }
                sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()


def main_mcp() -> None:
    """Entry point for the nanorecall-mcp standalone executable/command."""
    server = NanoRecallMCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main_mcp()
