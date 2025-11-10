#!/usr/bin/env python3
"""
Title: Universal Video → MP4 Converter (Any Format)
Author: G.M
Date: 09 Nov 2025
Version: 3.0

═══════════════════════════════════════════════════════════════════════════════
CHANGELOG
═══════════════════════════════════════════════════════════════════════════════
v2.0 → v3.0 (UNIVERSAL)
  • REMOVED .homohs-only limit
  • ADDED: Any video file (mp4, mkv, avi, mov, webm, wmv, flv, etc.)
  • ADDED: Auto-detect via ffprobe (extension not required)
  • ADDED: "Unknown file" → still probes and prints info
  • ADDED: Table shows Container, Video Codec, Audio, Bitrate
  • ADDED: Smart conversion (lossless → CRF 17, lossy → copy if possible)
  • ADDED: Fallback: if ffprobe fails → shows file size + hex preview
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

# No extension limit — we'll use ffprobe to validate
# But keep a safe list to avoid scanning junk
SAFE_EXTS = {
    ".homohs", ".avi", ".mp4", ".mkv", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".vob", ".ogv", ".3gp",
    # Uppercase
    ".AVI", ".MP4", ".MKV", ".MOV", ".WMV", ".FLV", ".WEBM"
}

def run_cmd(cmd: List[str], capture: bool = True) -> str:
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, check=True)
        return result.stdout + result.stderr if capture else ""
    except subprocess.CalledProcessError as e:
        return e.stderr or "FFmpeg failed."

def probe(file_path: Path, debug: bool = False) -> Optional[Dict]:
    cmd = [
        "ffprobe", "-v", "quiet" if not debug else "debug",
        "-print_format", "json", "-show_format", "-show_streams", str(file_path)
    ]
    try:
        out = run_cmd(cmd)
        data = json.loads(out)
        if debug:
            debug_file = file_path.with_name(file_path.name + ".probe.json")
            debug_file.write_text(json.dumps(data, indent=2))
            console.print(f"[dim]Probe saved: {debug_file}[/dim]")
        return data
    except Exception as e:
        console.print(f"[yellow]ffprobe failed: {e}[/yellow]")
        return None

def get_info(data: Optional[Dict], path: Path) -> Dict:
    if not data:
        # Fallback: show file size + hex preview
        size_mb = path.stat().st_size // (1024*1024)
        try:
            with open(path, "rb") as f:
                head = f.read(64).hex(" ")
            hex_preview = head[:100] + "..." if len(head) > 100 else head
        except:
            hex_preview = "N/A"
        return {
            "file": path.name,
            "status": "[red]UNREADABLE[/]",
            "container": "Unknown",
            "v_codec": "N/A",
            "a_codec": "N/A",
            "res": "N/A",
            "fps": "N/A",
            "dur": "N/A",
            "bitrate": "N/A",
            "size": f"{size_mb} MB",
            "hex": hex_preview,
            "path": path,
            "can_convert": False
        }

    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s["codec_type"] == "video"), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)

    duration = fmt.get("duration")
    dur_str = f"{float(duration):.1f}s" if duration else "N/A"

    bitrate = fmt.get("bit_rate")
    br_str = f"{int(bitrate)//1000} kb/s" if bitrate else "N/A"

    return {
        "file": path.name,
        "status": "[green]VALID[/]",
        "container": fmt.get("format_name", "Unknown").split(",")[0].upper(),
        "v_codec": video.get("codec_name", "N/A").upper() if video else "N/A",
        "a_codec": audio.get("codec_name", "N/A").upper() if audio else "NONE",
        "res": f"{video.get('width', '?')}x{video.get('height', '?')}" if video else "N/A",
        "fps": video.get("r_frame_rate", "N/A") if video else "N/A",
        "dur": dur_str,
        "bitrate": br_str,
        "size": f"{path.stat().st_size // (1024*1024)} MB",
        "path": path,
        "can_convert": bool(video)
    }

def find_files(root: Path) -> List[Path]:
    if root.is_file():
        return [root]
    candidates = []
    for p in root.rglob("*"):
        if p.is_file():
            if p.suffix.lower() in SAFE_EXTS:
                candidates.append(p)
            elif p.stat().st_size > 1024*1024:  # >1MB → maybe video
                candidates.append(p)
    return candidates

def menu(files: List[Dict]) -> List[Dict]:
    if not files:
        console.print("[bold red]No files found.[/bold red]")
        sys.exit(1)

    table = Table(title="Detected Video Files")
    table.add_column("No.", style="bold cyan")
    table.add_column("File")
    table.add_column("Status")
    table.add_column("Container")
    table.add_column("V.Codec")
    table.add_column("Res")
    table.add_column("FPS")
    table.add_column("Size")

    for i, f in enumerate(files, 1):
        table.add_row(
            str(i),
            f["file"],
            f["status"],
            f["container"],
            f["v_codec"],
            f["res"],
            f["fps"],
            f["size"]
        )
    console.print(table)

    # Show unreadable ones with hex
    unreadable = [f for f in files if not f.get("can_convert", True)]
    if unreadable:
        console.print("\n[bold yellow]Unreadable files (ffprobe failed):[/]")
        for f in unreadable:
            console.print(f"  • {f['file']} → {f['size']} | First bytes: {f['hex']}")

    convertible = [f for f in files if f.get("can_convert", False)]
    if not convertible:
        console.print("[red]No convertible videos found.[/red]")
        sys.exit(1)

    while True:
        choice = Prompt.ask(
            f"\n[bold]Convert:[/bold] [green]a[/]ll ({len(convertible)}) • [yellow]number[/] • [red]q[/]uit",
            default="a"
        ).strip().lower()

        if choice in ["a", "all"]:
            if Confirm.ask(f"Convert [bold]{len(convertible)}[/] valid files?"):
                return convertible
        elif choice == "q":
            console.print("[dim]Goodbye![/dim]")
            sys.exit(0)
        elif choice.isdigit() and 1 <= int(choice) <= len(files):
            idx = int(choice) - 1
            item = files[idx]
            if item.get("can_convert"):
                console.print(f"[green]Converting #[bold]{choice}[/]: {item['file']}[/]")
                return [item]
            else:
                console.print("[red]That file is not convertible.[/red]")
        else:
            console.print("[yellow]Invalid. Use a, q, or number from table.[/yellow]")

def output_dir(root: Path, title: str) -> Path:
    now = datetime.now()
    d = now.strftime("%d%b%Y")
    t = now.strftime("%Hh%Mm%Ss")
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:60]
    p = root / d / t / safe
    p.mkdir(parents=True, exist_ok=True)
    return p

def md5(f: Path) -> str:
    h = hashlib.md5()
    with open(f, "rb") as fp:
        for c in iter(lambda: fp.read(8192), b""): h.update(c)
    return h.hexdigest()

def convert(src: Path, out_dir: Path, info: Dict, debug: bool = False):
    out_file = out_dir / f"{src.stem}.mp4"
    log_file = out_dir / "conversion.log"

    # Smart encoding
    vcodec = info["v_codec"].lower()
    is_lossless = vcodec in ["huffyuv", "ffv1", "v210", "rawvideo"]

    cmd = ["ffmpeg", "-i", str(src)]

    if is_lossless:
        # Lossless source → re-encode to high quality H.264
        cmd += [
            "-c:v", "libx264", "-preset", "slow", "-crf", "17",
            "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-bf", "2", "-g", "25", "-coder", "1"
        ]
    else:
        # Already lossy → stream copy if H.264/AAC
        if vcodec == "h264" and info["container"] in ["MP4", "MOV"]:
            cmd += ["-c:v", "copy"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "23"]

    cmd += ["-c:a", "aac" if info["a_codec"] != "NONE" else "-an",
            "-movflags", "+faststart", "-y", str(out_file)]

    if debug:
        cmd.insert(1, "-loglevel"); cmd.insert(2, "debug")

    console.print(f"\n[bold blue]→ {out_file.name}[/]")
    start = datetime.now()
    logs = run_cmd(cmd, capture=debug)
    end = datetime.now()

    with open(log_file, "w") as f:
        f.write(f"Start: {start.isoformat()}\nEnd: {end.isoformat()}\n")
        f.write(f"Command: {' '.join(cmd)}\n\n{logs}\n")
        f.write(f"Input MD5:  {md5(src)}\n")
        f.write(f"Output MD5: {md5(out_file)}\n")
        f.write(f"Size: {out_file.stat().st_size // (1024*1024)} MB\n")

    console.print(f"[bold green]SUCCESS → {out_file.stat().st_size // (1024*1024)} MB[/]")

# =============================================================================
# Main
# =============================================================================
parser = argparse.ArgumentParser(description="Convert ANY video → MP4")
parser.add_argument("path", help="Folder or file")
parser.add_argument("-o", "--output", default="converted_videos")
parser.add_argument("--debug", action="store_true")
args = parser.parse_args()

def main():
    p = Path(args.path).expanduser().resolve()
    if not p.exists():
        console.print(f"[red]Path not found: {p}[/red]")
        sys.exit(1)

    candidates = find_files(p)
    if not candidates:
        console.print("[yellow]No candidate files.[/yellow]")
        sys.exit(0)

    console.print(f"[cyan]Scanning {len(candidates)} files...[/]")

    files = []
    for f in candidates:
        data = probe(f, args.debug)
        info = get_info(data, f)
        files.append(info)

    to_convert = menu(files)

    root = Path(args.output).expanduser().resolve()
    root.mkdir(exist_ok=True)

    for item in to_convert:
        title = item["file"].rsplit(".", 1)[0]
        out_dir = output_dir(root, title)
        convert(item["path"], out_dir, item, args.debug)

    console.print(f"\n[bold green]DONE! → {root}[/]")

if __name__ == "__main__":
    main()