"""
NanoRecall Local Web Dashboard Server
Zero external web framework dependencies (Standard library http.server)
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from nanorecall.capture import ScreenCaptureEngine
from nanorecall.memory import RecallMemory
from nanorecall.ocr import OCREngine
from nanorecall.privacy import PrivacyShield


class NanoRecallHandler(BaseHTTPRequestHandler):
    memory: RecallMemory
    capture_engine: ScreenCaptureEngine
    ocr_engine: OCREngine
    privacy_shield: PrivacyShield
    web_dir: Path

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP request logging in terminal
        pass

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_file(self.web_dir / "index.html", "text/html")
        elif path == "/style.css":
            self._serve_file(self.web_dir / "style.css", "text/css")
        elif path == "/app.js":
            self._serve_file(self.web_dir / "app.js", "application/javascript")
        elif path == "/api/stats":
            stats = self.memory.get_stats()
            self._send_json(stats)
        elif path == "/api/recent":
            self._handle_recent()
        elif path == "/api/search":
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0]
            matches = self.memory.search(q, top_k=20)
            data = [
                {
                    "id": m.id,
                    "score": round(m.score, 4),
                    "timestamp": m.timestamp,
                    "app_name": m.app_name,
                    "window_title": m.window_title,
                    "image_path": m.image_path,
                    "thumb_path": m.thumb_path,
                    "snippet": m.snippet,
                }
                for m in matches
            ]
            self._send_json(data)
        elif path == "/image":
            qs = parse_qs(parsed.query)
            img_path = qs.get("path", [""])[0]
            if img_path and os.path.exists(img_path):
                mime, _ = mimetypes.guess_type(img_path)
                self._serve_file(Path(img_path), mime or "application/octet-stream")
            else:
                self.send_error(404, "Image not found")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/capture":
            self._handle_manual_capture()
        else:
            self.send_error(404, "Not Found")

    def _handle_recent(self) -> None:
        # Retrieve latest items from memory
        total = len(self.memory.index)
        if total == 0:
            self._send_json([])
            return

        # Dummy search with empty or universal query to get recent top items
        matches = self.memory.search("desktop screen window application", top_k=20)
        data = [
            {
                "id": m.id,
                "score": round(m.score, 4),
                "timestamp": m.timestamp,
                "app_name": m.app_name,
                "window_title": m.window_title,
                "image_path": m.image_path,
                "thumb_path": m.thumb_path,
                "snippet": m.snippet,
            }
            for m in matches
        ]
        self._send_json(data)

    def _handle_manual_capture(self) -> None:
        title, app_cls = self.privacy_shield.get_active_window()
        if self.privacy_shield.is_window_private(title, app_cls):
            self._send_json({"status": "shielded", "message": "Active window is private. Skipped."})
            return

        frame = self.capture_engine.capture_frame(force_save=True)
        ocr_res = self.ocr_engine.extract_text(frame.image)
        clean_text = self.privacy_shield.redact_text(ocr_res.full_text)

        self.memory.index_frame(
            frame_id=frame.timestamp,
            text=clean_text,
            app_name=app_cls or "Desktop",
            window_title=title or "Active Window",
            image_path=frame.image_path or "",
            thumb_path=frame.thumb_path or "",
            timestamp=frame.timestamp,
        )
        self.memory.save()
        self._send_json({"status": "ok", "frame_id": frame.timestamp})

    def _serve_file(self, filepath: Path, content_type: str) -> None:
        if not filepath.exists():
            self.send_error(404, "File not found")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    memory: Optional[RecallMemory] = None,
    capture_engine: Optional[ScreenCaptureEngine] = None,
    ocr_engine: Optional[OCREngine] = None,
    privacy_shield: Optional[PrivacyShield] = None,
) -> None:
    """
    Launches the local NanoRecall web UI server.
    """
    web_dir = Path(__file__).parent / "web"
    mem = memory or RecallMemory()
    cap = capture_engine or ScreenCaptureEngine()
    ocr = ocr_engine or OCREngine()
    priv = privacy_shield or PrivacyShield()

    class ConfiguredHandler(NanoRecallHandler):
        pass

    ConfiguredHandler.memory = mem
    ConfiguredHandler.capture_engine = cap
    ConfiguredHandler.ocr_engine = ocr
    ConfiguredHandler.privacy_shield = priv
    ConfiguredHandler.web_dir = web_dir

    server = HTTPServer((host, port), ConfiguredHandler)
    print(f"🚀 NanoRecall Dashboard live at: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NanoRecall server.")
        server.server_close()
