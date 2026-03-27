#!/usr/bin/env python3
#
# demo_float_playingcard_3.py
#
# Scene-driven demo launcher for the floating playing card
#

import cv2
import argparse
import time

from asimov import scene, io, conf as asimov_conf
from asimov.common import ThreadSafeContext

# ------------------------------------------------------------
# Scene definition (from conf.SCENE)
# ------------------------------------------------------------

FLOATING_CARD_SCENE = asimov_conf.SCENE

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Floating playing card demo (scene-driven)"
    )
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    # --- camera ---
    cap = cv2.VideoCapture(args.device)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        io.echo("Failed to open camera", level="critical")
        return 1

    # --- shared context ---
    context = ThreadSafeContext()

    # --- activate scene ---
    scene.request(FLOATING_CARD_SCENE)

    ptime = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)

        # Apply pending scene switch if requested
        scene.apply_if_needed(args=args, context=context)

        # Run scene pipeline
        frame = scene.run(frame, args=args, context=context)

        # FPS (debug only)
        if args.debug:
            ctime = time.time()
            fps = 1.0 / max(ctime - ptime, 1e-6)
            ptime = ctime
            cv2.putText(
                frame,
                f"FPS: {int(fps)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

        cv2.imshow("Floating Card (Scene)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
