#!/usr/bin/env python3
"""
vimba_stepper_controller.py — Your Working Version + Limit Detection
Fallbacks to classic vimba if vmbpy not found.
"""

import argparse
import datetime
import sys
import time
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------- #
# Import with fallback (classic vimba or modern vmbpy)
# --------------------------------------------------------------------- #
VIMBA_MODULE = None
try:
    from vmbpy import VmbSystem, Camera as VmbCamera, VmbFeatureError
    VIMBA_MODULE = 'vmbpy'
    print("[DEBUG] Using vmbpy (Vimba X API)")
except ImportError:
    try:
        from vimba import Vimba, Camera as VimbaCamera
        VIMBA_MODULE = 'vimba'
        print("[DEBUG] Using vimba (classic API)")
    except ImportError:
        print("[ERROR] Neither vmbpy nor vimba found. Install Vimba SDK + Python API.")
        print("   Download: https://www.alliedvision.com/en/products/software/vimba-x-sdk/")
        print("   Or classic: https://www.alliedvision.com/en/products/vimba-sdk/")
        sys.exit(1)

# --------------------------------------------------------------------- #
# Optional rich (colors only)
# --------------------------------------------------------------------- #
try:
    from rich.console import Console
    console = Console()
    RICH = True
except ImportError:
    console = None
    RICH = False

import logging

# --------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------- #
SCRIPT_VERSION = "1.0"
HEX_COMMANDS = {
    "init": [
        "050080000000066E",
        "0500EC000100C318",
        "05009000061405FA",
        "0500910000000A70",
        "050093000003E887",
        "0500F0000401C897",
        "0500A4000003E82A",
        "0500A50000C350D1",
        "0500A60000C3508E",
        "0500A70000C35019",
        "0500A80000C35010",
        "0500AA0000C350D8",
        "0500AB0000000AE6",
        "0500B40000000F65",
        "0500A000000000C6",
    ],
    "forward": "0500AD000186A0F7",
    "backward": "0500ADFFFE795F29",
    "reset": [
        "0500AD0000000007",
        "0500A10000000051"
    ]
}
INTER_COMMAND_DELAY = 0.2  # Slower for visibility
SUMMARY_CSV = "logs/session_summary.csv"

# StallGuard / limit detection
STALLGUARD_THRESHOLD = 50
CALIBRATION_SPEED = 200
CALIBRATION_ACCEL = 100
XACTUAL_REGISTER = "0500A10000000051"

# --------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------- #
def setup_logging(auto: bool = False, debug: bool = False):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs") / ts
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "session.log"

    logger = logging.getLogger("stepper")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    return logger, log_dir

# --------------------------------------------------------------------- #
# UI helpers
# --------------------------------------------------------------------- #
def print_banner():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"""
──────────────────────────────────────────────────────────
 CAMERA + STEPPER MOTOR CONTROL INTERFACE
 Version {SCRIPT_VERSION} | Date: {now}
──────────────────────────────────────────────────────────
""")

def log_info(msg, logger):    print(f"[INFO] {msg}"); logger.info(msg)
def log_ok(msg, logger):      line = f"[OK] {msg}"; print(line) if not RICH else console.print(f"[green]{line}[/]"); logger.info(msg)
def log_motor(msg, logger):   line = f"[MOTOR] {msg}"; print(line) if not RICH else console.print(f"[bold blue]{line}[/]"); logger.info(msg)
def log_warn(msg, logger):    line = f"[WARN] {msg}"; print(line) if not RICH else console.print(f"[bold yellow]{line}[/]"); logger.warning(msg)
def log_error(msg, logger):   line = f"[ERROR] {msg}"; print(line) if not RICH else console.print(f"[bold red]{line}[/]"); logger.error(msg)
def log_debug(msg, logger, debug):
    if debug:
        print(f"[DEBUG] {msg}")
        logger.debug(msg)

# --------------------------------------------------------------------- #
# Hex validation
# --------------------------------------------------------------------- #
def validate_hex(cmd: str) -> Optional[bytes]:
    try:
        data = bytes.fromhex(cmd)
        return data if len(data) == 8 else None
    except Exception:
        return None

