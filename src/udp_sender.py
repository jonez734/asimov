# udp_sender.py
import socket
import argparse
import time
from asimov.net import encode_packet, decode_packet, PING, PONG, NetError, UDPSender

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP PING Sender")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="The target host to send PINGs to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000,
                        help="The target port to send PINGs to (default: 5000)")
    parser.add_argument("--bind_port", type=int, default=0,
                        help="The local port to bind to (0 for OS-assigned, default: 0)")
    parser.add_argument("--count", type=int, default=3,
                        help="Number of PING packets to send (default: 3)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Time in seconds between PINGs (default: 1.0)")

    args = parser.parse_args()

    sender = UDPSender(args.host, args.port, args.bind_port)
    try:
        for i in range(1, args.count + 1):
            sender.send_ping(i)
            sender.listen_for_response()
            if i < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSender stopped by user.")
    finally:
        sender.close()
