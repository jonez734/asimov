import socket
from asimov import net

def udp_responder(host='127.0.0.1', port=5000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"Listening for PING on {host}:{port}")

    while True:
        data, addr = sock.recvfrom(65536)
        packet = net.decode_packet(data)
        if packet.get('packet_type') == net.PACKET_TYPE_PING:
            print(f"Received PING from {addr}, sending PONG")
            pong_packet = {'packet_type': net.PACKET_TYPE_PONG}
            sock.sendto(net.encode_packet(pong_packet), addr)

if __name__ == "__main__":
    udp_responder()