def validate_all(logger):
    for key, cmds in HEX_COMMANDS.items():
        if isinstance(cmds, list):
            for c in cmds:
                if not validate_hex(c):
                    log_error(f"Invalid hex in {key}: {c}", logger)
                    sys.exit(1)
        else:
            if not validate_hex(cmds):
                log_error(f"Invalid hex in {key}: {cmds}", logger)
                sys.exit(1)

# --------------------------------------------------------------------- #
# Camera wrapper (handles both APIs)
# --------------------------------------------------------------------- #
class StepperCamera:
    def __init__(self, cam, logger, debug: bool = False):
        self.cam = cam
        self.logger = logger
        self.debug = debug
        self.hub_enabled = False
        self.dio_feature = None
        self.min_pos = None
        self.max_pos = None
        self._find_dio()

    # ---- feature helpers (API-agnostic) ----
    def _feat(self, name: str):
        try:
            if VIMBA_MODULE == 'vmbpy':
                return self.cam.get_feature_by_name(name)
            else:  # classic vimba
                return self.cam.get_feature_by_name(name)
        except (VmbFeatureError, Exception):
            log_debug(f"Feature {name} not found", self.logger, self.debug)
            return None

    def _set(self, name: str, value):
        f = self._feat(name)
        if not f:
            log_warn(f"Feature {name} missing", self.logger)
            return False
        try:
            f.set(value)
            log_debug(f"Set {name} = {value}", self.logger, self.debug)
            return True
        except Exception as e:
            log_error(f"Failed to set {name}: {e}", self.logger)
            return False

    # ---- opto sensor ----
    def _find_dio(self):
        for n in ["DigitalIOInput", "DigitalIO", "Line0", "GpioInput"]:
            if self._feat(n):
                self.dio_feature = self._feat(n)
                log_info(f"Opto sensor on feature: {n}", self.logger)
                return
        log_info("No opto sensor – safety check disabled", self.logger)

    def sensor_blocked(self) -> bool:
        if not self.dio_feature:
            return False
        try:
            state = self.dio_feature.get()
            blocked = bool(state)
            log_debug(f"Sensor: {state} → blocked={blocked}", self.logger, self.debug)
            return blocked
        except Exception as e:
            log_warn(f"Read sensor failed: {e}", self.logger)
            return False

    # ---- serial hub ----
    def enable_hub(self):
        if self._set("SerialHubEnable", True):
            self.hub_enabled = True
            self._set("SerialTxSize", 128)

    def send(self, hex_cmd: str) -> Optional[bytes]:
        if not self.hub_enabled:
            log_error("Serial Hub not enabled", self.logger)
            return None
        data = validate_hex(hex_cmd)
        if not data:
            log_error(f"Invalid command: {hex_cmd}", self.logger)
            return None
        tx = self._feat("SerialTxData")
        if not tx:
            log_error("SerialTxData missing", self.logger)
            return None
        try:
            tx.set(data)
            log_motor(f"Sending: {hex_cmd}", self.logger)
            time.sleep(INTER_COMMAND_DELAY)
            return self._read_reply()
        except Exception as e:
            log_error(f"Send failed: {e}", self.logger)
            return None

    def _read_reply(self) -> Optional[bytes]:
        rx = self._feat("SerialRxData")
        if not rx: return None
        try:
            rep = rx.get()
            if rep:
                h = rep.hex().upper()
                log_motor(f"Reply: {h}", self.logger)
                return rep
        except Exception as e:
            log_debug(f"RX failed: {e}", self.logger, self.debug)
        return None

    # ---- position read ----
    def read_position(self) -> Optional[int]:
        self.send(XACTUAL_REGISTER)
        reply = self._read_reply()
        if reply and len(reply) >= 8:
            val = int.from_bytes(reply[3:7], 'big', signed=True)
            return val
        return None

    # ---- limit detection ----
    def detect_limits(self, speed: int = CALIBRATION_SPEED):
        log_info("=== CALIBRATING FOCUS LIMITS ===", self.logger)

        # Enable stallGuard2
        self.send("0500B000000000B0")
        self.send(f"0500B100{STALLGUARD_THRESHOLD:02X}00{STALLGUARD_THRESHOLD:02X}00")
        self.send("0500B200000000B2")

        # Set safe speed/accel
        self.send(f"0500A400{speed:08X}{self._checksum(speed)}")
        self.send(f"0500A500{CALIBRATION_ACCEL:08X}{self._checksum(CALIBRATION_ACCEL)}")

        # Find MIN
        self.send("0500AD0000000007")
        self.send("0500ADFFFE795F29")
        log_motor("Moving to MIN limit...", self.logger)
        while True:
            if self._stall_detected():
                self.send("0500AD0000000007")
                break
            time.sleep(0.05)
        min_pos = self.read_position() or 0
        log_ok(f"MIN limit found at {min_pos}", self.logger)

        # Find MAX
        self.send("0500AD0000000007")
        self.send("0500AD000186A0F7")
        log_motor("Moving to MAX limit...", self.logger)
        while True:
            if self._stall_detected():
                self.send("0500AD0000000007")
                break
            time.sleep(0.05)
        max_pos = self.read_position() or 0
        log_ok(f"MAX limit found at {max_pos}", self.logger)

        # Store
        self.min_pos, self.max_pos = min(min_pos, max_pos), max(min_pos, max_pos)
        log_info(f"Safe travel range: {self.min_pos} .. {self.max_pos}", self.logger)

        # Restore normal speed
        self.send("0500A4000003E82A")
        self.send("0500A50000C350D1")

    def _stall_detected(self) -> bool:
        self.send("05006B000000006B")
        reply = self._read_reply()
        if reply and len(reply) >= 8:
            return reply[3] > 0
        return False

    @staticmethod
    def _checksum(value: int) -> str:
        return f"{(0x05 + (value >> 24) + ((value >> 16) & 0xFF) + ((value >> 8) & 0xFF) + (value & 0xFF)) & 0xFF:02X}"

    # ---- safe move ----
    def safe_move(self, steps: int) -> bool:
        if self.min_pos is None or self.max_pos is None:
            log_warn("Limits not calibrated – allowing move", self.logger)
        else:
            current = self.read_position() or 0
            target = current + steps
            if not (self.min_pos <= target <= self.max_pos):
                log_warn(f"Target {target} outside safe range [{self.min_pos}, {self.max_pos}] – blocked", self.logger)
                return False
        cmd = HEX_COMMANDS["forward"] if steps > 0 else HEX_COMMANDS["backward"]
        self.send(cmd)
        return True

    # ---- metadata ----
    def metadata(self):
        if VIMBA_MODULE == 'vmbpy':
            model = getattr(self.cam, "get_name", lambda: "Unknown")()
        else:
            model = self.cam.get_model() or "Unknown"
        sid = self.cam.get_id() if hasattr(self.cam, 'get_id') else self.cam.get_serial()
        log_ok(f"Camera connected: {model} (ID {sid})", self.logger)

