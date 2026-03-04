"""
Mediapipe compatibility shim to provide the old 'solutions' API
using the new MediaPipe Tasks API.

This shim allows code written for mediapipe < 0.10 (using mp.solutions)
to work with mediapipe 0.10+ which uses the Tasks API.

Usage:
    import sys
    sys.path.insert(0, '.')
    import mediapipe_compat
    
    # Now mp.solutions is available
    import mediapipe as mp
    hands = mp.solutions.hands.Hands(...)
"""
import os
import cv2

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Get the mediapipe models directory
MEDIAPIPE_MODELS_DIR = os.path.join(os.path.dirname(mp.__file__), 'models')


def _check_model_exists(model_path: str) -> None:
    """Check if model file exists, raise helpful error if not."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"MediaPipe model not found: {model_path}\n"
            "Download models from:\n"
            "  hand: https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task\n"
            "  face: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task\n"
            f"Place in: {MEDIAPIPE_MODELS_DIR}/"
        )


class _Hands:
    """Compatibility class for mp.solutions.hands"""
    
    def Hands(self, static_image_mode=False, max_num_hands=2, model_complexity=1,
              min_detection_confidence=0.5, min_tracking_confidence=0.5):
        """Create a Hands detector - compatible with old API"""
        model_path = os.path.join(MEDIAPIPE_MODELS_DIR, 'hand_landmarker.task')
        _check_model_exists(model_path)
        
        # Use IMAGE mode for static_image_mode=True, VIDEO otherwise
        running_mode = vision.RunningMode.IMAGE if static_image_mode else vision.RunningMode.VIDEO
        
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_path),
            running_mode=running_mode,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence)
        return _HandsDetector(options, static_image_mode)


class _HandsDetector:
    """Compatibility class for the hands detector"""
    
    def __init__(self, options, static_image_mode=False):
        self._detector = vision.HandLandmarker.create_from_options(options)
        self._options = options
        self._static_image_mode = static_image_mode
    
    def process(self, frame_rgb):
        """Process a frame - compatible with old API"""
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        # Use detect for IMAGE mode, detect_for_video for VIDEO mode
        if self._static_image_mode:
            result = self._detector.detect(image)
        else:
            # For VIDEO mode, we need timestamp - use 0 for simplicity
            result = self._detector.detect_for_video(image, int(cv2.getTickCount() / cv2.getTickFrequency() * 1000))
        
        class Results:
            def __init__(self, result):
                self.multi_hand_landmarks = []
                self.multi_handedness = []
                
                if result and result.hand_landmarks:
                    for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                        # Convert to old format
                        class Landmark:
                            def __init__(self, x, y, z):
                                self.x = x
                                self.y = y
                                self.z = z
                        
                        self.multi_hand_landmarks.append(
                            type('HandLandmarks', (), 
                                 {'landmark': [Landmark(lm.x, lm.y, lm.z) for lm in hand_landmarks]})()
                        )
                        
                        # Handedness
                        class Classification:
                            def __init__(self, label, score):
                                self.label = label
                                self.score = score
                        
                        self.multi_handedness.append(
                            type('Handedness', (),
                                 {'classification': [Classification(h.category_name, h.score) for h in handedness]})()
                        )
        
        return Results(result)
    
    def close(self):
        self._detector.close()


class _DrawingUtils:
    """Compatibility class for mp.solutions.drawing_utils"""
    
    @staticmethod
    def DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=2):
        return type('DrawingSpec', (), {'color': color, 'thickness': thickness, 'circle_radius': circle_radius})()
    
    @staticmethod
    def draw_landmarks(image, landmark_list, connections=None, landmark_drawing_spec=None, connection_drawing_spec=None):
        # Not implementing drawing for compatibility - cvzone draws its own
        return image


class _FaceMesh:
    """Compatibility class for mp.solutions.face_mesh"""
    
    def FaceMesh(self, static_image_mode=False, max_num_faces=1, refine_landmarks=False,
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        model_path = os.path.join(MEDIAPIPE_MODELS_DIR, 'face_landmarker.task')
        _check_model_exists(model_path)
        
        # Use IMAGE mode for static_image_mode=True, VIDEO otherwise
        running_mode = vision.RunningMode.IMAGE if static_image_mode else vision.RunningMode.VIDEO
        
        options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_path),
            running_mode=running_mode,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False)
        return _FaceMeshDetector(options, static_image_mode)


class _FaceMeshDetector:
    """Compatibility class for the face mesh detector"""
    
    def __init__(self, options, static_image_mode=False):
        self._detector = vision.FaceLandmarker.create_from_options(options)
        self._options = options
        self._static_image_mode = static_image_mode
    
    def process(self, frame):
        # Handle both RGB and BGR frames
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            # Convert BGR to RGB if needed (assuming BGR from OpenCV)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
            
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        # Use detect for IMAGE mode, detect_for_video for VIDEO mode
        if self._static_image_mode:
            result = self._detector.detect(image)
        else:
            result = self._detector.detect_for_video(image, int(cv2.getTickCount() / cv2.getTickFrequency() * 1000))
        
        class Results:
            def __init__(self, result):
                self.multi_face_landmarks = []
                
                if result and result.face_landmarks:
                    for face_landmarks in result.face_landmarks:
                        class Landmark:
                            def __init__(self, x, y, z):
                                self.x = x
                                self.y = y
                                self.z = z
                        
                        self.multi_face_landmarks.append(
                            type('FaceLandmarks', (),
                                 {'landmark': [Landmark(lm.x, lm.y, lm.z) for lm in face_landmarks]})()
                        )
        
        return Results(result)
    
    def close(self):
        self._detector.close()


# Add the solutions module to mediapipe
class _Solutions:
    hands = _Hands()
    drawing_utils = _DrawingUtils()
    face_mesh = _FaceMesh()

mp.solutions = _Solutions()
