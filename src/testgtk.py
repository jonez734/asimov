import cv2
import gi
 
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
 
cap = cv2.VideoCapture(1)
 
builder = Gtk.Builder()
builder.add_from_file("testgtk.glade")
 
greyscale = False
 
class Handler:
    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)
 
    def toggleGreyscale(self, *args):
        global greyscale
        greyscale = not greyscale
 
 
def on_key_release_event(widget, event):
    if event.keyval == Gdk.KEY_Escape:
        Gtk.main_quit()
        return True
    return False
        
def show_frame(*args):
    ret, frame = cap.read()
    frame = cv2.resize(frame, None, fx=2, fy=2, interpolation = cv2.INTER_CUBIC)
    if greyscale:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    else:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
 
    pb = GdkPixbuf.Pixbuf.new_from_data(frame.tobytes(),
                                        GdkPixbuf.Colorspace.RGB,
                                        False,
                                        8,
                                        frame.shape[1],
                                        frame.shape[0],
                                        frame.shape[2]*frame.shape[1])
    image.set_from_pixbuf(pb.copy())
    return True

window = builder.get_object("asimov")
window.connect("key-release-event", on_key_release_event)
image = builder.get_object("image")
window.show_all()
builder.connect_signals(Handler())
 
GLib.idle_add(show_frame)
Gtk.main()
