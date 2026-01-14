import socket
import threading
import sys
import os

# Thêm đường dẫn hiện tại vào path để import được các module trong folder con
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import từ thư mục database (package)
from database.firebase_db import DBHandler

HOST = '127.0.0.1'
PORT = 65432

class ChatServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((HOST, PORT))
        self.server.listen()
        
        self.clients = {} # Dictionary lưu {client_socket: username}
        self.db = DBHandler()
        print(f"[SERVER] ChatApp Server đang chạy tại {HOST}:{PORT}")

    def broadcast_user_list(self):
        """Gửi danh sách user online cho tất cả mọi người"""
        users = list(self.clients.values())
        user_list_str = "LIST|" + ",".join(users)
        for client in self.clients:
            try:
                client.send(user_list_str.encode('utf-8'))
            except:
                pass

    def handle_client(self, client, addr):
        username = ""
        try:
            # Bước 1: Nhận tin nhắn đăng nhập
            login_msg = client.recv(1024).decode('utf-8')
            if login_msg.startswith("LOGIN|"):
                username = login_msg.split("|")[1]
                self.clients[client] = username
                
                # Lưu vào Firebase
                self.db.log_user(username)
                print(f"[NEW] {username} đã tham gia.")
                self.broadcast_user_list()
            
            # Bước 2: Chat loop
            while True:
                msg = client.recv(1024).decode('utf-8')
                if msg.startswith("MSG|"):
                    content = msg.split("|")[1]
                    print(f"[{username}] {content}")
                    
                    self.db.save_message(username, content)
                    
                    response = f"MSG|{username}|{content}"
                    for c in self.clients:
                        if c != client:
                            c.send(response.encode('utf-8'))
                else:
                    break
        except:
            pass
        
        if client in self.clients:
            print(f"[EXIT] {username} thoát.")
            del self.clients[client]
            client.close()
            self.broadcast_user_list()

    def start(self):
        while True:
            client, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(client, addr))
            thread.start()

if __name__ == "__main__":
    ChatServer().start()