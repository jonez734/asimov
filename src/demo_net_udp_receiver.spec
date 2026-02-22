# demo_udp_receiver Specification

## Overview

`demo_udp_receiver` demonstrates receiving UDP frames with callback-based processing using `start_listening()`.

## Usage

```bash
python demo_udp_receiver.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--host` | str | "0.0.0.0" | Host to bind to |
| `--port` | int | 5000 | Port to listen on |

## Features

- Callback-based frame handling
- `start_listening()` loop with idle callback
- Automatic frame reassembly
- Delta frame reconstruction

## Callbacks

### frame_received_callback(frame, frame_id)

Called when a complete frame is received.

```python
def handle_complete_frame(frame: np.ndarray, frame_id: int):
    cv2.imshow("cap", frame)
```

### idle_callback()

Called between receive attempts. Return False to stop listening.

```python
def idle_callback():
    ch = cv2.pollKey() & 0xFF
    if ch == 27 or ch == ord('q'):
        return False
    return True
```

## Behavior

1. Creates UDPReceiver on specified host:port
2. Sets up frame and idle callbacks
3. Calls `start_listening()` which:
   - Loops calling `receive()` 
   - Calls frame_received_callback on complete frames
   - Calls idle_callback between receives
4. Runs until idle_callback returns False

## Exit

- ESC or 'q' key via idle_callback
- Cleanup: closes socket, destroys windows
