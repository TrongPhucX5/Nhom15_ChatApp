import socket
import threading
import sys
import os

# --- 1. Tự động thêm đường dẫn để tìm file Database ---
# (Giúp tránh lỗi ModuleNotFoundError khi file nằm lộn xộn)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- 2. Import Database an toàn ---
# (Nếu chưa tạo file firebase_db.py, server vẫn chạy bình thường)
try:
    from database.firebase_db import DBHandler
    has_db = True
    print(" [SERVER] Đã kết nối module Database.")
except ImportError:
    print(" [SERVER] Cảnh báo: Không tìm thấy file 'database/firebase_db.py'.")
    print("   -> Server sẽ chạy ở chế độ KHÔNG LƯU TIN NHẮN.")
    has_db = False

HOST = '127.0.0.1'
PORT = 65432

class ChatServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # [QUAN TRỌNG] Cho phép dùng lại cổng ngay lập tức sau khi tắt
        # Giúp sửa lỗi "Address already in use"
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server.bind((HOST, PORT))
            self.server.listen()
            print(f" [SERVER] Đang chạy tại {HOST}:{PORT}")
        except OSError:
            print(f" [SERVER] Lỗi: Cổng {PORT} đang bận! (Có thể server đã chạy rồi)")

        self.clients = {} # Lưu {socket: username}
        
        # Chỉ khởi tạo DB nếu import thành công
        self.db = DBHandler() if has_db else None

    def broadcast_user_list(self):
        """Gửi danh sách online cho mọi người"""
        users = list(self.clients.values())
        msg = "LIST|" + ",".join(users)
        for c in self.clients:
            try: c.send(msg.encode('utf-8'))
            except: pass

    def handle_client(self, client, addr):
        username = "Unknown"
        try:
            # Nhận tin nhắn đầu tiên (LOGIN)
            first_msg = client.recv(1024).decode('utf-8')
            if first_msg.startswith("LOGIN|"):
                username = first_msg.split("|")[1]
                self.clients[client] = username
                print(f" [NEW] {username} đã kết nối.")
                
                # Lưu log vào Firebase (nếu có)
                if self.db: self.db.log_user(username)
                
                self.broadcast_user_list()
            
            # Vòng lặp Chat
            while True:
                msg = client.recv(1024).decode('utf-8')
                if not msg: break
                
                if msg.startswith("MSG|"):
                    # Cấu trúc: MSG|Nội dung
                    content = msg.split("|")[1]
                    print(f"💬 [{username}]: {content}")
                    
                    # Lưu tin nhắn (nếu có DB)
                    if self.db: self.db.save_message(username, content)
                    
                    # Gửi cho người khác
                    response = f"MSG|{username}|{content}"
                    for c in self.clients:
                        if c != client:
                            try: c.send(response.encode('utf-8'))
                            except: pass
        except:
            pass # Client ngắt kết nối đột ngột
        
        # Dọn dẹp khi client thoát
        if client in self.clients:
            print(f"jf [EXIT] {username} đã thoát.")
            del self.clients[client]
            client.close()
            self.broadcast_user_list()

    def start(self):
        # Lắng nghe kết nối mới
        while True:
            try:
                client, addr = self.server.accept()
                t = threading.Thread(target=self.handle_client, args=(client, addr))
                t.daemon = True # Thread tự tắt khi chương trình chính tắt
                t.start()
            except OSError:
                break # Server bị đóng

if __name__ == "__main__":
    server = ChatServer()
    server.start()