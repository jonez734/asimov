import cv2
import mediapipe as mp
import importlib

def init(args, **kwargs):
    return True

def buildargs(args, **kwargs):
    return None

def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    # Explicit list of processing modules
    MODULE_NAMES = [
        "asimov.detect_rectangles",
        "asimov.detect_touch",
        "asimov.draw_overlays",
        "asimov.track_rectangles",
        "asimov.update_osd",
    ]

    modules = []
    for mod_name in MODULE_NAMES:
        mod = importlib.import_module(mod_name)
        modules.append(mod)

    # Setup MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False,
                           max_num_hands=2,
                           min_detection_confidence=0.5,
                           min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(0)

    context = {
        "trackers": [],  # List of (tracker, id, color) tuples
        "tracker_id_counter": 0
    }

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                h, w, _ = frame.shape
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                context["left_index_tip"] = (int(index_tip.x * w), int(index_tip.y * h))
                break  # Just use the first detected hand for simplicity
        else:
            context.pop("left_index_tip", None)

        # Pass frame and context through all processing modules
        for mod in modules:
            if hasattr(mod, "should_run") and not mod.should_run(context):
                continue
            if hasattr(mod, "process"):
                frame, context = mod.process(frame, context)

        cv2.imshow("Modular Tracker", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    return True
