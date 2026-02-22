import time
from asimov import net

PACKET_TYPE_PING = net.PACKET_TYPE_PING
PACKET_TYPE_PONG = net.PACKET_TYPE_PONG

def send_ping_and_wait_for_pong(dest_host, dest_port,
                               local_host="127.0.0.1", local_port=5001,
                               timeout=1.0, retries=50):

    # Create receiver bound locally on local_host:local_port
    receiver = net.UDPReceiver(local_host, local_port)

    # Create sender - no local port needed here usually, addr is remote
    sender = net.UDPSender(dest_host, dest_port, local_port=local_port)
    
    # Optional: inject sender instance to receiver for ping responses, if used
    # receiver.sender = sender  # Uncomment if needed by your code

    print(f"receiver: {local_host=} {local_port=} sender: {dest_host=} {dest_port=}")

    ping_packet = {'packet_type': PACKET_TYPE_PING}
    data = net.encode_packet(ping_packet)

    for attempt in range(1, retries + 1):
        print(f"[ping] Sending PING to {dest_host}:{dest_port} (attempt {attempt})")
        sender.send(data)

        start_time = time.time()
        while time.time() - start_time < timeout:
            packet, addr = receiver.receive()
            print(f"[send_ping_and_wait_for_pong] {packet=} {addr=}")
            if packet is None:
                time.sleep(0.01)
                continue

            if packet.get('packet_type') == PACKET_TYPE_PONG:
                print(f"[pong] Received PONG from {addr}")
                sender.close()
                receiver.close()
                return True
            else:
                print(f"[warn] Unexpected packet from {addr}: {packet=}")

        print("[timeout] No response, retrying...")

    print("[fail] No PONG received.")
    sender.close()
    receiver.close()
    return False

if __name__ == "__main__":
    success = send_ping_and_wait_for_pong("127.0.0.1", 5000, local_host="127.0.0.1", local_port=5001)
    print("Success:", success)
