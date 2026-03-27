# tcp_look_demo.py
import socket
import threading
import time

from asimov.net import send_with_length, recv_with_length

# Local definition of packet types (we're not touching net.py)
PACKET_TYPE_LOOK = b"LOOK"

# Some long Lorem Ipsum text (>4096 bytes)
IPSUM_TEXT = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50
    + "\n\n"
    + "Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; "
    * 50
    + "\n\n"
    + "Curabitur non nulla sit amet nisl tempus convallis quis ac lectus. " * 50
    + "\n\n"
    + "Proin eget tortor risus. Cras ultricies ligula sed magna dictum porta. " * 50
    + "\n\n"
).encode("utf-8")


def handle_client(conn, addr):
    print(f"[SERVER] Connection from {addr}")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            if data.startswith(PACKET_TYPE_LOOK):
                print("[SERVER] Got LOOK request")
                # Send the big text
                send_with_length(conn, IPSUM_TEXT)
    except Exception as e:
        print(f"[SERVER] Error: {e}")
    finally:
        conn.close()
        print(f"[SERVER] Closed connection {addr}")


def server_thread(host="127.0.0.1", port=9009):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        print(f"[SERVER] Listening on {host}:{port}")
        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            ).start()


def client_thread(host="127.0.0.1", port=9009):
    time.sleep(1)  # give server time
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("[CLIENT] Connected to server")

        # Send LOOK request
        s.sendall(PACKET_TYPE_LOOK)
        print("[CLIENT] Sent LOOK")

        # Receive framed response
        response = recv_with_length(s)
        print(f"[CLIENT] Got response of {len(response)} bytes")
        print(response[:500].decode("utf-8") + "\n... [truncated] ...")


if __name__ == "__main__":
    # Start server in background
    threading.Thread(target=server_thread, daemon=True).start()

    # Run client
    client_thread()
