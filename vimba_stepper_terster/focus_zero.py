#!/usr/bin/env python3
"""
focus_zero.py — With 'r' = Reset to Mechanical Zero
f = focus out, b = focus in, r = reset to zero, q = quit
"""

import sys
import time

# --------------------------------------------------------------------- #
# Import with fallback
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
# Constants
# --------------------------------------------------------------------- #
STEP_SIZE = 200
INTER_DELAY = 0.5
CALIB_SPEED = 150
XACTUAL = "0500A10000000051"
STOP = "0500AD0000000007"

# --------------------------------------------------------------------- #
# Controller
# --------------------------------------------------------------------- #
class FocusController:
    def __init__(self, cam):
        self.cam = cam
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
            time.sleep(INTER_DELAY)
            return self._read_reply()
        except: return None

    def _read_reply(self):
        rx = self._feat("SerialRxData")
        if not rx: return None
        try:
            rep = rx.get()
            return rep if rep else None
        except: return None

    def read_pos(self):
        self.send(XACTUAL)
        rep = self._read_reply()
        if rep and len(rep) >= 8:
            val = int.from_bytes(rep[3:7], 'big', signed=True)
            return val
        return None

    def move(self, steps):
        # forward = negative (focus out), backward = positive (focus in)
        cmd = "0500ADFFFE795F29" if steps < 0 else "0500AD000186A0F7"
        self.send(cmd)
        dir_name = "FOCUS OUT" if steps < 0 else "FOCUS IN"
        print(f"   → {dir_name} {abs(steps)} steps")

    def reset_to_zero(self):
        print("\n[RESET TO ZERO] Starting...")
        print("  [1] stallGuard ON")
        self.send("0500B000000000B0")
        self.send("0500B10032003200")
        self.send("0500B200000000B2")

        print("  [2] Slow speed")
        self.send(f"0500A400{CALIB_SPEED:08X}{self._checksum(CALIB_SPEED)}")
        self.send("0500A50000000064{self._checksum(100)}")

        print("  [3] Move to MIN (mechanical stop)")
        self.send(STOP)
        self.send("0500ADFFFE795F29")  # negative = move to MIN
        print("    Moving...", end="")
        while not self._stall():
            print(".", end="", flush=True)
            time.sleep(0.1)
        self.send(STOP)
        print("\n    STOPPED at mechanical end")
        min_pos = self.read_pos()
        print(f"    Raw position: {min_pos}")

        print("  [4] Set ZERO")
        self.send("0500A10000000051")
        time.sleep(0.5)
        zero = self.read_pos()
        print(f"    ZERO SET: {zero}")

        print("  [5] Restore normal speed")
        self.send("0500A4000003E82A")
        self.send("0500A50000C350D1")

        print("[RESET COMPLETE] Lens at mechanical zero.\n")

    def _stall(self):
        self.send("05006B000000006B")
        rep = self._read_reply()
        return rep and rep[3] > 0

    @staticmethod
    def _checksum(v):
        s = 5 + (v>>24) + ((v>>16)&255) + ((v>>8)&255) + (v&255)
        return f"{s & 255:02X}"

# --------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------- #
def main():
    print("Focus Zero + Live Control")
    if VIMBA_MODULE == 'vmbpy':
        with VmbSystem.get_instance() as sys:
            cams = sys.get_all_cameras()
            if not cams:
                print("No camera.")
                return
            with cams[0] as cam:
                ctrl = FocusController(cam)
                print("\nLIVE CONTROL:")
                print("  f = focus out")
                print("  b = focus in")
                print("  r = reset to mechanical zero")
                print("  q = quit\n")
                while True:
                    k = input("> ").strip().lower()
                    if k == 'q': break
                    if k == 'f': ctrl.move(-STEP_SIZE)
                    if k == 'b': ctrl.move(STEP_SIZE)
                    if k == 'r': ctrl.reset_to_zero()
                    pos = ctrl.read_pos()
                    print(f"   POS: {pos:+}" if pos is not None else "   POS: ?")
    else:
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            if not cams:
                print("No camera.")
                return
            with cams[0] as cam:
                ctrl = FocusController(cam)
                print("\nLIVE CONTROL:")
                print("  f = focus out")
                print("  b = focus in")
                print("  r = reset to mechanical zero")
                print("  q = quit\n")
                while True:
                    k = input("> ").strip().lower()
                    if k == 'q': break
                    if k == 'f': ctrl.move(-STEP_SIZE)
                    if k == 'b': ctrl.move(STEP_SIZE)
                    if k == 'r': ctrl.reset_to_zero()
                    pos = ctrl.read_pos()
                    print(f"   POS: {pos:+}" if pos is not None else "   POS: ?")
    print("Done.")

if __name__ == "__main__":
    main()