# --------------------------------------------------------------------- #
# Test sequences
# --------------------------------------------------------------------- #
def run_reset(sc: StepperCamera):
    log_motor("Resetting motor...", sc.logger)
    for cmd in HEX_COMMANDS["reset"]:
        sc.send(cmd)
    log_ok("Position reset (0)", sc.logger)

def run_init(sc: StepperCamera):
    log_info("Initializing motor...", sc.logger)
    for cmd in HEX_COMMANDS["init"]:
        sc.send(cmd)

def run_move(sc: StepperCamera, direction: str) -> bool:
    if sc.sensor_blocked():
        log_warn("OPTO SENSOR BLOCKED – MOVEMENT ABORTED", sc.logger)
        return False

    steps = 100000 if direction == "forward" else -100000
    if not sc.safe_move(steps):
        return False
    log_motor(f"Moving {direction} {abs(steps)} steps...", sc.logger)
    time.sleep(1.0)
    current = sc.read_position() or 0
    log_ok(f"Motor position: {current:+}", sc.logger)
    return True

# --------------------------------------------------------------------- #
# Interactive menu
# --------------------------------------------------------------------- #
def interactive(sc: StepperCamera, log_dir: Path, args):
    while True:
        print("Select test mode:")
        print("[1] Full Test")
        print("[2] Forward Only")
        print("[3] Backward Only")
        print("[4] Reset")
        print("[Q] Quit")
        choice = input("> ").strip().lower()

        if choice == "q":
            break

        start = time.time()
        success = True
        test_type = ""

        try:
            if choice == "1":
                test_type = "full"
                run_init(sc)
                if not run_move(sc, "forward"):
                    success = False
                run_reset(sc)
                log_motor("Returning...", sc.logger)
                if not run_move(sc, "backward"):
                    success = False
                run_reset(sc)

            elif choice == "2":
                test_type = "forward"
                run_init(sc)
                success = run_move(sc, "forward")
                run_reset(sc)

            elif choice == "3":
                test_type = "backward"
                run_init(sc)
                success = run_move(sc, "backward")
                run_reset(sc)

            elif choice == "4":
                test_type = "reset"
                run_reset(sc)

            else:
                print("Invalid choice.")
                continue

        except KeyboardInterrupt:
            log_info("Interrupted.", sc.logger)
            break

        duration = time.time() - start
        log_info(f"Test complete. Logs saved to {log_dir}/session.log", sc.logger)

        notes_input = input("Please enter your notes or observations:\n> ").strip()
        notes = notes_input if notes_input else "(none)"
        if notes_input:
            sc.logger.info(f"Notes: {notes_input}")

        csv_line = f"{datetime.datetime.now().isoformat()},{test_type},{success},{notes},{duration:.2f}\n"
        Path(SUMMARY_CSV).parent.mkdir(parents=True, exist_ok=True)
        with open(SUMMARY_CSV, "a", encoding="utf-8") as f:
            f.write(csv_line)

        log_ok("Note saved. Session archived.", sc.logger)

    print("System shutdown complete.")

