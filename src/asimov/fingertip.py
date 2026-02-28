# UNUSED - DEPRECATED
# This module is not used by main_dashboard. Left for reference.
# Use asimov.modules.indexfingertip instead.
# Note: This file has broken conf references and should not be used.

from . import conf

import cv2
import mediapipe as mp
from cvzone.HandTrackingModule import HandDetector

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.8)

# Create hand detector instance
detector = HandDetector(detectionCon=0.9, maxHands=2)

def detect(frame, context):
    # Detect hands and get list of hands and image with drawing
    hands, frame = detector.findHands(frame, draw=False)
    index_finger_tip = None
#    logentry(f"fingertip.detect.100: {hands=}")
    if hands:
        for hand in hands:
            fingers = detector.fingersUp(hand)
            if fingers == [0, 1, 0, 0, 0]:  # Only index finger is up
                # Get index finger tip position (landmark 8)
                context["index_finger_tip"] = tuple(hand['lmList'][8][:2])  # x, y
#                logentry(f"{context['index_finger_tip']=}")
            else:
                context["index_finger_tip"] = None
    else:
        context["index_finger_tip"] = None

def draw(frame, context):
    index_finger_tip = context.get("index_finger_tip", None)
    if index_finger_tip:
        cv2.circle(frame, index_finger_tip, conf.FINGERTIP_CIRCLE_RADIUS, conf.FINGERTIP_COLOR, -1)
    return frame
