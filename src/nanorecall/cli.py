"""
NanoRecall Command Line Interface (CLI)
Copyright (c) 2026 eminsk (M_N_Nik@yahoo.com)
MIT License
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from nanorecall.capture import ScreenCaptureEngine
from nanorecall.memory import RecallMemory
from nanorecall.ocr import OCREngine
from nanorecall.privacy import PrivacyShield
from nanorecall.server import run_server

# Ensure UTF-8 output encoding for Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def cmd_capture(args: argparse.Namespace) -> None:
    shield = PrivacyShield()
    title, app_cls = shield.get_active_window()

    if shield.is_window_private(title, app_cls):
        print(f"🛡️  Window shielded: '{title}' [{app_cls}] is marked private. Skipped.")
        return

    engine = ScreenCaptureEngine()
    ocr = OCREngine()
    memory = RecallMemory()

    print("📸 Capturing desktop screen...")
    frame = engine.capture_frame(force_save=args.force)

    if frame.is_duplicate:
        print(f"💤 Screen unchanged (diff: {frame.diff_score*100:.2f}%). Frame skipped to save space.")
        return

    print("🔍 Extracting offline OCR text...")
    ocr_res = ocr.extract_text(frame.image)
    clean_text = shield.redact_text(ocr_res.full_text)

    print(f"🧠 Indexing into NanoVector (Window: {title or 'Active Window'})...")
    memory.index_frame(
        frame_id=frame.timestamp,
        text=clean_text,
        app_name=app_cls or "Desktop",
        window_title=title or "Active Window",
        image_path=frame.image_path or "",
        thumb_path=frame.thumb_path or "",
        timestamp=frame.timestamp,
    )
    memory.save()
    print(f"✅ Indexed frame {frame.timestamp} ({len(clean_text.split())} words, {frame.diff_score*100:.1f}% change)")


def cmd_search(args: argparse.Namespace) -> None:
    memory = RecallMemory()
    query = " ".join(args.query)

    if not query.strip():
        print("Please provide a search query. Example: nanorecall search \"github pull request\"")
        return

    t0 = time.perf_counter()
    matches = memory.search(query, top_k=args.top_k, app_filter=args.app)
    t_search_ms = (time.perf_counter() - t0) * 1000

    print(f"\n🔍 Search Query: '{query}' ({len(matches)} results found in {t_search_ms:.2f} ms)\n")
    if not matches:
        print("No matching memories found.")
        return

    for rank, m in enumerate(matches, 1):
        score_pct = int(max(0, min(100, m.score * 100)))
        print(f"#{rank} [{score_pct}% Match] {m.app_name} — {m.window_title}")
        print(f"   🕒 Captured: {m.timestamp}")
        print(f"   📝 Text:     {m.snippet or 'No snippet'}")
        if m.image_path:
            print(f"   🖼️  File:     {m.image_path}")
        print("-" * 65)


def cmd_daemon(args: argparse.Namespace) -> None:
    print(f"🚀 Starting NanoRecall Background Daemon (Interval: {args.interval}s)")
    print("Press Ctrl+C to stop.\n")

    shield = PrivacyShield()
    engine = ScreenCaptureEngine()
    ocr = OCREngine()
    memory = RecallMemory()

    try:
        while True:
            title, app_cls = shield.get_active_window()
            if shield.is_window_private(title, app_cls):
                time.sleep(args.interval)
                continue

            frame = engine.capture_frame(force_save=False)
            if not frame.is_duplicate:
                ocr_res = ocr.extract_text(frame.image)
                clean_text = shield.redact_text(ocr_res.full_text)
                memory.index_frame(
                    frame_id=frame.timestamp,
                    text=clean_text,
                    app_name=app_cls or "Desktop",
                    window_title=title or "Active Window",
                    image_path=frame.image_path or "",
                    thumb_path=frame.thumb_path or "",
                    timestamp=frame.timestamp,
                )
                memory.save()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved: {app_cls or 'Desktop'} | Diff: {frame.diff_score*100:.1f}%")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nDaemon stopped.")


def cmd_ui(args: argparse.Namespace) -> None:
    run_server(host=args.host, port=args.port)


def cmd_stats(args: argparse.Namespace) -> None:
    memory = RecallMemory()
    stats = memory.get_stats()
    print("\n⚡ NanoRecall Engine Telemetry:")
    print("-" * 40)
    print(f"Total Indexed Frames: {stats['total_frames']}")
    print(f"Vector Dimension:     {stats['vector_dim']}D")
    print(f"Active Backend:       {stats['backend']}")
    print(f"Local Database Size:  {stats['file_size_kb']} KB")
    print(f"Database Location:    {stats['file_path']}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nanorecall",
        description="100% Private, Zero-Cloud Desktop Memory & Screen Search Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # capture
    p_cap = subparsers.add_parser("capture", help="Capture and index current screen")
    p_cap.add_argument("--force", action="store_true", help="Force save even if screen is unchanged")

    # search
    p_search = subparsers.add_parser("search", help="Search desktop screen memory")
    p_search.add_argument("query", nargs="+", help="Natural language search phrase")
    p_search.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    p_search.add_argument("--app", type=str, default=None, help="Filter by application name")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run background monitor daemon")
    p_daemon.add_argument("--interval", type=float, default=3.0, help="Check interval in seconds")

    # ui
    p_ui = subparsers.add_parser("ui", help="Launch web dashboard")
    p_ui.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    p_ui.add_argument("--port", type=int, default=8765, help="Port number")

    # stats
    subparsers.add_parser("stats", help="Show database statistics and footprint")

    args = parser.parse_args()
    if args.command == "capture":
        cmd_capture(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "ui":
        cmd_ui(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