# --------------------------------------------------------------------- #
# Auto mode
# --------------------------------------------------------------------- #
def auto_run(sc: StepperCamera, log_dir: Path):
    log_info("AUTO MODE: Running full test", sc.logger)
    start = time.time()
    run_init(sc)
    run_move(sc, "forward")
    run_reset(sc)
    log_motor("Returning...", sc.logger)
    run_move(sc, "backward")
    run_reset(sc)
    duration = time.time() - start
    log_info(f"Test complete. Logs saved to {log_dir}/session.log", sc.logger)
    notes = "Auto-run"
    csv_line = f"{datetime.datetime.now().isoformat()},full,True,{notes},{duration:.2f}\n"
    Path(SUMMARY_CSV).parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_CSV, "a", encoding="utf-8") as f:
        f.write(csv_line)
    log_ok("Note saved. Session archived.", sc.logger)

# --------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--calibrate", action="store_true", help="Run limit calibration on start-up")
    parser.add_argument("--slow", type=int, default=CALIBRATION_SPEED, help=f"Calibration speed in steps/s (default: {CALIBRATION_SPEED})")
    args = parser.parse_args()

    logger, log_dir = setup_logging(auto=args.auto, debug=args.debug)
    print_banner()
    validate_all(logger)

    log_info("Initializing system...", logger)

    if VIMBA_MODULE == 'vmbpy':
        with VmbSystem.get_instance() as system:
            log_debug("VmbSystem context entered", logger, args.debug)
            cams = system.get_all_cameras()
            if not cams:
                log_error("No cameras detected.", logger)
                log_info("Check: USB cable, power, open Vimba Viewer first?", logger)
                return
            for c in cams:
                log_debug(f"Found: {c.get_name()} | ID: {c.get_id()}", logger, args.debug)
            cam = cams[0]
            with cam:
                sc = StepperCamera(cam, logger, debug=args.debug)
                sc.metadata()
                sc.enable_hub()
                if args.calibrate:
                    sc.detect_limits(speed=args.slow)
                log_info("System ready.", logger)
                if args.auto:
                    auto_run(sc, log_dir)
                else:
                    interactive(sc, log_dir, args)
    else:  # classic vimba
        with Vimba.get_instance() as vimba:
            log_debug("Vimba context entered", logger, args.debug)
            cams = vimba.get_all_cameras()
            if not cams:
                log_error("No cameras detected.", logger)
                log_info("Check: USB cable, power, open Vimba Viewer first?", logger)
                return
            for c in cams:
                log_debug(f"Found: {c.get_id()}", logger, args.debug)
            cam = cams[0]
            with cam:
                sc = StepperCamera(cam, logger, debug=args.debug)
                sc.metadata()
                sc.enable_hub()
                if args.calibrate:
                    sc.detect_limits(speed=args.slow)
                log_info("System ready.", logger)
                if args.auto:
                    auto_run(sc, log_dir)
                else:
                    interactive(sc, log_dir, args)

    log_info("System shutdown complete.", logger)

if __name__ == "__main__":
    main()