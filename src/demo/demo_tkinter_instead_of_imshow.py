import cv2
import tkinter as tk
from PIL import Image, ImageTk

class OpenCVApp:
    def __init__(self, window, video_source=0):
        self.window = window
        self.window.title("OpenCV + Tkinter Dashboard")
        
        # 1. Initialize Video Capture
        self.vid = cv2.VideoCapture(video_source)
        
        # 2. Create UI Widgets
        self.canvas = tk.Label(window)
        self.canvas.pack(padx=10, pady=10)
        
        self.btn_quit = tk.Button(window, text="Exit Application", command=self.window.quit)
        self.btn_quit.pack(pady=5)
        
        # 3. Start the refresh loop
        self.update_frame()
        
    def update_frame(self):
        # Capture frame-by-frame
        ret, frame = self.vid.read()
        
        if ret:
            # OpenCV uses BGR, Tkinter/PIL uses RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert the image to a format Tkinter understands
            self.img = ImageTk.PhotoImage(image=Image.fromarray(frame))
            self.canvas.config(image=self.img)
            
        # Schedule the next update in 10ms (approx 60fps)
        self.window.after(10, self.update_frame)

    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()

# Run the app
root = tk.Tk()
app = OpenCVApp(root, video_source=0) # Change 0 to your --cap-device index
root.mainloop()
