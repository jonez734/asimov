import cv2
import numpy as np
import pyvirtualcam
import argparse
from cvzone.HandTrackingModule import HandDetector

# --- Import Reusable Functions from the assumed module ---
from asimov.util import blend_alpha, apply_layer_fade, interpolate_sequential 

# --- Configuration ---
WIDTH, HEIGHT = 640, 480
BALL_RADIUS = 20
BALL_COLOR = (0, 0, 255)  
MAX_TRAIL_LENGTH = 40 
BASE_TRAIL_COLOR = (255, 255, 0) # BGR - Cyan 
TRAIL_FADE_RATE = 0.95 

# --- Runtime State Variable ---
USE_TRUE_ALPHA = False 

def main():
    """
    Main function to initialize components and run the virtual pong trail demo.
    """
    global USE_TRUE_ALPHA

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
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    detector = HandDetector(detectionCon=0.8, maxHands=1) # Set maxHands to 1 for simplicity
    past_positions = [] 

    trail_canvas = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8) 

    print(f"--- Starting Demo ---")
    print(f"Camera Device Index: {device_index}")
    print(f"Press 'M' to switch rendering modes. Press 'Q' or 'ESC' to quit.")
    
    # --- 3. Virtual Camera Setup and Main Loop ---
    with pyvirtualcam.Camera(width=WIDTH, height=HEIGHT, fps=30, fmt=pyvirtualcam.PixelFormat.BGR) as cam:
        
        while True:
            success, img = cap.read()
            if not success:
                break
            
            img = cv2.flip(img, 1)
            hands, img = detector.findHands(img, flipType=False)
            ball_center = None
            is_index_isolatedly_up = False
            
            # ✋ Hand Detection and Gesture Check
            if hands:
                hand = hands[0]
                lmList = hand['lmList']
                
                # [Thumb, Index, Middle, Ring, Pinky]
                fingers = detector.fingersUp(hand)
                
                # Check for the specific gesture: Index (1) is UP, others (0, 2, 3, 4) are DOWN
                # fingers[0] = Thumb (should be 0/down)
                # fingers[1] = Index (should be 1/up)
                # fingers[2] = Middle (should be 0/down)
                # fingers[3] = Ring (should be 0/down)
                # fingers[4] = Pinky (should be 0/down)
                
                if fingers == [0, 1, 0, 0, 0]:
                    is_index_isolatedly_up = True
                    # Position is at the Index Finger Tip (Landmark 8)
                    x, y, _ = lmList[8]
                    ball_center = (x, y)

            # A. Decay the entire canvas (This ensures the old trail fades regardless of gesture)
            trail_canvas = apply_layer_fade(trail_canvas, TRAIL_FADE_RATE)
            
            # B. Update Trail Position List ONLY if the gesture is active
            if is_index_isolatedly_up and ball_center:
                past_positions.append(ball_center)
                if len(past_positions) > MAX_TRAIL_LENGTH:
                    past_positions.pop(0)
            else:
                # OPTIONAL: Clear the trail list immediately when the finger goes down
                # If you want the trail to instantly stop and disappear quickly, uncomment:
                # past_positions = []
                pass

            # C. Draw Trail Segments 
            if len(past_positions) >= 2:
                
                # Contiguity Fix: Split and Merge for Safe Drawing
                B, G, R, A = cv2.split(trail_canvas)
                bgr_canvas_temp = cv2.merge((B, G, R)) 
                
                for i in range(1, len(past_positions)):
                    pt1 = past_positions[i-1]
                    pt2 = past_positions[i]
                    
                    # Use imported interpolate_sequential for thickness
                    thickness = int(interpolate_sequential(i, MAX_TRAIL_LENGTH, 1.0, 8.0))
                    
                    if USE_TRUE_ALPHA:
                        # Use imported interpolate_sequential for alpha
                        alpha_value = int(interpolate_sequential(i, MAX_TRAIL_LENGTH, 0.0, 255.0))
                        line_color = BASE_TRAIL_COLOR
                        
                        cv2.line(bgr_canvas_temp, pt1, pt2, line_color, thickness)
                        cv2.line(A, pt1, pt2, (alpha_value), thickness) 
                        
                    else:
                        # Color Gradient Fade
                        intensity_factor = i / len(past_positions)
                        simulated_color = (
                            int(BASE_TRAIL_COLOR[0] * intensity_factor),
                            int(BASE_TRAIL_COLOR[1] * intensity_factor),
                            int(BASE_TRAIL_COLOR[2] * intensity_factor)
                        )
                        cv2.line(bgr_canvas_temp, pt1, pt2, simulated_color, thickness)
                
                # Merge the modified channels back into the main canvas
                B_new, G_new, R_new = cv2.split(bgr_canvas_temp)
                trail_canvas = cv2.merge((B_new, G_new, R_new, A))
                
            # D. Blending and Final Image
            
            if USE_TRUE_ALPHA:
                trail_bgr = trail_canvas[:,:,:3].astype(float)
                alpha = trail_canvas[:,:,3].astype(float) / 255.0 
                final_img = blend_alpha(trail_bgr, img.astype(float), alpha)
            else:
                final_img = cv2.addWeighted(img, 1, trail_canvas[:,:,:3], 1, 0)

            # E. Draw the Ball 🔴 and Status
            if ball_center:
                # Draw the ball only if the gesture is active
                cv2.circle(final_img, ball_center, BALL_RADIUS, BALL_COLOR, cv2.FILLED)
                cv2.putText(final_img, "STATUS: TRACKING (Index Isolated)", (50, HEIGHT - 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(final_img, "STATUS: IDLE (Requires Index Only)", (50, HEIGHT - 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # F. Display and Hotkeys
            mode_name = "TRUE ALPHA FADE (M)" if USE_TRUE_ALPHA else "COLOR GRADIENT FADE (M)"
            cv2.putText(final_img, f"Mode: {mode_name}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(final_img, f"Device: {device_index} | Quit: ESC/Q", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv2.imshow("Virtual Pong Trail Demo", final_img)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('m'):
                USE_TRUE_ALPHA = not USE_TRUE_ALPHA
                trail_canvas = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
                print(f"Switched mode to: {'TRUE ALPHA' if USE_TRUE_ALPHA else 'COLOR GRADIENT'}")
            
            if key == ord('q') or key == 27:
                break

            cam.send(cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB))
            cam.sleep_until_next_frame()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
