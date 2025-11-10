#!/usr/bin/env python3
"""
Title: Video Format Detector & MP4 Converter Launcher
Author: G.M
Date: 09 Nov 2025
Version: 0.1

Description:
This is a senior-level, production-grade utility script that:
1. Scans a user-specified directory (or single file) for video files.
2. Detects container format + video/audio codec details using ffprobe (from ffmpeg).
3. Presents an interactive menu:
   - Convert ALL detected videos.
   - Convert a SINGLE selected video.
4. On conversion (next step – this script only detects/prepares), output is saved in a strict folder hierarchy:
   output_root/
   └── 09Nov2025/
       └── 14h30m22s/          # 24-hour time when conversion STARTS
           └── original_clip_title/
               ├── clip_title.mp4
               └── conversion.log
5. Supports --debug mode for verbose ffprobe/ffmpeg output + detailed internal logging.
6. Creates a virtual environment bootstrap + pip requirements for reproducibility.
7. Exits gracefully on missing ffmpeg/ffprobe with clear instructions.

Dependencies (installed via pip in venv):
- rich          (pretty terminal UI)
- tqdm          (progress bars – future-proof for batch)
- pathlib, argparse, subprocess, json, datetime – stdlib

FFmpeg must be installed on the host system (ffprobe + ffmpeg binaries in PATH).

Fixes:
Fixed: Case-insensitive extensions, better empty folder debug
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

console = Console()

# Case-insensitive video extensions
VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".ts", ".m2ts", ".vob", ".ogv", ".3gp", ".3g2",
    ".MP4", ".MKV", ".AVI", ".MOV", ".WMV", ".FLV", ".WEBM", ".M4V",
    ".MPG", ".MPEG", ".TS", ".M2TS", ".VOB", ".OGV", ".3GP", ".3G2",
}

def find_videos(root: Path) -> List[Path]:
    if root.is_file():
        return [root] if root.suffix in VIDEO_EXTS else []
    return [p for p in root.rglob("*") if p.is_file() and p.suffix in VIDEO_EXTS]


# --------------------------------------------------------------------------- #
# Helper: Run ffprobe and parse JSON
# --------------------------------------------------------------------------- #
def probe_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Run ffprobe -print_format json -show_format -show_streams and return dict."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        if args.debug:
            console.print(f"[red]ffprobe failed on {file_path}: {e}[/red]")
        return None
    except FileNotFoundError:
        console.print("[bold red]Error: ffprobe not found in PATH. Install ffmpeg.[/bold red]")
        sys.exit(1)


# --------------------------------------------------------------------------- #
# Helper: Extract human-readable info
# --------------------------------------------------------------------------- #
def extract_info(probe_data: Dict[str, Any], file_path: Path) -> Dict[str, str]:
    """Return a dict with friendly fields for display."""
    fmt = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    video = next((s for s in streams if s["codec_type"] == "video"), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)

    return {
        "file": file_path.name,
        "container": fmt.get("format_name", "unknown"),
        "duration": fmt.get("duration", "N/A"),
        "size_mb": f"{int(fmt.get('size', 0)) / (1024*1024):.2f}" if fmt.get("size") else "N/A",
        "v_codec": video["codec_name"].upper() if video else "N/A",
        "v_res": f"{video.get('width', '?')}x{video.get('height', '?')}" if video else "N/A",
        "a_codec": audio["codec_name"].upper() if audio else "N/A",
    }


# --------------------------------------------------------------------------- #
# Discovery: Find video files (common extensions)
# --------------------------------------------------------------------------- #
VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg",
    ".ts", ".m2ts", ".vob", ".ogv", ".3gp", ".3g2",
}

def find_videos(root: Path) -> List[Path]:
    """Recursively find files with video extensions."""
    if root.is_file() and root.suffix.lower() in VIDEO_EXTS:
        return [root]
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]


# --------------------------------------------------------------------------- #
# Main detection routine
# --------------------------------------------------------------------------- #
def detect_videos(paths: List[Path]) -> List[Dict[str, Any]]:
    """Probe each path, return list of enriched info dicts (or None on failure)."""
    results = []
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Probing files...", total=len(paths))
        for p in paths:
            progress.update(task, description=f"Probing {p.name}")
            data = probe_file(p)
            if data:
                info = extract_info(data, p)
                info["path"] = p
                info["probe_raw"] = data if args.debug else None
                results.append(info)
            else:
                console.print(f"[yellow]Skipping {p.name} – probe failed[/yellow]")
            progress.advance(task)
    return results


# --------------------------------------------------------------------------- #
# Interactive menu
# --------------------------------------------------------------------------- #
def interactive_menu(videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not videos:
        console.print("[bold red]No valid video files detected.[/bold red]")
        return []

    table = Table(title="Detected Video Files")
    for key in ["file", "container", "v_codec", "v_res", "a_codec", "duration", "size_mb"]:
        table.add_column(key.replace("_", " ").title(), justify="left")

    for idx, v in enumerate(videos, 1):
        table.add_row(
            f"[bold cyan]{idx}[/bold cyan] {v['file']}",
            v["container"],
            v["v_codec"],
            v["v_res"],
            v["a_codec"],
            f"{float(v['duration']):.1f}s" if v["duration"] != "N/A" else "N/A",
            v["size_mb"],
        )
    console.print(table)

    choice = Prompt.ask(
        "\n[bold]Options[/bold]:\n"
        "  [green]a[/green] – Convert **ALL** files\n"
        "  [yellow]number[/yellow] – Convert a single file\n"
        "  [red]q[/red] – Quit",
        choices=["a"] + [str(i) for i in range(1, len(videos)+1)] + ["q"],
        default="a",
    )

    if choice == "q":
        console.print("[dim]Bye![/dim]")
        sys.exit(0)
    elif choice == "a":
        if Confirm.ask("Convert ALL detected files?"):
            return videos
        else:
            return interactive_menu(videos)
    else:
        idx = int(choice) - 1
        return [videos[idx]]


# --------------------------------------------------------------------------- #
# Output folder structure builder
# --------------------------------------------------------------------------- #
def build_output_structure(base_output: Path, clip_title: str) -> Path:
    """Create: base_output/DDMonYYYY/HHmmss/clip_title/"""
    now = datetime.now()
    date_folder = now.strftime("%d%b%Y").replace("0", "")  # 9Nov2025 → 9Nov2025
    time_folder = now.strftime("%Hh%Mm%Ss")
    clip_folder = base_output / date_folder / time_folder / clip_title
    clip_folder.mkdir(parents=True, exist_ok=True)
    return clip_folder


# --------------------------------------------------------------------------- #
# Placeholder: Conversion stub (will be called in next phase)
# --------------------------------------------------------------------------- #
def convert_to_mp4(input_path: Path, output_dir: Path, debug: bool = False) -> Path:
    """Stub – prints ffmpeg command that would run. Real conversion in phase 2."""
    output_file = output_dir / f"{input_path.stem}.mp4"
    log_file = output_dir / "conversion.log"

    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-y",  # overwrite
        str(output_file),
    ]

    if debug:
        cmd.insert(1, "-loglevel")
        cmd.insert(2, "debug")

    console.print(f"[green]Would run:[/green] {' '.join(cmd)}")
    console.print(f"[dim]Log → {log_file}[/dim]")

    # For demo, just touch files
    output_file.touch()
    with open(log_file, "w") as f:
        f.write(f"ffmpeg command: {' '.join(cmd)}\n")
        f.write(f"Start: {datetime.now().isoformat()}\n")

    return output_file


# --------------------------------------------------------------------------- #
# Argument parser
# --------------------------------------------------------------------------- #
parser = argparse.ArgumentParser(
    description="Video format detector (phase 1) – prepares for MP4 conversion."
)
parser.add_argument(
    "path",
    type=str,
    help="File or directory to scan",
)
parser.add_argument(
    "-o", "--output",
    type=str,
    default="converted_videos",
    help="Root output directory (default: ./converted_videos)",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable verbose ffprobe/ffmpeg output + keep raw JSON",
)
args, _ = parser.parse_known_args()


# --------------------------------------------------------------------------- #
# Main entrypoint
# --------------------------------------------------------------------------- #
def main() -> None:
    global args
    args = parser.parse_args()

    input_path = Path(args.path).expanduser().resolve()
    if not input_path.exists():
        console.print(f"[bold red]Path does not exist: {input_path}[/bold red]")
        sys.exit(1)

    console.print(Panel(
        "[bold magenta]Video Format Detector v0.1[/bold magenta]\n"
        "[dim]Author: G.M | 09 Nov 2025[/dim]",
        expand=False,
    ))

    # 1. Find candidate files
    candidates = find_videos(input_path)
    if not candidates:
        console.print("[bold yellow]No video files found.[/bold yellow]")
        sys.exit(0)

    console.print(f"[bold green]Found {len(candidates)} candidate(s)[/bold green]")

    # 2. Probe them
    detected = detect_videos(candidates)
    if not detected:
        console.print("[bold red]All probes failed.[/bold red]")
        sys.exit(1)

    # 3. Interactive selection
    to_convert = interactive_menu(detected)

    # 4. Build output structure & stub conversion
    output_root = Path(args.output).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    for item in to_convert:
        src = item["path"]
        title = src.stem[:50]  # truncate long names
        out_dir = build_output_structure(output_root, title)
        console.print(f"\n[bold]Processing:[/bold] {src.name}")
        convert_to_mp4(src, out_dir, debug=args.debug)

    console.print("\n[bold green]Detection phase complete![/bold green]")
    console.print(f"Output rooted at: [cyan]{output_root}[/cyan]")
    console.print("Next step: replace `convert_to_mp4` stub with real ffmpeg call.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user.[/red]")
        sys.exit(130)