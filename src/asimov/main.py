import random
import time
import threading

import cv2
import numpy as np
import mediapipe as mp

from OpenGL.GL import *

from flask import Flask, Response

import glfw

import importlib

# Explicit list of processing modules
MODULE_NAMES = [
    "detect_rectangles",
    "detect_touch",
    "draw_overlays",
]

# Global variables
#texture_id = None
#next_distortion_time = time.time() + random.uniform(2, 5)

# OpenCV video capture
#cap = cv2.VideoCapture(0)
#detector = HandDetector(detectionCon=0.8, maxHands=2)

# MARGIN = 10

# moved to asimov.util
#def update_texture(textureid, image):
#    glBindTexture(GL_TEXTURE_2D, textureid)
#    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.shape[1], image.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, image)
#    glBindTexture(GL_TEXTURE_2D, 0)

def key_callback(window, key, scancode, action, mods):
    global distortions_enabled
    if key == glfw.KEY_D and action == glfw.PRESS:
        distortions_enabled = not distortions_enabled
        print(f"Distortions {'enabled' if distortions_enabled else 'disabled'}")

def init(args, **kwargs):
    return True

def access(args, op, **kwargs):
    return True

def buildargs(args, **kwargs):
    return None

def main(args, **kwargs):
    modules = []
    for mod_name in MODULE_NAMES:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"main.100: {e}")
        else:
            modules.append(mod)

    # Setup MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False,
                           max_num_hands=2,
                           min_detection_confidence=0.5,
                           min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        context = {}

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                h, w, _ = frame.shape
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                context["left_index_tip"] = (int(index_tip.x * w), int(index_tip.y * h))
                break  # Just use the first detected hand for simplicity

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
