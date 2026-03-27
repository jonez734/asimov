import cv2
import time

# Global variables (not strictly necessary in this non-threaded version, but kept for consistency)
cap = None
ret = False
frame = None
fps = 0
running = True  # Still useful for controlling the loop


def main():
    global cap, ret, frame, fps, running

    if cv2.ocl.haveOpenCL():
        print("OpenCL is enabled in OpenCV. Attempting to use it.")
        cv2.ocl.setUseOpenCL(True)
    else:
        print("OpenCL is NOT enabled in OpenCV. Falling back to CPU.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        running = False
        return

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Actual Resolution: {actual_width}x{actual_height}")

    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_FPS, 30)

    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Actual FPS: {actual_fps}")

    cv2.namedWindow("Camera Feed")

    prev_frame_time = 0
    new_frame_time = 0

    while running:
        ret_val, frame_val = cap.read()
        if ret_val:
            ret = ret_val
            frame = frame_val

            new_frame_time = time.time()
            fps_calc = 1 / (new_frame_time - prev_frame_time)
            prev_frame_time = new_frame_time
            fps = int(fps_calc)

            cv2.putText(
                frame,
                str(fps),
                (7, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                3,
                (100, 255, 0),
                3,
                cv2.LINE_AA,
            )
            cv2.imshow("Camera Feed", frame)

        key = cv2.waitKey(1)
        if key == 27:
            running = False  # Set the flag to exit the loop
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
