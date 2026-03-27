import cv2
from cvzone.FaceMeshModule import FaceMeshDetector
import numpy as np

from . import conf

__all__ = ["draw", "detect"]

# Eye landmark indices
LEFT_EYE_IDX = [33, 133, 159, 145, 160, 158, 153, 144]
RIGHT_EYE_IDX = [362, 263, 386, 374, 385, 380, 373, 390]

# Initialize cvzone FaceMeshDetector
face_detector = FaceMeshDetector(maxFaces=1)


def detect(frame, context):
    frame, faces = face_detector.findFaceMesh(frame, draw=False)
    context["faces"] = faces
    return


def draw(frame, context):
    faces = context.get("faces")
    if faces is None:
        return frame

    if faces:
        for face in faces:
            # face[0] is bounding box [x, y, w, h], face[1:] are landmarks
            face_landmarks = face[1:]

            # Get eye coordinates
            left_eye_points = [
                (int(face_landmarks[i][0]), int(face_landmarks[i][1]))
                for i in LEFT_EYE_IDX
            ]
            right_eye_points = [
                (int(face_landmarks[i][0]), int(face_landmarks[i][1]))
                for i in RIGHT_EYE_IDX
            ]

            # Combine all eye points
            all_eye_points = left_eye_points + right_eye_points
            all_eye_points_np = np.array(all_eye_points)

            # Get bounding rectangle around both eyes
            x, y, w, h = cv2.boundingRect(all_eye_points_np)

            # Make the rectangle a bit taller to give that "witness protection" look
            y -= int(0.2 * h)
            h += int(0.4 * h)

            # Draw the blue rectangle (privacy bar)
            cv2.rectangle(
                frame, (x, y), (x + w, y + h), conf.PRIVACY_EYES_COLOR, thickness=-1
            )
    return frame
