import cv2
import numpy as np
import pyvirtualcam
from cvzone.HandTrackingModule import HandDetector
import argparse # Import the argparse library

# --- Configuration ---
WIDTH, HEIGHT = 1280, 720
BALL_RADIUS = 20
BALL_COLOR = (0, 0, 255)  
MAX_TRAIL_LENGTH = 40 
BASE_TRAIL_COLOR = (255, 255, 0) # BGR - Cyan 
TRAIL_FADE_RATE = 0.95 

# --- Runtime State Variable (Global or Class-level for simple access) ---
USE_TRUE_ALPHA = False 

def alpha_blend(foreground_bgr_float, background_bgr_float, alpha_3ch):
    """
    Performs true alpha blending between a foreground and background layer.
    
    Args:
        foreground_bgr_float: BGR color layer of the foreground (trail), dtype float.
        background_bgr_float: BGR color layer of the background (live cam), dtype float.
        alpha_3ch: Alpha channel (0.0 to 1.0), replicated across 3 channels, dtype float.
        
    Returns:
        The blended image as a NumPy array (dtype np.uint8).
    """
    # Blending formula: final = (alpha * foreground) + ((1 - alpha) * background)
    blended_img_float = (alpha_3ch * foreground_bgr_float) + ((1 - alpha_3ch) * background_bgr_float)
    return blended_img_float.astype(np.uint8)

def main():
    """
    Main function to initialize components and run the virtual pong trail demo.
    """
    global USE_TRUE_ALPHA # Access the global state variable

    # --- 1. Argument Parsing ---
    parser = argparse.ArgumentParser(description="Virtual Pong Trail Demo with CVZone and PyVirtualCam.")
    parser.add_argument(
        '--device', 
        type=int, 
        default=0, 
        help='The camera device index (e.g., 0, 1, 2) to use for capture. Default is 0.'
    )
    args = parser.parse_args()
    device_index = args.device

    # --- 2. Initialization ---
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print(f"Error: Could not open camera device {device_index}. Exiting.")
        return
        
    cap.set(3, WIDTH)
    cap.set(4, HEIGHT)
    detector = HandDetector(detectionCon=0.8, maxHands=2)
    past_positions = [] 

    # Initialize the persistent canvas layer with 4 channels (BGRA)
    trail_canvas = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8) 

    print(f"--- Starting Demo ---")
    print(f"Camera Device Index: {device_index}")
    print(f"Press 'M' to switch rendering modes.")
    print(f"Press 'Q' to quit.")
    
    # --- 3. Virtual Camera Setup and Main Loop ---
    with pyvirtualcam.Camera(width=WIDTH, height=HEIGHT, fps=30, fmt=pyvirtualcam.PixelFormat.BGR) as cam:
        print(f'Using virtual camera: {cam.device}')
        
        while True:
            success, img = cap.read()
            if not success:
                break
            
            img = cv2.flip(img, 1)
            hands, img = detector.findHands(img, flipType=False)
            ball_center = None
            
            # Placeholder for fingertip logic (uses index finger tip landmark 8)
            if hands:
                lmList = hands[0]['lmList']
                x, y, _ = lmList[8]
                ball_center = (x, y)

            # Update Trail Position List
            if ball_center:
                past_positions.append(ball_center)
                if len(past_positions) > MAX_TRAIL_LENGTH:
                    past_positions.pop(0)

            # A. Decay the entire canvas (Applied to all 4 channels)
            decay_factor = TRAIL_FADE_RATE
            trail_canvas = cv2.addWeighted(trail_canvas, decay_factor, np.zeros_like(trail_canvas), 1 - decay_factor, 0)
            
            # B. Draw Trail Segments based on Current Mode
            if len(past_positions) >= 2:
                for i in range(1, len(past_positions)):
                    pt1 = past_positions[i-1]
                    pt2 = past_positions[i]
                    
                    thickness = int(np.interp(i, [1, MAX_TRAIL_LENGTH], [1, 8]))
                    
                    if USE_TRUE_ALPHA:
                        # --- MODE 1: TRUE ALPHA FADE ---
                        # Alpha value is 0 (oldest) to 255 (newest)
                        alpha_value = int(np.interp(i, [1, MAX_TRAIL_LENGTH], [0, 255]))
                        line_color = BASE_TRAIL_COLOR
                        
                        # Draw solid line color onto the BGR channels
                        cv2.line(trail_canvas[:,:,:3], pt1, pt2, line_color, thickness)
                        # Draw the corresponding alpha value onto the Alpha channel
                        cv2.line(trail_canvas[:,:,3], pt1, pt2, (alpha_value), thickness) 
                        
                    else:
                        # --- MODE 2: COLOR GRADIENT FADE ---
                        # Intensity factor is 0.0 (oldest) to 1.0 (newest)
                        intensity_factor = i / len(past_positions)
                        
                        # Interpolate the color from black to BASE_TRAIL_COLOR
                        simulated_color = (
                            int(BASE_TRAIL_COLOR[0] * intensity_factor),
                            int(BASE_TRAIL_COLOR[1] * intensity_factor),
                            int(BASE_TRAIL_COLOR[2] * intensity_factor)
                        )
                        
                        # Draw solid color line onto the BGR channels
                        cv2.line(trail_canvas[:,:,:3], pt1, pt2, simulated_color, thickness)
                        # Ensure Alpha channel is zero/ignored for this mode (handled by blending below)

            # C. Blending and Final Image
            
            if USE_TRUE_ALPHA:
                # Manual Alpha Blending
                trail_bgr = trail_canvas[:,:,:3].astype(float)
                alpha = trail_canvas[:,:,3].astype(float) / 255.0 
                img_float = img.astype(float)
                alpha_3ch = cv2.merge([alpha, alpha, alpha])
                
                final_img = alpha_blend(trail_bgr, img_float, alpha_3ch)
            else:
                # Color Gradient Blending (Simple Weighted Addition)
                final_img = cv2.addWeighted(img, 1, trail_canvas[:,:,:3], 1, 0)

            # D. Draw the Ball 🔴
            if ball_center:
                cv2.circle(final_img, ball_center, BALL_RADIUS, BALL_COLOR, cv2.FILLED)

            # E. Hotkey and Display
            mode_name = "TRUE ALPHA FADE (Press 'M')" if USE_TRUE_ALPHA else "COLOR GRADIENT FADE (Press 'M')"
            cv2.putText(final_img, f"Mode: {mode_name}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(final_img, f"Device: {device_index}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv2.imshow("Virtual Pong Trail Demo", final_img)
            
            # Key Press Handling
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('m'):
                USE_TRUE_ALPHA = not USE_TRUE_ALPHA
                # Clear canvas on mode switch
                trail_canvas = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
                print(f"Switched mode to: {'TRUE ALPHA' if USE_TRUE_ALPHA else 'COLOR GRADIENT'}")
            
            if key == ord('q'):
                break

            # Send to Virtual Camera
            cam.send(cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB))
            cam.sleep_until_next_frame()

    # --- 4. Cleanup ---
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
