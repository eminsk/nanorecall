When Microsoft announced **Windows Recall** — a feature that silently captures your screen every few seconds so you can search your past activity — the tech community had two immediate reactions:

1. **"The concept is actually super useful."** Everyone has closed a browser tab, lost a terminal command, or forgotten a link sent in a chat days ago.
2. **"The execution is a privacy and security disaster."** 
   - Unencrypted local storage vulnerable to malware.
   - Cloud telemetry concerns.
   - **Hardware lock-in:** Microsoft claimed you must buy a brand new **$1,500+ Copilot+ PC** with a 40+ TOPS NPU chip just to search your own screen!

I refused to accept that a simple screen search engine requires gigabytes of OS bloat and specialized AI silicon. 

So, I built **[NanoRecall](https://github.com/eminsk/nanorecall)**: an open-source, 100% private, zero-cloud desktop memory engine in **<200KB of code that runs on any standard CPU at sub-millisecond speeds**.

---

## 🖥️ The Interactive Dark-Mode Dashboard

Here is what it looks like running locally on your PC (`nanorecall ui`):

![NanoRecall Dashboard](https://raw.githubusercontent.com/eminsk/nanorecall/main/assets/dashboard_preview.jpg)

- **Search Bar:** Type any natural query (*"sqlfluff pull request 8449 github"*, *"docker crash error"*, *"hotel reservation receipt"*).
- **Daily Timeline:** Scrub your day hour-by-hour (09:00 ➔ 14:00 ➔ 20:00) with visual activity heatmaps.
- **Privacy Shield:** Active window detection that automatically shields password managers and private browsing tabs.

---

## ⚡ Feature Comparison: Microsoft Recall vs. NanoRecall

| Feature | Microsoft Windows Recall | **NanoRecall (This Project)** |
| :--- | :---: | :---: |
| **Privacy & Cloud** | Unencrypted storage, telemetry risks | **100% Local & Encrypted** (Zero bytes leave your PC) |
| **Hardware Requirement** | Requires **Copilot+ PC ($1500+)** with 40+ TOPS NPU | **Runs on any standard Intel / AMD / ARM CPU** |
| **Vector Engine** | Heavy proprietary runtime | **[NanoVector](https://github.com/eminsk/nanovector)** (Pure C99 + AVX2, <120KB footprint) |
| **Search Latency** | Variable (Cloud / NPU overhead) | **0.28 ms** (Sub-millisecond exact semantic search) |
| **Password Protection** | Records sensitive credentials and cards | **Privacy Shield**: Auto-ignores 1Password, Bitwarden, KeePass, Incognito |
| **Storage Footprint** | Tens of gigabytes of raw frames | **Smart Frame Differencing**: Suppresses static frames (30–60 KB/frame) |
| **Code Footprint** | Gigabytes of OS bloatware | **<200 KB pure codebase**, <25MB RAM idle, 0.1% CPU |

---

## 🏛️ Architecture: How It Works Under the Hood

NanoRecall is built with zero cloud dependencies using standard Python and bare-metal C99 SIMD:

```
                     ┌────────────────────────────────┐
                     │     Windows Desktop Display    │
                     └───────────────┬────────────────┘
                                     │
                        (Perceptual Diffing / 0.1% CPU)
                                     │
                     ┌───────────────▼────────────────┐
                     │    Native Win32 Screen Capture │
                     │  (GDI / BitBlt / DirectMemory) │
                     └───────────────┬────────────────┘
                                     │
                     ┌───────────────▼────────────────┐
                     │    Offline Text Extraction     │
                     │  (Windows.Media.Ocr / Local)   │
                     └───────────────┬────────────────┘
                                     │
                                     ├───────────────────────────────┐
                                     │ Text + Embeddings             │ Compressed Frame
                                     ▼                               ▼
                     ┌────────────────────────────────┐  ┌───────────────────────┐
                     │       NanoVector Core          │  │   Local Image Store   │
                     │  (C99 AVX2 + .nvec persistence)│  │   (WebP / 30-60 KB)   │
                     └───────────────┬────────────────┘  └───────────┬───────────┘
                                     │                               │
                                     └───────────────┬───────────────┘
                                                     ▼
                                     ┌────────────────────────────────┐
                                     │     Search & Recall Engine     │
                                     │   (CLI + Dark-Mode Dashboard)  │
                                     └────────────────────────────────┘
```

### 1. Smart Perceptual Frame Differencing (0.1% Idle CPU)
Instead of blindly capturing screenshots every 3 seconds and exhausting your SSD, NanoRecall calculates a fast 32x32 grayscale perceptual fingerprint. If the screen hasn't changed by at least 1.5% (reading, typing a note, or stepped away for coffee), capture is automatically skipped.

### 2. Built-in Privacy Shield
Through Win32 API hooks (`GetForegroundWindow`), NanoRecall constantly inspects the active window title and class. Whenever password managers (`1Password`, `Bitwarden`, `KeePassXC`), private browsing windows (`Incognito`, `InPrivate`), or crypto wallets (`MetaMask`, `Ledger`) are focused, capture is **instantly paused**. Sensitive tokens (`sk-...` keys, credit cards) are redacted via regex before indexing.

### 3. Sub-Millisecond Search Powered by NanoVector
For vector search, it directly utilizes **[NanoVector](https://github.com/eminsk/nanovector)**, a minimalist ~120KB C99 SIMD engine with AVX2 and ARM NEON unrolled kernels. Your entire desktop memory history is packed into a single binary `.nvec` file that loads in milliseconds.

---

## 🚀 60-Second Quickstart

NanoRecall is packaged and published on PyPI. You can install and try it right now on Windows, Linux, or macOS:

```bash
pip install nanorecall
```

### 1. Capture Your Current Screen
```bash
nanorecall capture
```
Output:
```text
📸 Capturing desktop screen...
🔍 Extracting offline OCR text...
🧠 Indexing into NanoVector (Window: Active Window)...
✅ Indexed frame 2026-09-11_142315 (342 words, 98.4% change)
```

### 2. Search Anything from Your Past (CLI)
```bash
nanorecall search "github pull request sqlfluff"
```
Output:
```text
🔍 Search Query: 'github pull request sqlfluff' (1 results found in 0.28 ms)

#1 [98% Match] Google Chrome — sqlfluff pull request 8449 github
   🕒 Captured: 2026-09-11_142315
   📝 Text:     merged upstream/main to pull in CI fix and added StarRocks test cases...
   🖼️  File:     ~/.nanorecall/frames/2026-09-11_142315.webp
```

### 3. Launch the Local Web Dashboard
```bash
nanorecall ui
```
Open `http://127.0.0.1:8765` in your browser to explore your visual timeline and search interactively!

---

## 🧪 Try It in Your Browser (Google Colab)

Don't want to install anything locally yet? Run the live interactive demo directly in Google Colab:

👉 **[Open NanoRecall Quickstart in Google Colab](https://colab.research.google.com/github/eminsk/nanorecall/blob/main/notebooks/nanorecall_quickstart.ipynb)**

### Colab CPU Benchmark Results:
Testing search latency over thousands of recorded desktop frames on a standard virtual CPU:

| Stored Frames ($N$) | Search Latency | Throughput (QPS) |
| :--- | :---: | :---: |
| **$N = 500$** | **0.023 ms (23 µs)** | **44,014 QPS** |
| **$N = 2,000$** | **0.071 ms (71 µs)** | **14,130 QPS** |
| **$N = 10,000$** | **0.320 ms (320 µs)** | **3,128 QPS** |

Even with **10,000 recorded desktop screens**, search executes in **under 1/3 of a millisecond**!

---

## 🔗 Links & Open Source

NanoRecall is 100% open source under the MIT license:

* 🌟 **GitHub Repository:** [github.com/eminsk/nanorecall](https://github.com/eminsk/nanorecall)
* 📦 **PyPI Package:** [pypi.org/project/nanorecall](https://pypi.org/project/nanorecall/)
* ⚡ **Core Vector Engine:** [github.com/eminsk/nanovector](https://github.com/eminsk/nanovector)

If you believe software should be private, lightweight, and respect user autonomy, drop a ⭐ on GitHub and let me know what features you'd like to see next!
