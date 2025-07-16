# test_receive_and_respond.py
import threading

from bbsengine6 import io
from asimov import net

def main(args=None, **kwargs):
    receiver = net.UDPReceiver("127.0.0.1", 5000, blocking=False)

    # Set up sender and send a PING
    sender = net.UDPSender("127.0.0.1", 5000, local_port=5001)
    for attempt in range(2):
        print(f"[test_receive_amd_respond] sending PING. {attempt=}")
        sender.send_ping()
        packet = receiver.receive()
        if packet[0] == net.PACKET_TYPE_PING:
            print(f"[test_receive_and_respond] PING {packet=}")
            addr = packet[5]
            print(f"{addr=}")
            net.respond_to_ping(addr)

    sender.close()
    receiver.close()
    return True

if __name__ == "__main__":
    main()
