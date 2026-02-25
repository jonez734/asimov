import cv2
import time
import threading
import numpy as np

class CameraThread(threading.Thread):
    def __init__(self, camera_index=0):
        threading.Thread.__init__(self)
        self.cap = cv2.VideoCapture(camera_index)
        self.ret = False  # Initialize ret
        self.frame = None  # Initialize frame
        self.fps = 0
        self.running = True # Flag to stop the thread
#        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Actual Resolution: {actual_width}x{actual_height}")  # Verify
    def run(self):
        prev_frame_time = 0
        new_frame_time = 0

        while self.running:  # Check the running flag
            ret, frame = self.cap.read()
            if ret:
                self.ret = ret
                self.frame = frame

                new_frame_time = time.time()
                fps = 1/(new_frame_time-prev_frame_time)
                prev_frame_time = new_frame_time
                self.fps = int(fps) # Store the fps value
            else:
                self.running = False # Stop the thread if no frame

        self.cap.release() # Release capture when thread is done

    def stop(self):
        self.running = False # Set the flag to stop the thread
        self.join() # Wait for the thread to fully stop

class HandDetector:
    def __init__(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2() # Background subtraction
        self.kernel = np.ones((5,5),np.uint8) # Kernel for morphological operations

    def find_hands(self, frame):
        umat_frame = cv2.UMat(frame)
        gray = cv2.cvtColor(umat_frame, cv2.COLOR_BGR2GRAY)

        fg_mask = self.background_subtractor.apply(gray) # Apply background subtraction

        # Morphological operations to remove noise
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel)

        # Skin color detection (very basic - needs calibration)
#        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
#        lower_skin = np.array([0, 20, 70])  # Example lower skin boundary
#        upper_skin = np.array([20, 255, 255]) # Example upper skin boundary
#        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

        # Combine background subtraction and skin detection (AND operation)
#        final_mask = cv2.bitwise_and(fg_mask, skin_mask)

        # Find contours (potential hand regions)
        contours, _ = cv2.findContours(fg_mask.get(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        return contours # Return the contours

    def draw_hand_rectangles(self, frame, contours):
        for contour in contours:
            if cv2.contourArea(contour) > 5000:  # Filter small contours (noise)
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        return frame

def main():
    camera_thread = CameraThread()
    camera_thread.start()
    # hand_detector = HandDetector()

    if not cv2.ocl.haveOpenCL():
        print("OpenCL is not available in OpenCV")
        exit()
    else:
        cv2.ocl.setUseOpenCL(True)

    cv2.namedWindow("Camera Feed")

    while True:
        if camera_thread.ret:
            frame = camera_thread.frame
            fps_text = str(camera_thread.fps)
            cv2.putText(frame, fps_text, (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)

            #contours = hand_detector.find_hands(frame)
            #frame = hand_detector.draw_hand_rectangles(frame, contours)

            cv2.imshow("Camera Feed", frame)

        key = cv2.waitKey(1)
        if key == 27:
            break

        if not camera_thread.is_alive(): # Check if thread is still running
            break
    camera_thread.stop() # Stop the thread gracefully
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
