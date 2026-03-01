# import locale
import argparse
##from dataclasses import dataclass, field

from . import io

import cv2
import pyvirtualcam
##import numpy as np

##import mediapipe as mp

from .util import draw_text, get_device_by_label
from .base import conf, glitch, indexfingertip, eyes_next as eyes
from .common import camera_ready

# Constants
# MARGIN = 20  # pixels
# TITLE = "Project Asimov v202509.0"
# CAP_HEIGHT = 480
# CAP_WIDTH = 640
# CAP_FPS = 30

## moved to .conf
##FINGERTIP_COLOR = (0, 255, 255) # yellow BGR
##RECT_COLOR_TOUCHED = (0, 255, 0) # green

##from cvzone.HandTrackingModule import HandDetector

##index_finger_tip = None

# 1. detect fingertip
# 2. detect rectangles
# 3. detect fingertip touching rectangles (update border_color)
# 4. detect eyes
# 5. draw fingertip
# 6. draw rectangles
# 7. draw eyebars


def apply_title(frame, context):
    return draw_text(
        frame,
        10,
        15,
        conf.TITLE,
        color=conf.WATERMARK_COLOR,
        font_scale=0.50,
        alpha=0.75,
        shadow_alpha=0.75,
        shadow_offset=2,
    )


def apply_glitches(frame, context):
    glitch.scheduler()
    return glitch.apply(frame)


OVERLAYS = [
    {
        "key": "f",
        "enabled": True,
        "running": True,
        "label": "fingertip",
        "func": lambda frame, context: indexfingertip.draw(frame, context),
    },
    #            { "key": "r", "enabled":True, "running":True,  "label": "rects",      "func": lambda frame, context: rect.draw(frame, context)},
    #            { "key": "p", "enabled":True, "running":True,  "label": "playingcards",      "func": lambda frame, context: playingcard.draw(frame, context)},
    {
        "key": "e",
        "enabled": True,
        "running": True,
        "label": "eyes",
        "func": eyes.draw,
    },  # lambda frame, context: eyes.draw(frame, context)},
    #            { "key": "w", "enabled":True, "running":True,  "label": "watermark", "func": lambda frame, context: watermark.draw(frame, context)},
    {
        "key": "t",
        "enabled": True,
        "running": False,
        "label": "title",
        "func": lambda frame, context: apply_title(frame, context),
    },
    {
        "key": "g",
        "enabled": True,
        "running": False,
        "label": "glitches",
        "func": lambda frame, context: apply_glitches(frame, context),
    },
]


def apply_overlays(frame, context):
    global OVERLAYS

    for o in OVERLAYS:
        if not o["enabled"]:
            continue
        if not o["running"]:
            continue
        f = o.get("func", None)
        if callable(f):
            frame = f(frame, context)
    return frame


def main(args, **kwargs):
    global OVERLAYS

    # Open the real webcam
    cap = cv2.VideoCapture(conf.CAP_DEVICE, cv2.CAP_V4L2)

    try:
        if camera_ready(cap) is False:
            raise RuntimeError("Camera is not ready after 5s")

        for name in glitch.GLITCH_LIST:
            kwargs = glitch.GLITCH_CONFIG.get(name, {})
            glitch.register(name, **kwargs)

        # Make sure the webcam opens correctly
        if not cap.isOpened():
            raise RuntimeError("Could not open webcam. check group membership.")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.CAP_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.CAP_HEIGHT)
        if cap.set(cv2.CAP_PROP_FPS, conf.CAP_FPS) is False:
            io.echo(f"could not set FPS to {conf.FPS}")

        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)

        # Get the frame size
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame from camera")

        # get virtual camera device by label
        device = get_device_by_label(conf.VIRTCAM_LABEL)

        context = {}
        ##        io.echo(f"{{labelcolor}}virtualcam label {{valuecolor}}{conf.CAM_LABEL} {{labelcolor}}, device {{valuecolor}}{device}{{/all}}")
        ##        playingcard.init(args.basedir, args.set_name, context)
        # Start the virtual camera
        device = get_device_by_label(conf.VIRTCAM_LABEL)
        io.echo(f"----> virtual camera device: {device}")
        with pyvirtualcam.Camera(
            width=actual_width,
            height=actual_height,
            fps=actual_fps,
            print_fps=True,
            device=device,
        ) as cam:
            io.echo(
                f"{{labelcolor}}Capture: {{valuecolor}}{conf.CAP_DEVICE}, virtcam: ({cam.device}) {actual_width}{{labelcolor}}x{{valuecolor}}{actual_height} {{labelcolor}}@ {{valuecolor}}{actual_fps} {{labelcolor}}fps{{/all}}"
            )
            while True:
                ret, frame = cap.read()
                if frame is None:
                    continue

                height, width = frame.shape[:2]

                if not ret:
                    break

                frame = cv2.flip(frame, 1)
                ##                logentry(f"main_virtualcam.100: {context=}")
                ##                playingcard.detect(frame, context)
                ##                rect.detect(frame, context)
                indexfingertip.detect(frame, context)
                ##                touch.detect(frame, context)
                eyes.detect(frame, context)

                frame = apply_overlays(frame, context)
                frame = apply_title(frame, context)

                cv2.imshow(conf.TITLE, frame)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Send frame to virtual camera
                cam.send(frame)

                ch = cv2.waitKey(10) & 0xFF
                for o in OVERLAYS:
                    if ch == ord(o["key"]):
                        print(f"toggle {o=}")
                        o["running"] = True - o["running"]
                        break

                if ch == ord("q") or ch == 27:
                    break

                # Wait until next frame is due
                cam.sleep_until_next_frame()
    finally:
        cap.release()


def buildargs(args=None, **kw: dict):
    parser = argparse.ArgumentParser("asimov")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    parser.add_argument("--basedir", default="$HOME/projects/playingcarddata")
    parser.add_argument("--set-name", default="bicycle")

    #    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    #    database.buildargs(parser, defaults, suppress=True)

    return parser


def init(args, **kwargs):
    return True


def access(args, op, **kwargs):
    return True
