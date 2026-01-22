import customtkinter as ctk
import sys
import os
import json
import base64
import socket

# Đường dẫn import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.login_window import LoginWindow
from ui.chat_window import ChatAppClient
from core.protocol import Protocol # Import ở đây để tránh circular

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("ChatApp Enterprise - Zalo Clone")
        self.geometry("1000x650")
        self.resizable(True, True)

        # Container chứa các màn hình (Frame)
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        
        # Dictionary lưu trạng thái username/socket khi chuyển màn hình
        self.session_data = {
            "username": None,
            "socket": None,
            "email": None,
            "password": None
        }
        self.session_file = "session.json"

        self.check_auto_login()

    def check_auto_login(self):
        """Kiểm tra file session để tự động đăng nhập"""
        if not os.path.exists(self.session_file):
            self.show_login()
            return

        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
            
            email = data.get("email")
            encoded_pass = data.get("password")

            if not email or not encoded_pass:
                self.show_login()
                return

            password = base64.b64decode(encoded_pass).decode()

            # Thử kết nối và đăng nhập tự động
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Create SSL Context
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            sock = context.wrap_socket(raw_sock, server_hostname='localhost')
            sock.connect(('127.0.0.1', 65432)) # Cần config host/port
            
            cmd = f"AUTH|LOGIN|{email}|{password}"
            sock.sendall(Protocol.pack(cmd))
            
            response = Protocol.recv_msg_sync(sock)
            if response and response.startswith("AUTH|SUCCESS|"):
                parts = response.split("|")
                username = parts[3]
                self.on_login_success(username, sock, email, password)
            else:
                # Nếu auto-login thất bại, hiện màn hình login bình thường
                self.show_login()

        except Exception as e:
            print(f"Lỗi tự động đăng nhập: {e}")
            self.show_login()


    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_container()
        self.geometry("1000x650") # Reset size cho login
        
        # LoginWindow giờ là Frame
        login_screen = LoginWindow(master=self.container, on_login_success=self.on_login_success)
        login_screen.pack(fill="both", expand=True)

    def on_login_success(self, username, sock, email, password):
        self.session_data["username"] = username
        self.session_data["socket"] = sock
        self.session_data["email"] = email
        self.session_data["password"] = password
        
        print(f"[SYSTEM] Đăng nhập thành công: {username}")
        self.show_chat()

    def show_chat(self):
        self.clear_container()
        self.geometry("1100x700") # Resize lớn hơn cho chat
        self.minsize(950, 600)
        
        chat_screen = ChatAppClient(
            master=self.container,
            username_from_login=self.session_data["username"],
            existing_socket=self.session_data["socket"],
            on_logout_callback=self.on_logout,
            email=self.session_data["email"],
            password=self.session_data["password"]
        )
        chat_screen.pack(fill="both", expand=True)

    def on_logout(self):
        print(f"[SYSTEM] Đăng xuất: {self.session_data['username']}")
        # Đóng socket cũ
        if self.session_data["socket"]:
            try: self.session_data["socket"].close()
            except: pass
        
        # Xóa file session khi đăng xuất
        if os.path.exists(self.session_file):
            os.remove(self.session_file)

        self.session_data = {"username": None, "socket": None}
        self.show_login()

    def on_close(self):
        print("[MAIN] Closing application...")
        # Đóng socket nếu có
        sock = self.session_data.get("socket")
        if sock:
            try: sock.close()
            except: pass
        self.destroy()
        print("[MAIN] Application destroyed.")

if __name__ == "__main__":
    try:
        app = MainApp()
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        app.mainloop()
    except Exception as e:
        print(f"\n[FATAL CRASH] {e}")
        import traceback
        traceback.print_exc()
        import time
        time.sleep(10) # Dừng lại để xem lỗi