import copy
import threading


import cv2

from asimov import io

try:
    from cvzone.FPS import FPS as cvzoneFPS
except ImportError:
    cvzoneFPS = None

try:
    from cvzone.HandTrackingModule import HandDetector
except ImportError:
    HandDetector = None

try:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    gi.require_version("GObject", "2.0")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, GObject
    from gi.repository import Gst, GstApp
except ImportError:
    Gtk = None
    Gdk = None
    GLib = None
    GdkPixbuf = None
    GObject = None
    Gst = None
    GstApp = None

RESOLUTION = (640, 480)
# RESOLUTION = (1280, 720)
SRC = 1
FONT = cv2.FONT_HERSHEY_SIMPLEX
FPS = 30

LABELCOLOR = (187, 187, 187)  # lightgray
VALUECOLOR = (0, 204, 85)  # green
DARKGRAY = (51, 51, 51)
BGCOLOR = DARKGRAY
GREEN = (0, 204, 85)
CONTOURCOLOR = GREEN
VIDEODEVICE = 1

# import gi
#
# gi.require_version('Gtk', '3.0')
# gi.require_version('Gst', '1.0')
# gi.require_version('GstApp', '1.0')
# gi.require_version('GObject', '2.0')
# gi.require_version('GdkPixbuf', '2.0')
#
# from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, GObject
# from gi.repository import Gst, GstApp


