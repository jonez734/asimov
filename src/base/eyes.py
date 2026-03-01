import cv2
import mediapipe as mp
import numpy as np

from . import conf

__all__ = ["draw", "detect"]

# Eye landmark indices
LEFT_EYE_IDX = [33, 133, 159, 145, 160, 158, 153, 144]
RIGHT_EYE_IDX = [362, 263, 386, 374, 385, 380, 373, 390]

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.4, min_tracking_confidence=0.5)

def detect(frame, context):
    context["face_mesh_processed"] = face_mesh.process(frame)
    return

def draw(frame, context):
    results = context.get("face_mesh_processed")
    if results is None:
        return frame

    if results.multi_face_landmarks:
#        logentry(f"checking eye landmarks")
        for face_landmarks in results.multi_face_landmarks:
            ih, iw, _ = frame.shape

            # Get eye coordinates
            left_eye_points = [(int(face_landmarks.landmark[i].x * iw), int(face_landmarks.landmark[i].y * ih)) for i in LEFT_EYE_IDX]
            right_eye_points = [(int(face_landmarks.landmark[i].x * iw), int(face_landmarks.landmark[i].y * ih)) for i in RIGHT_EYE_IDX]

            # Combine all eye points
            all_eye_points = left_eye_points + right_eye_points
            all_eye_points_np = np.array(all_eye_points)

            # Get bounding rectangle around both eyes
            x, y, w, h = cv2.boundingRect(all_eye_points_np)

            # Make the rectangle a bit taller to give that "witness protection" look
            y -= int(0.2 * h)
            h += int(0.4 * h)

            # Draw the blue rectangle (privacy bar)
            cv2.rectangle(frame, (x, y), (x + w, y + h), conf.PRIVACY_EYES_COLOR, thickness=-1)
    return frame
