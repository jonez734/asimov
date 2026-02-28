import sys
import time
import threading

import gi
#gi.require_version('Gtk', '3.0')
gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
gi.require_version('GObject', '2.0')

#from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
from gi.repository import Gst, GLib

from bbsengine6 import io

from asimov import lib as libasimov

import cv2

class Asimov(object):
    def __init__(self):
        self.number_frames = 0
        self.fps = libasimov.FPS
        self.duration = 1 / self.fps * Gst.SECOND
        self.cap = cv2.VideoCapture(1)
        # io.echo(f"{self.cap=}", level="debug")
        gst_str = "appsrc name=source emit-signals=true is-live=true ! queue ! video/x-raw,format=BGR ! videoconvert ! udpsink name=sink port=5000"
        # gst_str = "appsrc name=source emit-signals=true is-live=true ! queue ! video/x-raw,format=BGR ! videoconvert ! x264enc insert-vui=1 ! h264parse ! rtph264pay ! udpsink name=sink port=5000"
        # self.out = cv2.VideoWriter(gst_str, cv2.CAP_GSTREAMER, 0, float(libasimov.FPS), libasimov.RESOLUTION)
        # gst_str = "appsrc name=asimovsrc ! videoconvert ! queue ! x264enc tune=zerolatency bitrate=500000 ! rtph264pay ! udpsink host=127.0.0.1 port=5000"
        # gst_str="appsrc name=source ! video/x-raw, format=(string)BGR ! jpegenc ! udpsink host=127.0.0.1 port=5000"
        # gst_str = "appsrc name=source ! application/x-raw ! jpegenc ! udpsink host=127.0.0.1 port=5000"
        # gst_str = "appsrc name=source ! rtpjpegpay ! udpsink host=localhost port=5000"
        # gst_str = "appsrc name=source ! decodebin ! videoconvert ! jpegenc ! rtpjpegpay ! udpsink host=localhost port=5000"
        # gst_str = "appsrc name=source ! videoconvert ! x264enc speed-preset=ultrafast tune=zerolatency byte-stream=true ! mpegtsmux ! udpsink name=sink host=localhost port=5000"
        
        self.pipeline = Gst.parse_launch(gst_str)
        if self.pipeline is None:
            io.echo("failed to create pipline", level="error")
            return
        #self.appsrc = self.pipeline.query("uri")
        self.appsrc = self.pipeline.get_child_by_name("source")
        # io.echo(f"{self.appsrc=}")
        # self.appsrc.connect("need-data", self.on_need_data) # moved to .start()
        # self.appsrc = self.pipeline.get_child_by_name("appsrc")
        # io.echo(f"pipline.init.100: {self.source=}")
        self.bus = self.pipeline.get_bus()
        if self.bus is not None:
            self.busid = self.bus.add_watch(73, self.bus_callback)
            io.echo(f"{self.busid=}", level="debug")
        self.running = False
        self.frame = None
        self.loop = GLib.MainLoop()
        self._capthread = None
        self._showthread = None
        # self._glibmainloopthread = None
        self.lock = threading.Lock()
        # self.out = cv2.VideoWriter(gst_str, cv2.VideoWriter_fourcc(*"MJPG"), libasimov.FPS, libasimov.RESOLUTION)

        # io.echo(f"{gst_str=} {self.pipeline=} {self.source=}", level="debug")

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
  
    def on_need_data(self, src, length):
        # Convert frame to bytes (assuming BGR format)
        io.echo("on_need_data entered", level="debug")
        if self.frame is None:
            return

        self.push_buffer(self.frame)

    def on_debug(self, category, level, dfile, dfctn, dline, source, message, user_data):
        if source:
	        print('Debug {} {}: {}'.format(Gst.DebugLevel.get_name(level), source.name, message.get()))
        else:
            print('Debug {}: {}'.format(Gst.DebugLevel.get_name(level), message.get()))

    def start(self):
        io.echo("start() called", level="debug")
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        io.echo(f"{ret=}", level="debug")
        if ret == Gst.StateChangeReturn.SUCCESS:
            io.echo("Pipeline state changed to PLAYING successfully.")
        elif ret == Gst.StateChangeReturn.ASYNC:
            io.echo("Pipeline state change is asynchronous.")
            # Wait for state change notification on the bus
            message = self.bus.timed_pop(3 * Gst.SECOND) # Gst.CLOCK_TIME_NONE)
            if message:
                io.echo(f"{message=}", level="debug")
                #if message.type == Gst.State.STATE_CHANGED:
                #    old_state, new_state, _ = message.parse_state_changed()
                #    if new_state == Gst.State.PLAYING:
                #        io.echo("Pipeline is now PLAYING.")
                #    else:
                #        io.echo(f"Unexpected state change: {Gst.StateNames.get_name(new_state)}")
                #else:
                #    io.echo("Received unexpected message type on the bus.")
            else:
                io.echo("Timeout waiting for message on the bus.")
        else:
            io.echo(f"Error changing pipeline state: {ret}")

        self.appsrc.connect("need-data", self.on_need_data)

        Gst.debug_remove_log_function(None)
        Gst.debug_add_log_function(self.on_debug, None)
        Gst.debug_set_default_threshold(Gst.DebugLevel.INFO)
        Gst.debug_set_active(True)
        self.running = True
        
    def _get_frame(self):
        # start = time.time()
        while self.running is True:
            if self.cap.isOpened() is True:
                with self.lock:
                    ret, self.frame = self.cap.read()
                if not ret:
                    self.running = False

    # Function to push a frame to appsrc as a buffer
    def push_buffer(self, frame):
        data = frame.tobytes()
        # Create GStreamer buffer
        buffer = Gst.Buffer.new_allocate(None, len(data), None)
        buffer.fill(0, data)

        # Set buffer properties
        duration = 1 / self.fps * Gst.SECOND
        timestamp = self.number_frames * duration
        buffer.pts = buffer.dts = int(timestamp)
        buffer.offset = timestamp
        self.number_frames += 1

        # Push buffer to appsrc
        ret = self.appsrc.emit("push-buffer", buffer)
        if ret != Gst.FlowReturn.OK:
            print(f"Error pushing buffer: {ret}")

    def run(self):
        if not self._capthread:
            self._capthread = threading.Thread(target=self._get_frame)
            self._capthread.start()
            io.echo("capture thread started", level="debug")
        #if not self._showthread:
        #    self._showthread = threading.Thread(target=self._show_frame)
        #    self._showthread.start()
        #    io.echo("show thread started", level="debug")
        #if not self._glibmainloopthread:
        #    self._glibmainloopthread = threading.Thread(target=self._glib_mainloop)
        #    self._glibmainloopthread.start()

        while self.running is True:
            if self.frame is None:
                time.sleep(1)
                io.echo("sleep")
                continue

            #self.push_buffer(self.frame)
            cv2.imshow("frame", self.frame)
            ch = cv2.waitKey(1) & 0xFF
            if ch == "q" or ch == 27:
                self.running = False

        #self.loop.run()
        #while self.running is True:
        #    # io.echo("loop")
        #    time.sleep(0.125)

        #while self.running is True:
        #    # help(self.pipeline.get_state) 
        #    # io.echo(f"{self.pipeline.get_state()=}", level="debug")
        #    start = time.time()
        #    if self.cap.isOpened() is True:
        #        ret, self.frame = self.cap.read()
        #        if not ret:
        #            self.running = False
        #            break
        #    # io.echo(f"{ret=}", level="debug")
        #    #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #
        #    cv2.imshow("frame", self.frame)
        #    # self.push_frame(self.frame)
        #
        #    ch = cv2.waitKey(1) & 0xFF
        #    if ch == 27:
        #        self.running = False
        #
        #    # try:
        #    # 	ret = self.out.write(frame)
        #    # except Exception as e:
        #    # 	io.echo(f"Error writing frame: {e}")
        #
        #    #data = frame.tobytes()
        #    #buf = Gst.Buffer.new_allocate(None, len(data), None)
        #    #buf.fill(0, data)
        #    #buf.duration = self.duration
        #    #timestamp = self.framecount * self.duration
        #    #buf.pts = buf.dts = int(timestamp)
        #    #buf.offset = timestamp
        #    #self.framecount += 1
        #    #retval = self.source.emit("push-buffer", buf)
        #    #if retval != Gst.FlowReturn.OK:
        #    #    io.echo(f"{retval=}", level="warning")

    def stop(self):
        self.running = False
        io.echo("sending EOS")
        eos = Gst.Event.new_eos()
        if eos is None:
            io.echo("stop.100: unable to create end-of-stream event", level="error")
        else:
            self.pipeline.send_event(eos)
            io.echo("waiting for EOS...", level="debug", end="")
            message = self.bus.timed_pop_filtered(3*Gst.SECOND, Gst.MessageType.EOS)
            if message is None:
                io.echo("timeout", level="debug")
            else:
                structure = message.get_structure()
                if structure is not None:
                    io.echo(f"{structure.get('name')=}")

        #io.echo("setting stream state to null", level="debug")
        #self.pipeline.set_state(Gst.State.NULL)
        self.cap.release()
        # self.out.release()
        # Gst.event_unref(eos)
        # self.bus.remove_watch(self.busid)
        #self._capthread.stop()
        #self._showthread.stop()

        if self.loop is not None:
            self.loop.quit()


def main():
    io.echo("init gst", level="debug")
    Gst.init(sys.argv)
    io.echo("init pipline", level="debug")
    asimov = Asimov()
    io.echo("start pipeline", level="debug")
    asimov.start()
    try:
        asimov.run()
        # asimov.loop.run()
    except KeyboardInterrupt:
        io.echo("*INTR*")
    finally:
        asimov.stop()
    # io.inputboolean("prompt: ")
if __name__ == "__main__":
    main()
