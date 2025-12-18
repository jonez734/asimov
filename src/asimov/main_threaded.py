import time
import threading
# import locale
import argparse
##from dataclasses import dataclass, field

import cv2
import pyvirtualcam

from .util import draw_text, get_bottom_right_position, get_device_by_label, camera_ready

###from .common import ThreadSafeContext, CaptureCamera, ProcessingWorker
from . import rect, conf, glitch, indexfingertip, touch, eyes_next as eyes, playingcard

##from .common import logentry
from . import io

# Constants
#MARGIN = 20  # pixels
#TITLE = "Project Asimov v202509.0"
#CAP_HEIGHT = 480
#CAP_WIDTH = 640
#CAP_FPS = 30

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

class ThreadSafeContext(dict):
    """
    A dictionary subclass that uses a threading lock for all access.
    Maintains backward compatibility with existing detection and drawing functions.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()

    def __getitem__(self, key):
        with self._lock:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        with self._lock:
            super().__setitem__(key, value)

    def __delitem__(self, key):
        with self._lock:
            super().__delitem__(key)

    def __contains__(self, key):
        with self._lock:
            return super().__contains__(key)

    def get(self, key, default=None):
        with self._lock:
            return super().get(key, default)

    def copy(self):
        """Returns a non-thread-safe snapshot for rendering."""
        with self._lock:
            return super().copy()

# --- 2. Capture Thread (Hardware Owner) ---
class CameraCapture:
    def __init__(self, src):
        self.src = src
        self.frame = None
        self.stopped = False
        self.lock = threading.Lock()
        self.thread = None
        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        # Wait for hardware to warm up so Main has dimensions
        timeout = time.time() + 7.0
        while self.frame is None and time.time() < timeout:
            time.sleep(0.1)
        if self.frame is None:
            raise RuntimeError("Webcam failed to initialize.")
        return self

    def _run(self):
        """Background thread: Opens, Reads, and Closes the camera."""
        cap = cv2.VideoCapture(self.src, cv2.CAP_V4L2)
        
        # Verify hardware before starting loop
        if not cap.isOpened() or not camera_ready(cap):
            io.echo("{{error}}Capture: Hardware not available.{{/all}}")
            self.stopped = True
            cap.release()
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.CAP_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.CAP_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, conf.CAP_FPS)

        self.actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.actual_fps = cap.get(cv2.CAP_PROP_FPS)

        while not self.stopped:
            ret, frame = cap.read()
            if not ret or frame is None: break
            
            flipped = cv2.flip(frame, 1)
            with self.lock:
                self.frame = flipped
        
        cap.release()
        io.echo("Capture: Hardware released.")

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.stopped = True
        if self.thread: self.thread.join(timeout=2.0)

# --- 3. Processing Thread (The Brain) ---
class ProcessingWorker:
    def __init__(self, capture, context):
        self.capture = capture
        self.context = context
        self.stopped = False

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self):
        while not self.stopped:
            frame = self.capture.read()
            if frame is not None:
                # Heavy lifting on pristine frames
                indexfingertip.detect(frame, self.context)
                eyes.detect(frame, self.context)
                glitch.scheduler() # Decides to glitch
            else:
                time.sleep(0.01)
    def stop(self):
        self.stopped = True


def apply_title(frame, context):
    return draw_text(frame, 10, 15, conf.TITLE, color=conf.WATERMARK_COLOR, font_scale=0.50, alpha=0.75, shadow_alpha=0.75, shadow_offset=2)

def apply_glitches(frame, context):
    glitch.scheduler()
    return glitch.apply(frame)

OVERLAYS = [
#            { "key": "f", "enabled":True, "running":True,  "label": "fingertip",  "func": lambda frame, context: indexfingertip.draw(frame, context)},
#            { "key": "r", "enabled":True, "running":True,  "label": "rects",      "func": lambda frame, context: rect.draw(frame, context)},
#            { "key": "p", "enabled":True, "running":True,  "label": "playingcards",      "func": lambda frame, context: playingcard.draw(frame, context)},
            { "key": "e", "enabled":True, "running":True,  "label": "eyes",       "func": eyes.draw}, #lambda frame, context: eyes.draw(frame, context)},
#            { "key": "w", "enabled":True, "running":True,  "label": "watermark", "func": lambda frame, context: watermark.draw(frame, context)},
            { "key": "t", "enabled":True, "running":False, "label": "title",      "func": lambda frame, context: apply_title(frame, context)},
            { "key": "g", "enabled":True, "running":False, "label": "glitches",   "func": lambda frame, context: apply_glitches(frame, context)},
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

    context = ThreadSafeContext()

    capture = CameraCapture(conf.CAP_DEVICE).start()
    processing = ProcessingWorker(capture, context).start()
    
    # cap = cv2.VideoCapture(conf.CAP_DEVICE, cv2.CAP_V4L2)

    try:
        # Make sure the webcam opens correctly
#        if not capture.src.isOpened():
#            raise RuntimeError("Could not open webcam. check group membership.")

        for name in glitch.GLITCH_LIST:
            kwargs = glitch.GLITCH_CONFIG.get(name, {})
            glitch.register(name, **kwargs)

##        actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
##        actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
##        actual_fps = capture.get(cv2.CAP_PROP_FPS)

##        # Get the frame size
##        frame = capture.read()

        # get virtual camera device by label
        device = get_device_by_label(conf.VIRTCAM_LABEL)
##        io.echo(f"{{labelcolor}}virtualcam label {{valuecolor}}{conf.VIRTCAM_LABEL} {{labelcolor}}, device {{valuecolor}}{device}{{/all}}")
##        playingcard.init(args.basedir, args.set_name, context)
        # Start the virtual camera
##        device = get_device_by_label(conf.VIRTCAM_LABEL)
        io.echo(f"----> virtual camera device: {device}")
        with pyvirtualcam.Camera(width=capture.actual_width, height=capture.actual_height, fps=capture.actual_fps, print_fps=True, device=device) as cam:
#            capture.start()
#            processing.start()
            io.echo(f"{{labelcolor}}Capture: {{valuecolor}}{conf.CAP_DEVICE}, virtcam: ({cam.device}) {capture.actual_width}{{labelcolor}}x{{valuecolor}}{capture.actual_height} {{labelcolor}}@ {{valuecolor}}{capture.actual_fps} {{labelcolor}}fps{{/all}}")
            while True:
                raw_frame = capture.read()
                if raw_frame is None:
                    continue

                render_context = context.copy()

                display_frame = raw_frame.copy()
                display_frame = apply_overlays(display_frame, render_context)
                display_frame = apply_title(display_frame, render_context)

                cv2.imshow(conf.TITLE, display_frame)

                display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

                # Send frame to virtual camera
                cam.send(display_frame)

                # Wait until next frame is due
                cam.sleep_until_next_frame()

                ch = cv2.waitKey(10) & 0xFF
                for o in OVERLAYS:
                    if ch == ord(o["key"]):
                        print(f"toggle {o=}")
                        o["running"] = True - o["running"]
                        break

                if ch == ord("q") or ch == 27:
                    break
    finally:
        capture.stop()
        processing.stop()

def buildargs(args=None, **kw:dict):
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
