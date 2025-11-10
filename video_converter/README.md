# Universal Video → MP4 Converter  
**`convert_any_video_to_mp4.py` – v3.0**  
*Author: G.M* | *Date: 09 Nov 2025*  

---

## What It Does
Converts **any video file** (`.homohs`, `.avi`, `.mp4`, `.mkv`, `.mov`, `.wmv`, `.flv`, `.webm`, raw, etc.) into a **high-quality, web-ready MP4** using **FFmpeg**.

* **Detects format automatically** with `ffprobe` – no need to know the extension.  
* **Smart encoding**:  
  * Lossless sources (HuffYUV, FFV1, raw) → **CRF 17** (near-lossless).  
  * Already-lossy H.264 → **stream-copy** (instant).  
  * Everything else → **CRF 23** (excellent).  
* **Hardware acceleration** (Apple Silicon, NVIDIA, etc.) when possible.  
* **Structured output**:  
  ```
  converted_videos/
  └── 10Nov2025/
      └── 09h11m22s/
          └── clip_name/
              ├── clip_name.mp4
              └── conversion.log
  ```
* **Full logging + MD5 checksums** for verification.  
* **Interactive menu** – pick one file or convert all.  
* **Debug mode** (`--debug`) dumps raw `ffprobe` JSON and verbose FFmpeg logs.  

---

## Requirements

| Tool | Install Command |
|------|-----------------|
| **Python 3.9+** | `brew install python` (macOS) or system default |
| **FFmpeg** (with `ffprobe`) | `brew install ffmpeg` (macOS) <br> `sudo apt install ffmpeg` (Ubuntu) <br> `choco install ffmpeg` (Windows) |
| **Python packages** | `pip install rich` |

> **Verify FFmpeg**  
> ```bash
> ffmpeg -version
> ffprobe -version
> ```

---

## Quick Start

```bash
# 1. Clone / copy the script
cp convert_any_video_to_mp4.py ~/video_tools/

# 2. Install deps
pip install rich

# 3. Run on a folder
python3 convert_any_video_to_mp4.py "/path/to/your/clips"
```

---

## Usage

```text
python3 convert_any_video_to_mp4.py <path> [-o OUTPUT_ROOT] [--debug]
```

| Argument | Description |
|--------|-------------|
| `<path>` | Folder **or** single file |
| `-o`, `--output` | Root output folder (default: `converted_videos`) |
| `--debug` | Verbose FFmpeg + save `*.probe.json` |

---

## Interactive Menu

```
Detected Video Files
┏━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━┳━━━━━━┓
┃ No ┃ File             ┃ Status ┃ Container ┃ V.Codec ┃ Res       ┃ FPS ┃ Size ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━╇━━━━━━┩
│ 1  │ clip_01.homohs   │ VALID  │ AVI       │ HUFFYUV │ 2472x2064 │ 25  │ 294 MB│
│ 2  │ clip_02.mov      │ VALID  │ MOV       │ H264    │ 1920x1080 │ 30  │  45 MB│
│ 3  │ unknown.bin      │ UNREADABLE│ Unknown│ N/A     │ N/A       │ N/A │ 512 MB│
└────┴──────────────────┴────────┴───────────┴─────────┴───────────┴─────┴──────┘

Unreadable files:
  • unknown.bin → First bytes: 1a 45 df a3 ...

Action: all (2) • number • quit: a
```

* Type **`a`** → convert **all valid** files  
* Type **`1`**, **`2`**, … → convert **one**  
* Type **`q`** → quit  
* Invalid → friendly prompt repeats  

---

## Output Structure

```
converted_videos/
└── 10Nov2025/
    └── 09h11m22s/
        └── clip_01_homohs/
            ├── clip_01_homohs.mp4
            └── conversion.log
```

**Log contains**:  
* FFmpeg command  
* Start/end time  
* Input & output MD5  
* Output size  

---

## Troubleshooting

| Symptom | Cause | Fix |
|--------|-------|-----|
| `No .homohs files.` | Wrong path or no video files | Double-check path, use quotes |
| `ffprobe failed` | FFmpeg not in PATH | Run `ffmpeg -version` |
| `UNREADABLE` + hex dump | Not a video (data file) | Rename or ignore |
| Output blurry | Using `--debug` or low CRF | Remove `--debug`, use CRF 17 |
| Conversion slow | Using `libx264` on CPU | Add `-c:v h264_videotoolbox` (macOS) |
| Audio missing | Source has no audio | Normal – script adds `-an` |
| Menu won’t accept number | Typing `number 1` | Just type `1` |

---

## Changelog (Synced with Script)

```
v3.0 – Universal converter
  • Any video file (no extension limit)
  • ffprobe fallback + hex preview
  • Smart CRF / stream-copy
  • Unreadable file reporting

v2.0 – MAX QUALITY
  • CRF 17 + libx264 slow
  • Full changelog in script
  • Better menu

v1.3 – Quality boost
  • Switched to libx264 CRF 17
  • Removed VideoToolbox CRF warning

v1.2 – Menu fixed
  • Accepts 1, 2, a, q
  • No more “invalid option” spam

v1.1 – Audio & faststart
  • -an, +faststart, -q:v 20

v1.0 – Initial .homohs support
```

---

## Need Help?

* **X:** [@Artifioicus](https://x.com/Artifioicus)  
* **Country:** Netherlands (NL)  
* **Time Zone:** CET  

Feel free to DM with logs or screenshots!

---

## License

```
MIT License – Free to use, modify, and share.
```

---

**You now have a professional-grade, self-documenting video pipeline.**  
Just run the script — the `README.md` is your **permanent guide**.

Let me know when you want:
* Batch mode (no menu)  
* Auto-upload to cloud  
* Web UI  
* Docker container  

We’re ready to scale.  


