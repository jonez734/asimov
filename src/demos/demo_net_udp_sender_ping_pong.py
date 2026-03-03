# demo_net_udp_sender_ping_pong.py

import argparse
import time

from asimov import io
from asimov.net import UDPSender


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP PING Sender")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Target host")
    parser.add_argument("--port", type=int, default=5000, help="Target port")
    parser.add_argument("--bind-port", type=int, default=0, help="Local bind port")
    parser.add_argument("--count", type=int, default=3, help="Number of PING packets")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval between PINGs")
    args = parser.parse_args()

    io.echo(f"Sending to {args.host}:{args.port}")

    sender = UDPSender(args.host, args.port, args.bind_port)
    try:
        for i in range(1, args.count + 1):
            sender.send_ping()
            io.echo(f"Sent PING {i}/{args.count}")
            if i < args.count:
                time.sleep(args.interval)
        io.echo("done")
    except KeyboardInterrupt:
        io.echo("\nStopped by user.")
    finally:
        sender.close()
