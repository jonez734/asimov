# receive_frame_demo Specification

## Overview

`receive_frame_demo` demonstrates receiving cv2 video frames over UDP using asimov's frame transmission system with automatic reassembly and delta reconstruction.

## Usage

```bash
python receive_frame_demo.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--host` | str | "0.0.0.0" | Host to bind to |
| `--port` | int | 5000 | Port to listen on |
| `--blocking` | flag | False | Use blocking mode |
| `--timeout` | float | 1.0 | Receive timeout (seconds) |

## Features

- Automatic frame reassembly from chunks
- Delta frame reconstruction (applies changes to previous frame)
- Non-square block support (cols x rows grid)
- Displays received frames with cv2.imshow

## Behavior

1. Creates UDPReceiver on specified host:port
2. Receives packets in non-blocking mode
3. Reassembles complete frames from chunks
4. For delta frames: applies changes to previous frame
5. Displays frame when complete
6. Press 'q' to quit

## Frame Reception Flow

1. Receive packet with `receiver.receive()`
2. Packet contains: frame_id, cols, rows, block_w, block_h, is_delta, blocks
3. Store blocks in buffer
4. When all blocks received (total_blocks reached):
   - If is_delta: apply changes to previous frame
   - Otherwise: assemble new frame from all blocks
5. Call frame_received_callback if set

## Exit

- Press 'q' to quit
- Cleanup: closes socket, destroys windows
