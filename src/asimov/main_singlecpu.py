import cv2
from cvzone.HandTrackingModule import HandDetector
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

    detector = HandDetector(detectionCon=0.9, maxHands=1)

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

        hands, frame = detector.findHands(frame, draw=False)

        # Remove old fingertip position
        context.pop("index_tip", None)

        if hands:
            for hand in hands:
                lmList = hand["lmList"]
                index_tip = lmList[8]  # INDEX_FINGER_TIP
                index_tip_x = int(index_tip[0])
                index_tip_y = int(index_tip[1])

                context["index_tip"] = (index_tip_x, index_tip_y)

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
