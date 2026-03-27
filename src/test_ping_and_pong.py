import time

from asimov.net import UDPSender, UDPReceiver
from asimov.net import PACKET_TYPE_PING


def wait_for_pong(sender, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = sender.receive()
        if result:
            return result
        time.sleep(0.01)
    return None


def test_ping_and_pong():
    receiver = UDPReceiver("127.0.0.1", 5000, local_port=5001, blocking=True)
    sender = UDPSender("127.0.0.1", 5000, blocking=False)
    sender.send_ping()
    data = receiver.receive()
    if data["packet_type"] == PACKET_TYPE_PING:
        print("[test] received PING")
        sender.send_pong()

    print(f"{data=}")

    #  receiver.close()
    sender.close()


if __name__ == "__main__":
    test_ping_and_pong()
