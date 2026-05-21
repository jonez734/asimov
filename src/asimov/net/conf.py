# asimov/net/conf.py
# Network configuration for frame transmission

# Import asimov-specific capture configuration
from asimov import conf

CAPTURE_CONF = conf.CONF["CAPTURE"]
CAPTURE_WIDTH = CAPTURE_CONF["WIDTH"]
CAPTURE_HEIGHT = CAPTURE_CONF["HEIGHT"]
CAPTURE_FPS = CAPTURE_CONF["FPS"]
CAPTURE_DEVICE = CAPTURE_CONF["DEVICE"]

# Frame transmission constants
CHUNK_SIZE = 64
DEFAULT_PORT = 5000
COMPRESSION_ENABLED = False
BUFFER_SIZE = 65507

# Service endpoints (video capture, processing, rendering)
VIDEOCAPTURE_HOST = "127.0.0.1"
VIDEOCAPTURE_PORT = 5000
PROCESSING_HOST = "127.0.0.1"
PROCESSING_PORT = 6000
RENDER_HOST = "127.0.0.1"
RENDER_PORT = 6000

# Buffer sizes
TCP_BUFFER_SIZE = 8192
UDP_BUFFER_SIZE = 65507

# Retry configuration
RETRY_DELAY = 0.2
RETRY_COUNT = 5
