#!/usr/bin/env python3
"""
stallguard_test_FIXED.py — CORRECT REPLY + LOUD TEST
"""

import sys
import time

# --------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------- #
try:
    from vmbpy import VmbSystem, Camera
    VIMBA_MODULE = 'vmbpy'
except ImportError:
    try:
        from vimba import Vimba
        VIMBA_MODULE = 'vimba'
    except ImportError:
        print("Install Vimba SDK.")
        sys.exit(1)

# --------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------- #
TEST_SPEED = 50
TEST_ACCEL = 50
STALL_THRESHOLD = 150
MAX_STEPS = 200
STEP_DELAY = 0.02

XACTUAL = "0500A10000000051"
STOP = "0500AD0000000007"

# --------------------------------------------------------------------- #
# Controller
# --------------------------------------------------------------------- #
class LoudTester:
    def __init__(self, cam):
        self.cam = cam
        self.steps = 0
        self._enable_hub()

    def _feat(self, name):
        try: return self.cam.get_feature_by_name(name)
        except: return None

    def _set(self, name, val):
        f = self._feat(name)
        if f:
            try: f.set(val); return True
            except: pass
        return False

    def _enable_hub(self):
        self._set("SerialHubEnable", True)
        self._set("SerialTxSize", 128)

    def send(self, cmd):
        tx = self._feat("SerialTxData")
        if not tx: return None
        try:
            data = bytes.fromhex(cmd)
            tx.set(data)
            time.sleep(STEP_DELAY)
            return self._read_reply()
        except: return None

    def _read_reply(self):
        rx = self._feat("SerialRxData")  # ← FIXED: Rx, not Tx
        if not rx: return None
        try:
            rep = rx.get()
            if rep:
                # Debug: print raw reply
                print(f"   [RX] {rep.hex().upper()}")
                return rep
        except Exception as e:
            print(f"   [RX ERROR] {e}")
        return None

    def read_pos(self):
        self.send(XACTUAL)
        rep = self._read_reply()
        if rep and len(rep) >= 8:
            val = int.from_bytes(rep[3:7], 'big', signed=True)
            return val
        return None

    def _stall(self):
        self.send("05006B000000006B")
        rep = self._read_reply()
        return rep and rep[3] > 0

    @staticmethod
    def _checksum(v):
        s = 5 + (v>>24) + ((v>>16)&255) + ((v>>8)&255) + (v&255)
        return f"{s & 255:02X}"

    def run(self):
        print("\n=== LOUD STALLGUARD TEST ===")
        print("[1] Enable stallGuard")
        self.send("0500B000000000B0")
        self.send(f"0500B100{STALL_THRESHOLD:02X}00{STALL_THRESHOLD:02X}00")
        self.send("0500B200000000B2")

        print("[2] Slow speed")
        self.send(f"0500A400{TEST_SPEED:08X}{self._checksum(TEST_SPEED)}")
        self.send(f"0500A500{TEST_ACCEL:08X}{self._checksum(TEST_ACCEL)}")

        start = self.read_pos()
        print(f"[3] Start pos: {start}")

        print(f"[4] Moving FORWARD (max {MAX_STEPS} steps)...")
        self.send(STOP)
        self.send("0500AD000186A0F7")
        self.steps = 0
        while self.steps < MAX_STEPS and not self._stall():
            self.steps += 1
            print(f"   Step {self.steps} [CLICK]", end="\r")
            time.sleep(0.1)
        self.send(STOP)
        stall_pos = self.read_pos()
        print(f"\n   STALL at step {self.steps}, pos {stall_pos}")

        if self.steps == 0:
            print("   NO MOVEMENT — check power/wiring!")
            return

        print(f"[5] Moving BACK {self.steps} steps...")
        back_cmd = f"0500AD{(-self.steps):08X}{self._checksum(-self.steps)}"
        self.send(back_cmd)
        time.sleep(3.0)
        final = self.read_pos()
        print(f"   Back to: {final}")

        print("[6] Restore speed")
        self.send("0500A4000003E82A")
        self.send("0500A50000C350D1")

        error = abs(final - start)
        print(f"\n[RESULT] Moved {self.steps} steps out and back.")
        print(f"         Error: {error} steps")
        if error <= 5:
            print("         PASS: Motor works BOTH ways!")
        else:
            print("         FAIL: Check load or wiring.")

# --------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------- #
def main():
    print("Loud StallGuard Test")
    if VIMBA_MODULE == 'vmbpy':
        with VmbSystem.get_instance() as sys:
            cams = sys.get_all_cameras()
            if not cams:
                print("No camera.")
                return
            with cams[0] as cam:
                tester = LoudTester(cam)
                tester.run()
    else:
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            if not cams:
                print("No camera.")
                return
            with cams[0] as cam:
                tester = LoudTester(cam)
                tester.run()
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()