# asimov/conf.py

# --- Configuration ---
CAP_WIDTH = 640  # Static width
CAP_HEIGHT = 480 # Static height
CAP_FPS = 30
CAP_DEVICE = 0

# pyvirtualcam
CAM_LABEL = "asimov.cam0"

FRAME_DEPTH = 3

FPS = 30 # Target FPS for capture

DISPLAY_WIDTH = 1024 # Can be different from CAP_WIDTH/HEIGHT, best to use powers of 2
DISPLAY_HEIGHT = 768

# --- UDP Specifics ---
RECEIVER_HOST = '127.0.0.1'
RECEIVER_PORT = 5000

#RENDER_PORT = 4202
#RENDER_HOST = '127.0.0.1'

FINGERTIP_COLOR = (0, 255, 255) # yellow BGR
FINGERTIP_CIRCLE_RADIUS = 8

RECT_BORDER_COLOR_TOUCHED = (0, 255, 0) # green
RECT_BORDER_COLOR = (255, 0, 0) # blue
RECT_BORDER_THICKNESS = 2
RECT_TOUCH_MARGIN = 0

# Default timeout (seconds) and tolerance (fraction of size)
DEFAULT_RECT_TIMEOUT = 0.5
MERGE_TOLERANCE_RATIO = 0.2  # 20% of rectangle diagonal

WATERMARK_COLOR = (255, 255, 255)

PRIVACY_EYES_COLOR = (255, 0, 0)

TITLE = "Project Asimov v202509.0"
