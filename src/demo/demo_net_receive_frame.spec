# demo_net_receive_frame Specification

## Overview

`demo_net_receive_frame` demonstrates receiving cv2 video frames over UDP/TCP using asimov's frame transmission system with automatic reassembly and delta reconstruction.

## Usage

```bash
python demo_net_receive_frame.py [options]
```

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--protocol` | str | "udp" | Protocol to use (tcp or udp) |
| `--host` | str | "127.0.0.1" | Host to bind to |
| `--port` | int | 5000 | Port to listen on |
| `--max-idle` | int | 5 | Max seconds of no data before exiting |
| `--wait` | flag | False | Wait forever for new data (for sender restarts) |

## Features

- Automatic frame reassembly from chunks
- Delta frame reconstruction (applies changes to previous frame)
- Non-square block support (cols x rows grid)
- Displays received frames with cv2.imshow
- Two modes: exit after idle timeout or wait forever

## Behavior

### Default Mode (no --wait)

1. Creates UDPReceiver/TCPReceiver on specified host:port
2. Receives packets with blocking socket (1s timeout)
3. Reassembles complete frames from chunks
4. For delta frames: applies changes to previous frame
5. Displays frame when complete
6. After 5 seconds of no data, exits with "No data received, exiting..."
7. Press ESC to quit early

### Wait Mode (--wait)

1. Creates receiver with non-blocking socket
2. Loops continuously checking for data
3. Uses cv2.waitKey(1) to process window events (1000fps loop)
4. When sender exits: continues waiting (doesn't exit)
5. When new sender starts: accepts new connection and receives frames
6. Press ESC to quit

## Exit

- Default mode: exits after --max-idle seconds of no data, or ESC
- Wait mode: ESC to quit
- Cleanup: closes socket, destroys windows
