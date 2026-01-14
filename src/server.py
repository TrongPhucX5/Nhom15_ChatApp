import socket
import threading

def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(1024)
            if not message:
                break
            print(f"Received message: {message.decode('utf-8')}")
            # Broadcast the message to all other clients
            for client in clients:
                if client != client_socket:
                    client.send(message)
        except:
            break
    client_socket.close()

clients = []
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 5555))
server.listen(5)
print("Server listening on port 5555")

while True:
    client_socket, addr = server.accept()
    print(f"Accepted connection from {addr}")
    clients.append(client_socket)
    thread = threading.Thread(target=handle_client, args=(client_socket,))
    thread.start()
