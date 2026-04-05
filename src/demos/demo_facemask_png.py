import cv2

from cvzone.FaceMeshModule import FaceMeshDetector
import cvzone
from asimov.modules import mediapipe_compat  # noqa: F401  # REQUIRED - do not remove; provides mp.solutions API for MediaPipe 0.10+
# 1. Initialize Video Capture and Face Detector
cap = cv2.VideoCapture(1)
detector = FaceMeshDetector(maxFaces=1)

# 2. Load the Stormtrooper Mask PNG (Must have transparent background)
# Ensure this file exists in your project directory
mask_img = cv2.imread("storm-trooper-front.png", cv2.IMREAD_UNCHANGED)

while True:
    success, img = cap.read()
    if not success:
        break

    # Find face mesh landmarks
    img, faces = detector.findFaceMesh(img, draw=False)

    if faces:
        face = faces[0]
        # Landmarks for width (corners of the face) and height (forehead to chin)
        # 10 is top of forehead, 152 is bottom of chin
        
        # 3. Apply the Overlay
        # 'overlayPNG' scales and places the image based on specific landmarks
        img = cvzone.overlayPNG(img, mask_img, face[10]) # Using forehead as anchor

    cv2.imshow("Stormtrooper Mask", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