class VideoCaptureThread(threading.Thread):
    def __init__(self, src=0, width=800, height=600):
        super().__init__()
        self.cap = cv2.VideoCapture(src, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.running = True
        self.frame = None
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running and not self._stop_event.is_set():
            try:
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.frame = frame
            except Exception as e:
                io.echo(f"VideoCaptureThread: update failed: {e}", level="error")

    def get_frame(self):
        with self.lock:
            return self.frame

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
        io.echo("VideoCaptureThread: stopped and resources released")


class Asimov(object):
    def __init__(self):
        self.cap = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        # self.capthread = threading.Thread(target=self.capframe)

        self.greyscale = False
        self.handlehands = False

        # self.builder = Gtk.Builder()
        # self.builder.add_from_file("testgstgtk.glade")

        # Gst.init(sys.argv)
        # Gtk.init(sys.argv)

        self.fpsReader = cvzoneFPS(avgCount=FPS)

        self.handHandler = handHandler()

        self.number_frames = 0

        # self.gst_str = f"appsrc name=source emit-signals=true format=buffers caps=video/x-raw,format=BGR,width={RESOLUTION[0]},height={RESOLUTION[1]},framerate={FPS}/1 ! queue max-size-buffers=4 ! videoconvert ! udpsink host=localhost port=5000" # autovideosink sync=1"
        self.gst_str = "appsrc name=source emit-signals=true format=buffers ! jpegdec ! videoconvert ! x264enc ! rtph264pay ! udpsink port=5000"
        io.echo(f"{self.gst_str=}", level="debug")
        # self.gst_str = f"videotestsrc ! queue max-size-buffers=4 ! videoconvert ! udpsink host=localhost port=5000" # autovideosink sync=1"

        self.pipeline = Gst.parse_launch(self.gst_str)
        if self.pipeline is None:
            io.echo("failed to create pipline", level="error")
            return

        self.appsrc = self.pipeline.get_child_by_name("source")

        self.bus = self.pipeline.get_bus()
        if self.bus is not None:
            self.busid = self.bus.add_watch(73, self.bus_callback)
            io.echo(f"{self.busid=}", level="debug")

        Gst.debug_remove_log_function(None)
        Gst.debug_add_log_function(self.on_debug, None)
        Gst.debug_set_default_threshold(Gst.DebugLevel.DEBUG)
        Gst.debug_set_active(True)

    def capframe(self):
        # io.echo(f"{self.running=}", level="debug")
        # while self.running is True:
        # io.echo(f"capframe.100: trace {self.cap.isOpened()=}", level="debug")
        if self.cap.isOpened() is True:
            with self.lock:
                # io.echo("reading frame")
                ret, self.frame = self.cap.read()
                if not ret:
                    io.echo(f"capframe.120: {ret=}", level="debug")
        if self.running is True:
            return True
        return False

    def update(self):
        self.capframe()
        # self.show()
        self.push()
        return True

    def start(self):
        io.echo("starting...", level="debug")
        self.cap = cv2.VideoCapture(VIDEODEVICE)
        # io.echo(f"{self.cap=}", level="debug")
        if self.cap.isOpened():
            io.echo("cam opened")

        self.running = True

        self.appsrc.connect("need-data", self.on_need_data)

        # capframetimerid = GLib.timeout_add(30, self.capframe)
        GLib.idle_add(self.show)
        GLib.timeout_add(100, self.update)
        # GLib.timeout_add(350, self.show)

        # self.capthread.start()

    def pause(self):
        io.echo("pausing...", level="debug")

    def show(self):
        # io.echo(f"show.100: {self.frame=} {self.running=}", level="debug")
        # io.echo(f"show {self.frame=}", level="debug")
        # io.echo("show()", level="debug")
        if self.frame is None:
            io.echo("frame is none")
            return True

        f = self.frame
        f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        # io.echo(f"{f=}", level="debug")
        fps, f = self.fpsReader.update(
            f, bgColor=BGCOLOR, textColor=VALUECOLOR, scale=3, thickness=3
        )

        if self.greyscale is True:
            f = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
            f = cv2.cvtColor(f, cv2.COLOR_GRAY2RGB)
        else:
            f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        # io.echo(f"{fps=}", level="debug")
        if self.handlehands is True:
            f = self.handHandler.handle(f, draw=True)

        ret, f = cv2.imencode(".png", f)  # Adjust encoding format as needed
        # io.echo(f"{ret=}", level="debug")
        # data = encoded_img.tobytes()

        loader = GdkPixbuf.PixbufLoader()
        loader.write(f)
        pixbuf = loader.get_pixbuf()
        loader.close()
        # io.echo(f"{pixbuf.get_width()=} {pixbuf.get_height()=}", level="debug")
        # pixbuf = GdkPixbuf.Pixbuf.new_from_data(f.tobytes(),
        #                                    GdkPixbuf.Colorspace.RGB,
        #                                    False,
        #                                    8,
        #                                    f.shape[1],
        #                                    f.shape[0],
        #                                    f.shape[2]*f.shape[1])
        # io.echo(f"{pixbuf=}", level="debug")
        if pixbuf is None:
            io.echo("pixbuf is None", level="debug")
        # io.echo("calling set_from_pixbuf")
        image = self.builder.get_object("image")
        image.set_from_pixbuf(pixbuf.copy())
        return True

    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)

    def toggleGreyscale(self, *args):
        self.greyscale = not self.greyscale

    def toggleHands(self, *args):
        self.handlehands = not self.handlehands

    class eventHandler:
        greyscale = False
        hands = False

        def onDeleteWindow(self, *args):
            Gtk.main_quit(*args)

        def toggleGreyscale(self, *args):
            self.greyscale = not self.greyscale

        def toggleHands(self, *args):
            self.hands = not self.hands

    def main(self):
        window = self.builder.get_object("asimov")
        window.connect("key-release-event", self.on_key_release_event)
        window.set_default_size(RESOLUTION[0] * 1.05, RESOLUTION[1] * 1.05)

        window.show_all()

        self.builder.connect_signals(self)
        # self.builder.connect_signals(self.eventHandler())

        # GLib.idle_add(self.show)
        Gtk.main()

    def on_key_release_event(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False

    def bus_callback(self, bus, message):
        if message.type == Gst.MessageType.STATE_CHANGED:
            # Extract old and new states from the message
            old_state, new_state, pending = message.parse_state_changed()
            io.echo(f"{old_state=} -> {new_state=}")
        elif message.type == Gst.MessageType.ASYNC_DONE:
            io.echo("got async_done", level="debug")
        elif message.type == Gst.MessageType.ASYNC_START:
            io.echo("got async_start", level="debug")
        elif message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            io.echo(f"ERROR: {message.src.get_name()}: {error.message}", level="error")
        elif message.type == Gst.MessageType.EOS:
            io.echo("end of stream", level="info")

    # Function to push a frame to appsrc as a buffer
    def push(self, frame=None):
        if frame is None:
            frame = self.frame
        f = copy.copy(frame)
        ret, f = cv2.imencode(".jpg", f)

        # data = f.tobytes() # frame.tobytes()
        # Create GStreamer buffer
        buffer = Gst.Buffer.new_allocate(None, len(f), None)
        buffer.fill(0, f)

        # Set buffer properties
        duration = 1 / FPS * Gst.SECOND
        timestamp = self.number_frames * duration
        buffer.pts = buffer.dts = int(timestamp)
        buffer.offset = timestamp
        self.number_frames += 1

        # Push buffer to appsrc
        ret = self.appsrc.emit("push-buffer", buffer)
        if ret != Gst.FlowReturn.OK:
            io.echo(f"Error pushing buffer: {ret}", level="error")

    def on_need_data(self, src, length):
        # Convert frame to bytes (assuming BGR format)
        io.echo("on_need_data entered", level="debug")
        if self.frame is None:
            return

        self.push(self.frame)

    def on_debug(
        self, category, level, dfile, dfctn, dline, source, message, user_data
    ):
        if source:
            print(
                "Debug {} {}: {}".format(
                    Gst.DebugLevel.get_name(level), source.name, message.get()
                )
            )
        else:
            print("Debug {}: {}".format(Gst.DebugLevel.get_name(level), message.get()))

    def stop(self):
        io.echo("stopping...", level="debug")
        io.echo("sending EOS")
        eos = Gst.Event.new_eos()
        if eos is None:
            io.echo("stop.100: unable to create end-of-stream event", level="error")
        else:
            self.pipeline.send_event(eos)
            # io.echo("waiting for EOS...", level="debug", end="")
            # message = self.bus.timed_pop_filtered(3*Gst.SECOND, Gst.MessageType.EOS)
            # if message is None:
            #    io.echo("timeout", level="debug")
            # else:
            #    structure = message.get_structure()
            #    if structure is not None:
            #        io.echo(f"{structure.get('name')=}")

        self.running = False
        # self.capthread.join()
        self.pipeline.set_state(Gst.State.NULL)
        self.cap.release()

        # self.bus.remove_watch(self.busid)


class CardHandler(object):
    def handle(self, image):
        _image = image.copy()
        # io.echo(f"{img=}", level="debug")
        # Convert the image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        if ret is None:
            io.echo(
                "asimov.lib.handle_cards.100: threshold returned None", level="error"
            )
            return image
        contours, hierarchy = cv2.findContours(
            image=thresh, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(
            image=_image,
            contours=contours,
            contourIdx=-1,
            color=(0, 255, 0),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

        return _image

        # return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB) # thresh


class handHandler(object):
    def __init__(self):
        self.detector = HandDetector(
            staticMode=False,
            maxHands=1,
            modelComplexity=1,
            detectionCon=0.5,
            minTrackCon=0.5,
        )

    def handle(self, image, draw=True):
        hands, image = self.detector.findHands(image, draw=draw, flipType=True)
        if hands == [] or hands is None:
            return image

        for h in hands:
            fingers = self.detector.fingersUp(h)
            io.echo(f"{fingers=}", level="debug")
            if fingers == [0, 1, 0, 0, 0] or fingers == [1, 1, 0, 0, 0]:
                io.echo("index finger up")
        return image


def runmodule(args, modulepath, **kwargs):
    from . import module

    return module.run(args, f"asimov.{modulepath}", **kwargs)


def loadmodule(args, modulepath, **kwargs):
    from base import module

    return module.load(args, f"asimov.{modulepath}", **kwargs)
