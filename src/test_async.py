import socket
import sys
import os
import time

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.protocol import Protocol

HOST = '127.0.0.1'
PORT = 65432

def test_protocol():
    print("[TEST] Connecting to server...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("[FAIL] Cannot connect to server. Is it running?")
        return

    print("[TEST] Sending LOGIN...")
    # Use Protocol.pack
    login_msg = Protocol.pack("LOGIN|TesterBot")
    sock.sendall(login_msg)

    print("[TEST] Waiting for User List...")
    # Use Protocol.recv_msg_sync
    response = Protocol.recv_msg_sync(sock)
    print(f"[RECV] {response}")

    if not response or not response.startswith("LIST|"):
        print("[FAIL] Did not receive LIST or invalid protocol.")
        sock.close()
        return

    print("[TEST] Sending Chat Message...")
    msg = Protocol.pack("MSG|Hello Async World")
    sock.sendall(msg)
    
    # We might not receive our own message back depending on logic (exclude_sender?)
    # Server logic: broadcast(..., exclude_writer=writer) -> We WON'T see our own msg.
    # So we are done here if no crash.
    
    print("[PASS] Test Finished Successfully.")
    sock.close()

if __name__ == "__main__":
    test_protocol()
