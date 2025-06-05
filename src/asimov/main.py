import cv2
import mediapipe as mp
import importlib
import time

def access(args, op, **kwargs):
    return True

def init(args, **kwargs):
    return True

def buildargs(args, **kwargs):
    return None

def main(args, **kwargs):
    MODULE_NAMES = [
        "asimov.detect_rectangles",
        "asimov.track_rectangles",
        "asimov.detect_touch",
        "asimov.draw_overlays",
        "asimov.update_osd",
    ]

    modules = []
    for mod_name in MODULE_NAMES:
        mod = importlib.import_module(mod_name)
        modules.append(mod)

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    cap = cv2.VideoCapture(0)

    context = {
        "trackers": [],
        "tracker_id_counter": 0,
        "start_time": time.time(),
        "frame_count": 0,
        "distortions_enabled": False,
    }

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        context["frame_count"] += 1

        # Flip frame horizontally for natural mirror display
        frame = cv2.flip(frame, 1)

        h, w, _ = frame.shape
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        # Remove old fingertip position
        context.pop("index_tip", None)

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, hand_info in zip(results.multi_hand_landmarks, results.multi_handedness):

                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                #index_tip_x = int((1 - index_tip.x) * w)
                #index_tip_y = int(index_tip.y * h)
                index_tip_x = int(index_tip.x*w)
                index_tip_y = int(index_tip.y*h)

                label = hand_info.classification[0].label  # 'Left' or 'Right'
                # Track left hand fingertip only
                #if label == "Left":
                context["index_tip"] = (index_tip_x, index_tip_y)

                # Draw hand landmarks on the original (unflipped) frame
                # mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)



        # Run all modules
        for mod in modules:
            if hasattr(mod, "should_run") and not mod.should_run(context):
                continue
            if hasattr(mod, "process"):
                frame, context = mod.process(frame, context)

        cv2.imshow("project asimov", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
