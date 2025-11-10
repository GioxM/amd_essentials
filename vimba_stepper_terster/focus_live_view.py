#!/usr/bin/env python3
"""
focus_live_view.py — FINAL: GUI on main thread, no crashes
f = focus out   b = focus in   r = reset to zero   q = quit
"""

import sys
import time
import cv2
import numpy as np

# --------------------------------------------------------------------- #
# Vimba import
# --------------------------------------------------------------------- #
try:
    from vmbpy import VmbSystem, Camera, Stream, Frame
    VIMBA_MODULE = "vmbpy"
    print("[DEBUG] Using vmbpy")
except ImportError:
    try:
        from vimba import Vimba
        VIMBA_MODULE = "vimba"
        print("[DEBUG] Using classic vimba")
    except ImportError:
        print("[ERROR] Install the Vimba SDK Python bindings.")
        sys.exit(1)

# --------------------------------------------------------------------- #
# Stepper constants
# --------------------------------------------------------------------- #
STEP_SIZE   = 200
INTER_DELAY = 0.5
CALIB_SPEED = 150
XACTUAL     = "0500A10000000051"
STOP        = "0500AD0000000007"

# --------------------------------------------------------------------- #
# Stepper controller
# --------------------------------------------------------------------- #
class LiveFocusController:
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

    def send(self, cmd_hex: str):
        tx = self._feat("SerialTxData")
        if not tx: return None
        try:
            data = bytes.fromhex(cmd_hex)
            tx.set(data)
            time.sleep(INTER_DELAY)
            return self._read_reply()
        except: return None

    def _read_reply(self):
        rx = self._feat("SerialRxData")
        if not rx: return None
        try: return rx.get()
        except: return None

    def read_pos(self) -> int:
        self.send(XACTUAL)
        rep = self._read_reply()
        if rep and len(rep) >= 8:
            return int.from_bytes(rep[3:7], "big", signed=True)
        return 0

    def move(self, steps: int):
        cmd = "0500ADFFFE795F29" if steps < 0 else "0500AD000186A0F7"
        self.send(cmd)
        dir_name = "FOCUS OUT" if steps < 0 else "FOCUS IN"
        print(f"   → {dir_name} {abs(steps)} steps")

    def reset_to_zero(self):
        print("[RESET] Starting…")
        self.send("0500B000000000B0")
        self.send("0500B10096009600")
        self.send("0500B200000000B2")
        self.send(f"0500A400{CALIB_SPEED:08X}{self._checksum(CALIB_SPEED)}")
        self.send("0500A50000000064{self._checksum(100)}")
        self.send(STOP)
        self.send("0500ADFFFE795F29")
        while not self._stall():
            time.sleep(0.05)
        self.send(STOP)
        self.send("0500A10000000051")
        time.sleep(0.5)
        self.send("0500A4000003E82A")
        self.send("0500A50000C350D1")
        print(f"[RESET] ZERO: {self.read_pos()}")

    def _stall(self) -> bool:
        self.send("05006B000000006B")
        rep = self._read_reply()
        return rep and rep[3] > 0

    @staticmethod
    def _checksum(v: int) -> str:
        s = 5 + (v >> 24) + ((v >> 16) & 0xFF) + ((v >> 8) & 0xFF) + (v & 0xFF)
        return f"{s & 0xFF:02X}"

    def start_stream(self):
        if VIMBA_MODULE == "vmbpy":
            self.cam.start_streaming(handler=self._frame_handler_vmbpy)
        else:
            self.cam.start_streaming(handler=self._frame_handler_vimba)

    def stop_stream(self):
        if self.cam.is_streaming():
            self.cam.stop_streaming()

    def _frame_handler_vmbpy(self, cam: Camera, stream: Stream, frame: Frame):
        try:
            img = frame.as_opencv_image().copy()
            if frame.get_pixel_format().is_bayer():
                img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)
            pos = self.read_pos()
            cv2.putText(img, f"POS: {pos:+}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Live Focus", img)
            cv2.waitKey(1)
        except Exception as e:
            pass  # ignore frame errors

    def _frame_handler_vimba(self, cam, frame):
        try:
            img = frame.as_opencv_image().copy()
            pos = self.read_pos()
            cv2.putText(img, f"POS: {pos:+}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Live Focus", img)
            cv2.waitKey(1)
        except Exception:
            pass

# --------------------------------------------------------------------- #
# Main — GUI on main thread
# --------------------------------------------------------------------- #
def main():
    print("Live Camera + Focus Control")
    print("f = focus out   b = focus in   r = reset to zero   q = quit")

    cv2.namedWindow("Live Focus", cv2.WINDOW_NORMAL)

    if VIMBA_MODULE == "vmbpy":
        with VmbSystem.get_instance() as sys:
            cams = sys.get_all_cameras()
            if not cams:
                print("No camera.")
                return
            with cams[0] as cam:
                ctrl = LiveFocusController(cam)
                ctrl.start_stream()
                print("\nWindow open – use keys:")
                while True:
                    k = input("> ").strip().lower()
                    if k == "q":
                        break
                    if k == "f":
                        ctrl.move(-STEP_SIZE)
                    if k == "b":
                        ctrl.move(STEP_SIZE)
                    if k == "r":
                        ctrl.reset_to_zero()
                ctrl.stop_stream()
    else:
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            if not cams:
                print("No camera.")
                return
            with cams[0] as cam:
                ctrl = LiveFocusController(cam)
                ctrl.start_stream()
                print("\nWindow open – use keys:")
                while True:
                    k = input("> ").strip().lower()
                    if k == "q":
                        break
                    if k == "f":
                        ctrl.move(-STEP_SIZE)
                    if k == "b":
                        ctrl.move(STEP_SIZE)
                    if k == "r":
                        ctrl.reset_to_zero()
                ctrl.stop_stream()

    cv2.destroyAllWindows()
    print("Done.")

if __name__ == "__main__":
    main()