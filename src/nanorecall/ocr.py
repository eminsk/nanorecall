from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, List, Optional

try:
    from PIL import Image
except ImportError:
    Image = None


@dataclass
class TextBlock:
    text: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


@dataclass
class OCRResult:
    full_text: str
    blocks: List[TextBlock] = field(default_factory=list)
    engine: str = "none"


class OCREngine:
    """
    Zero-cloud offline OCR manager.
    Prioritizes built-in Windows.Media.Ocr, with fallback to local tesseract or mock.
    """

    def __init__(self, preferred_engine: str = "auto"):
        self.preferred_engine = preferred_engine
        self._backend = self._detect_backend()

    def _detect_backend(self) -> str:
        if self.preferred_engine != "auto":
            return self.preferred_engine

        if sys.platform == "win32":
            return "windows_winrt"
        return "fallback"

    def extract_text(self, image: Any) -> OCRResult:
        """
        Extracts all visible text from an image completely offline.
        """
        if self._backend == "windows_winrt":
            try:
                res = self._run_windows_ocr(image)
                if res.full_text.strip():
                    return res
            except Exception:
                pass

        # Try Tesseract if available
        try:
            import pytesseract
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            blocks = []
            words = []
            for i, word in enumerate(data.get("text", [])):
                word = word.strip()
                if word:
                    words.append(word)
                    blocks.append(TextBlock(
                        text=word,
                        x=data["left"][i],
                        y=data["top"][i],
                        width=data["width"][i],
                        height=data["height"][i],
                    ))
            full_text = " ".join(words)
            if full_text:
                return OCRResult(full_text=full_text, blocks=blocks, engine="tesseract")
        except Exception:
            pass

        return OCRResult(full_text="", blocks=[], engine="none")

    def _run_windows_ocr(self, image: Any) -> OCRResult:
        """
        Executes Windows.Media.Ocr via native PowerShell script.
        Requires zero third-party packages or external models.
        """
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Downscale slightly if image is 4K to speed up OCR
            w, h = image.size
            if w > 1920:
                scaled = image.resize((1920, int(h * (1920 / w))), Image.Resampling.BILINEAR)
                scaled.save(tmp_path, "PNG")
            else:
                image.save(tmp_path, "PNG")

            ps_script = f"""
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation.Diagnostics, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]

$async = [Windows.Storage.StorageFile]::GetFileFromPathAsync('{tmp_path}')
$task = [System.WindowsRuntimeSystemExtensions]::AsTask($async)
$task.Wait(3000) | Out-Null
$file = $task.Result

$streamAsync = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
$streamTask = [System.WindowsRuntimeSystemExtensions]::AsTask($streamAsync)
$streamTask.Wait(3000) | Out-Null
$stream = $streamTask.Result

$decoderAsync = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
$decoderTask = [System.WindowsRuntimeSystemExtensions]::AsTask($decoderAsync)
$decoderTask.Wait(3000) | Out-Null
$decoder = $decoderTask.Result

$bmpAsync = $decoder.GetSoftwareBitmapAsync()
$bmpTask = [System.WindowsRuntimeSystemExtensions]::AsTask($bmpAsync)
$bmpTask.Wait(3000) | Out-Null
$bmp = $bmpTask.Result

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$ocrAsync = $engine.RecognizeAsync($bmp)
$ocrTask = [System.WindowsRuntimeSystemExtensions]::AsTask($ocrAsync)
$ocrTask.Wait(5000) | Out-Null
$ocrResult = $ocrTask.Result

$lines = @()
foreach ($line in $ocrResult.Lines) {{
    $lines += $line.Text
}}
$lines -join "`n"
"""
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = res.stdout.strip()
            if output:
                return OCRResult(full_text=output, blocks=[TextBlock(text=output)], engine="windows_winrt")
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        return OCRResult(full_text="", blocks=[], engine="windows_winrt")
