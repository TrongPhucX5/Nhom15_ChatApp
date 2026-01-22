import socket
import ssl
import threading

def ssl_client(i):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    s = ctx.wrap_socket(socket.socket(), server_hostname="localhost")
    s.connect(("127.0.0.1", 65432))
    print(f"[CLIENT {i}] SSL connected")
    s.close()

threads = []

for i in range(50):
    t = threading.Thread(target=ssl_client, args=(i,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("DONE")
