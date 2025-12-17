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

class CameraCapture:
    def __init__(self, device=0):
        self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        self.lock = threading.Lock() # Create a lock
        self.ret, self.frame = self.cap.read()
        self.stopped = False
        self.thread = None

    def get(self, cap):
        return self.cap.get(cap)
    
    def set(self, cap, val):
        return cv2.cap.set(cap, val)

    def start(self):
        """Starts the thread to read frames from the video stream."""
        # daemon=True ensures the thread dies when the main program exits
        self.thread = threading.Thread(target=self.update, args=(), daemon=True).start()
        return self

##        cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.CAP_WIDTH)
##        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.CAP_HEIGHT)
##        if cap.set(cv2.CAP_PROP_FPS, conf.CAP_FPS) is False:
##            io.echo(f"could not set FPS to {conf.FPS}")

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                flipped = cv2.flip(frame, 1)
                with self.lock: # Ensure the assignment is isolated
                    self.frame = flipped
            else:
                self.stopped = True

    def read(self):
        with self.lock: # Ensure the read is isolated
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        """Stops the thread and releases the hardware."""
        self.stopped = True
        if hasattr(self, "thread") and self.thread is not None:
            self.thread.join(timeout=1.0)
        self.cap.release()

    def isOpened(self) -> bool:
        return self.cap.isOpened()

class ProcessingWorker:
    """The 'Brain' thread: handles heavy detection logic."""
    def __init__(self, capture, context):
        self.capture = capture
        self.context = context
        self.stopped = False
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self):
        while not self.stopped:
            frame = self.capture.read()
            if frame is not None:
                # Perform the heavy lifting without blocking the camera output
                indexfingertip.detect(frame, self.context)
                eyes.detect(frame, self.context)
            else:
                time.sleep(0.01)

    def stop(self):
        self.stopped = True
        if hasattr(self, "thread") and self.thread is not None:
            self.thread.join(timeout=1.0)

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
        if camera_ready(capture) is False:
            raise RuntimeError("Camera is not ready after 5s")

        for name in glitch.GLITCH_LIST:
            kwargs = glitch.GLITCH_CONFIG.get(name, {})
            glitch.register(name, **kwargs)

        # Make sure the webcam opens correctly
        if not capture.isOpened():
            raise RuntimeError("Could not open webcam. check group membership.")

        actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = capture.get(cv2.CAP_PROP_FPS)

        # Get the frame size
        frame = capture.read()

        # get virtual camera device by label
        device = get_device_by_label(conf.VIRTCAM_LABEL)
##        io.echo(f"{{labelcolor}}virtualcam label {{valuecolor}}{conf.VIRTCAM_LABEL} {{labelcolor}}, device {{valuecolor}}{device}{{/all}}")
##        playingcard.init(args.basedir, args.set_name, context)
        # Start the virtual camera
        device = get_device_by_label(conf.VIRTCAM_LABEL)
        io.echo(f"----> virtual camera device: {device}")
        with pyvirtualcam.Camera(width=actual_width, height=actual_height, fps=actual_fps, print_fps=True, device=device) as cam:
            capture.start()
            io.echo(f"{{labelcolor}}Capture: {{valuecolor}}{conf.CAP_DEVICE}, virtcam: ({cam.device}) {actual_width}{{labelcolor}}x{{valuecolor}}{actual_height} {{labelcolor}}@ {{valuecolor}}{actual_fps} {{labelcolor}}fps{{/all}}")
            while True:
                raw_frame = capture.read()
                if raw_frame is None:
                    continue

                render_context = context.copy()

                display_frame = raw_frame.copy()
                display_frame = apply_overlays(display_frame, context)
                display_frame = apply_title(display_frame, context)

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
