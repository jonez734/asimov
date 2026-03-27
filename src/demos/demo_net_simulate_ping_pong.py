import threading

from asimov.net import (
    UDPReceiver,
    UDPSender,
    send_ping_and_wait_for_pong,
    PACKET_TYPE_PING,
)


def receive_and_respond(receiver: UDPReceiver):
    """
    Continuously receive packets and respond to PINGs with PONGs.
    This will exit after handling one PING (for test purposes).
    """
    while True:
        packet_type, frame_id, payload = receiver.receive()
        if packet_type == PACKET_TYPE_PING:
            print("Receiver: handled PING")
            break


def test_ping_and_pong():
    # Set up receiver using your UDPReceiver class
    receiver = UDPReceiver(port=5000, bind_ip="127.0.0.1", packetsize=1500)

    # Start receiver logic in a background thread
    responder = threading.Thread(target=receive_and_respond, args=(receiver,))
    responder.start()

    # Set up sender and send a PING
    sender = UDPSender("127.0.0.1", 5000)
    print("Sender: sending PING...")

    if send_ping_and_wait_for_pong(sender, timeout=1.0, retry=1):
        print("✅ PONG received")
    else:
        print("❌ No PONG received")

    sender.close()
    receiver.close()
    responder.join()


if __name__ == "__main__":
    test_ping_and_pong()
