# asimov/conf.py

import math

# --- Configuration ---
CAP_WIDTH = 640  # Static width
CAP_HEIGHT = 480 # Static height
CAP_DEVICE = 0

FRAME_DEPTH = 3

FPS = 30 # Target FPS for capture

DISPLAY_WIDTH = 1024 # Can be different from CAP_WIDTH/HEIGHT, best to use powers of 2
DISPLAY_HEIGHT = 768
CHUNKSIZE = math.gcd(DISPLAY_WIDTH, DISPLAY_HEIGHT) # 256

# --- UDP Specifics ---
CNC_HOST = "127.0.0.1"
CNC_PORT = 4200

CAP_HOST = "127.0.0.1" # Localhost
CAP_PORT = 4210

PROCESSING_HOST = '127.0.0.1'
PROCESSING_PORT = 4220

#RENDER_PORT = 4202
#RENDER_HOST = '127.0.0.1'

# UDP_PORT = 4200        # Port for capture -> processing communication

