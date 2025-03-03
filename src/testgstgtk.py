import threading

import cv2
import numpy as np

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
 
from bbsengine6 import io

from asimov import lib as libasimov

import cvzone
from cvzone.FPS import FPS as cvzoneFPS
from cvzone.HandTrackingModule import HandDetector

class Asimov(object):
    def __init__(self):
        self.cap = None
        self.lock = threading.Lock()
        self.running = False
        self.capthread = threading.Thread(target=self.capframe)
        self.gst_str = "appname name=source format=time caps=video/x-raw,format=BGR,width={libasimov.RESOLUTION[0]},height={libasimov.RESOLUTION[1]} ! videoconvert ! autovideosink sync=1"

        self.builder = Gtk.Builder()
        self.builder.add_from_file("testgstgtk.glade")

    def capframe(self):
        while self.running is True:
            if self.cap.isOpened() is True:
                with self.lock:
                    ret, self.frame = self.cap.read()
                    if not ret:
                        self.running = False
    def start(self):
        io.echo("starting...", level="debug")
        self.cap = cv2.VideoCapture(libasimov.VIDEODEVICE)
        self.capthread.start()

    def pause(self):
        io.echo("pausing...", level="debug")
        io.echo("pass")

    def _show(self):
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(self.frame.tobytes(),
                                            GdkPixbuf.Colorspace.RGB,
                                            False,
                                            8,
                                            self.frame.shape[1],
                                            self.frame.shape[0],
                                            self.frame.shape[2]*frame.shape[1])
        builder = Gtk.Builder()
        builder.add_from_file("testgtk.glade")

        image.set_from_pixbuf(pixbuf.copy())
        
    def on_key_release_event(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False

    def stop(self):
        io.echo("stopping...", level="debug")
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

        self.running = False
        # io.echo("setting stream state to null", level="debug")
        self.cap.release()
        self.capthread.stop()
        self.pipeline.set_state(Gst.State.NULL)
        # self.bus.remove_watch(self.busid)

def main():
    asimov = Asimov()
    asimov.start()

if __name__ == "__main__":
    main()