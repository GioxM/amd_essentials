#!/usr/bin/env python3
"""
Title: .homohs (AVI/HuffYUV) to MP4 Converter
Author: G.M
Date: 09 Nov 2025
Version: 1.0

Description:
Production converter for .homohs files (AVI with HuffYUV lossless video).
- Detects/probes with ffprobe.
- Converts to MP4 (H.264/AAC) with Apple VideoToolbox accel.
- Strict output hierarchy: date/time/clip_title/*.mp4 + .log
- Interactive: all/single file.
- --debug: verbose logs + JSON dumps.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn

console = Console()

# Case-insensitive extensions (added .homohs)
VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg",
    ".ts", ".m2ts", ".vob", ".ogv", ".3gp", ".3g2", ".homohs", ".HOMOH S",
    # Uppercase variants for safety
    ".MP4", ".MKV", ".AVI", ".MOV", ".WMV", ".FLV", ".WEBM", ".M4V", ".MPG", ".MPEG",
    ".TS", ".M2TS", ".VOB", ".OGV", ".3GP", ".3G2", ".HOMOH S",
}

def run_cmd(cmd: List[str], capture: bool = True, check: bool = True) -> Optional[str]:
    """Run subprocess, return stdout if capture, else print live."""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.stdout + result.stderr
        else:
            subprocess.run(cmd, check=check)
            return None
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Cmd failed: {' '.join(cmd)}[/red]\n{e.stderr}")
        return e.stderr

def probe_file(file_path: Path, debug: bool = False) -> Optional[Dict[str, Any]]:
    cmd = ["ffprobe", "-v", "quiet" if not debug else "debug", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    try:
        result = run_cmd(cmd, capture=True, check=True)
        data = json.loads(result)
        if debug:
            dump_path = file_path.with_suffix(".probe.json")
            with open(dump_path, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"[dim]Dumped probe JSON: {dump_path}[/dim]")
        return data
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
        console.print(f"[yellow]Probe failed on {file_path}: {e}[/yellow]")
        return None

def extract_info(probe_data: Dict[str, Any], file_path: Path) -> Dict[str, str]:
    fmt = probe_data.get("format", {})
    streams = probe_data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "file": file_path.name,
        "container": fmt.get("format_name", "unknown").upper(),
        "duration": fmt.get("duration", "N/A"),
        "size_mb": f"{int(fmt.get('size', 0)) / (1024*1024):.1f} MB",
        "v_codec": video.get("codec_name", "N/A").upper() if video else "N/A",
        "v_res": f"{video.get('width', '?')}x{video.get('height', '?')}" if video else "N/A",
        "v_fps": f"{video.get('r_frame_rate', '?')}" if video else "N/A",
        "a_codec": audio.get("codec_name", "N/A").upper() if audio else "NONE",
    }

def find_videos(root: Path) -> List[Path]:
    if root.is_file() and root.suffix.lower() in {e.lower() for e in VIDEO_EXTS}:
        return [root]
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {e.lower() for e in VIDEO_EXTS}]

def detect_videos(paths: List[Path], debug: bool = False) -> List[Dict[str, Any]]:
    results = []
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%", TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Probing .homohs files...", total=len(paths))
        for p in paths:
            progress.update(task, description=f"Probing {p.name}")
            data = probe_file(p, debug)
            if data:
                info = extract_info(data, p)
                info["path"] = p
                results.append(info)
            progress.advance(task)
    return results

def interactive_menu(videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not videos:
        console.print("[bold red]No valid .homohs/AVI files detected.[/bold red]")
        sys.exit(1)

    table = Table(title="Detected .homohs Files (HuffYUV AVI)")
    for key in ["file", "container", "v_codec", "v_res", "v_fps", "duration", "size_mb"]:
        table.add_column(key.replace("_", " ").title(), justify="left", style="cyan")

    for idx, v in enumerate(videos, 1):
        table.add_row(
            f"[bold]{idx}[/bold] {v['file']}",
            v["container"],
            v["v_codec"],
            v["v_res"],
            v["v_fps"],
            f"{float(v['duration']):.1f}s" if v['duration'] != "N/A" else "N/A",
            v["size_mb"],
        )
    console.print(table)

    choice = Prompt.ask(
        "\n[bold]Options[/bold]:\n[green]a[/green] – Convert **ALL**\n[yellow]number[/yellow] – Single\n[red]q[/red] – Quit",
        choices=["a"] + [str(i) for i in range(1, len(videos)+1)] + ["q"],
        default="a",
    )

    if choice == "q":
        sys.exit(0)
    elif choice == "a":
        if Confirm.ask("Convert ALL? (High-res = big files!)"):
            return videos
    else:
        return [videos[int(choice)-1]]
    return interactive_menu(videos)  # Retry on no

def build_output_structure(base_output: Path, clip_title: str) -> Path:
    now = datetime.now()
    date_folder = now.strftime("%d%b%Y")  # 09Nov2025
    time_folder = now.strftime("%Hh%Mm%Ss")  # 14h30m22s
    clip_folder = base_output / date_folder / time_folder / clip_title
    clip_folder.mkdir(parents=True, exist_ok=True)
    return clip_folder

def md5_checksum(file_path: Path) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def convert_to_mp4(input_path: Path, output_dir: Path, debug: bool = False) -> bool:
    output_file = output_dir / f"{input_path.stem}.mp4"
    log_file = output_dir / "conversion.log"

    # FFmpeg cmd: HuffYUV decode → H.264 encode (VideoToolbox for M1/M2 accel), AAC audio
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-c:v", "h264_videotoolbox",  # Apple hardware accel
        "-preset", "medium",
        "-crf", "18",  # Near-lossless (lower = better, but bigger files)
        "-c:a", "aac",
        "-b:a", "192k",  # If audio added later
        "-pix_fmt", "yuv420p",  # Standard for MP4 compatibility
        "-movflags", "+faststart",  # Web-optimized
        "-y",  # Overwrite
        str(output_file),
    ]
    if debug:
        cmd[1:3] = ["-loglevel", "debug"]  # Verbose

    console.print(f"[green]Converting: {input_path.name} → {output_file}[/green]")

    start_time = datetime.now().isoformat()
    logs = run_cmd(cmd, capture=debug, check=True)

    end_time = datetime.now().isoformat()
    input_md5 = md5_checksum(input_path)
    output_md5 = md5_checksum(output_file)

    with open(log_file, "w") as f:
        f.write(f"Start: {start_time}\n")
        f.write(f"Cmd: {' '.join(cmd)}\n")
        f.write("FFmpeg Logs:\n" + (logs or "No capture (live output)\n"))
        f.write(f"End: {end_time}\n")
        f.write(f"Status: SUCCESS\n")
        f.write(f"Input MD5: {input_md5}\n")
        f.write(f"Output MD5: {output_md5}\n")
        f.write(f"Output Size: {output_file.stat().st_size / (1024*1024):.1f} MB\n")

    console.print(f"[bold green]Done! Log: {log_file}[/bold green]")
    return True

# Args
parser = argparse.ArgumentParser(description="Convert .homohs to MP4")
parser.add_argument("path", type=str, help="File/dir to scan")
parser.add_argument("-o", "--output", type=str, default="converted_videos", help="Output root")
parser.add_argument("--debug", action="store_true", help="Verbose + dumps")
args = parser.parse_args()

def main():
    input_path = Path(args.path).expanduser().resolve()
    if not input_path.exists():
        console.print(f"[red]Path missing: {input_path}[/red]")
        sys.exit(1)

    console.print(Panel("[bold magenta].homohs to MP4 Converter v1.0[/bold magenta]\n[dim]Author: G.M | 09 Nov 2025 | HuffYUV → H.264[/dim]"))

    candidates = find_videos(input_path)
    if not candidates:
        console.print("[yellow]No .homohs (or video) files found. Trying broader scan?[/yellow]")
        sys.exit(0)

    console.print(f"[green]Found {len(candidates)} candidate(s)[/green]")

    detected = detect_videos(candidates, args.debug)
    if not detected:
        console.print("[red]All probes failed — check FFmpeg.[/red]")
        sys.exit(1)

    to_convert = interactive_menu(detected)

    output_root = Path(args.output).expanduser().resolve()
    output_root.mkdir(exist_ok=True)

    success_count = 0
    for item in to_convert:
        src = item["path"]
        title = src.stem.replace("_", " ")[:50]  # Clean title
        out_dir = build_output_structure(output_root, title)
        if convert_to_mp4(src, out_dir, args.debug):
            success_count += 1

    console.print(f"\n[bold green]{success_count}/{len(to_convert)} converted![/bold green]")
    console.print(f"Root: [cyan]{output_root}[/cyan]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted.[/red]")
        sys.exit(130)