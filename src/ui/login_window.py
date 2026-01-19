import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
import os
import sys
import socket

# Thêm đường dẫn để import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.protocol import Protocol
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from core.protocol import Protocol

# --- CẤU HÌNH GIAO DIỆN CHUNG ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

HOST = '127.0.0.1'
PORT = 65432

class LoginWindow(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master)
        self.on_login_success = on_login_success
        self.sock = None
        self.username = None

        # --- ĐƯỜNG DẪN ẢNH ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(base_dir, '../../assets')

        # Xây dựng giao diện ngay trên frame này
        self.build_ui()

    def build_ui(self):
        # --- CỘT TRÁI (LOGO) ---
        self.left_frame = ctk.CTkFrame(self, width=400, corner_radius=0, fg_color="#0068ff")
        self.left_frame.pack(side="left", fill="both")
        
        ctk.CTkLabel(self.left_frame, text="💬", font=("Segoe UI Emoji", 80), text_color="white").place(relx=0.5, rely=0.35, anchor="center")
        ctk.CTkLabel(self.left_frame, text="ChatApp", font=("Segoe UI", 36, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self.left_frame, text="An toàn & Bảo mật", font=("Segoe UI", 14), text_color="#dceeff").place(relx=0.5, rely=0.58, anchor="center")

        # --- CỘT PHẢI ---
        self.right_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        self.right_frame.pack(side="right", fill="both", expand=True)

        self.show_login_form()

    # =========================================================================
    # GIAO DIỆN 1: FORM ĐĂNG NHẬP
    # =========================================================================
    def show_login_form(self):
        self.clear_right_frame()
        self.form_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7)

        ctk.CTkLabel(self.form_frame, text="Chào mừng trở lại!", font=("Segoe UI", 28, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.form_frame, text="Đăng nhập tài khoản của bạn", font=("Segoe UI", 12), text_color="#666").pack(anchor="w", pady=(0, 30))

        # Email
        ctk.CTkLabel(self.form_frame, text="Email", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.entry_email = ctk.CTkEntry(self.form_frame, placeholder_text="Nhập email...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333")
        self.entry_email.pack(fill="x", pady=(0, 15))

        # Password
        ctk.CTkLabel(self.form_frame, text="Mật khẩu", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.entry_pass = ctk.CTkEntry(self.form_frame, placeholder_text="Nhập mật khẩu...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333", show="●")
        self.entry_pass.pack(fill="x", pady=(0, 25))

        # Button Login
        ctk.CTkButton(self.form_frame, text="ĐĂNG NHẬP", height=45, corner_radius=25, font=("Segoe UI", 12, "bold"), fg_color="#0068ff", hover_color="#0056d3", command=self.handle_login).pack(fill="x", pady=(0, 20))

        # Switch to Register
        footer = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        footer.pack(pady=(10, 0))
        ctk.CTkLabel(footer, text="Chưa có tài khoản?", font=("Segoe UI", 11), text_color="#666").pack(side="left")
        ctk.CTkButton(footer, text="Đăng ký ngay", fg_color="transparent", text_color="#0068ff", font=("Segoe UI", 11, "bold"), width=0, hover=False, command=self.show_register_form).pack(side="left", padx=5)

    # =========================================================================
    # GIAO DIỆN 2: FORM ĐĂNG KÝ
    # =========================================================================
    def show_register_form(self):
        self.clear_right_frame()
        self.form_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7)

        ctk.CTkLabel(self.form_frame, text="Tạo tài khoản mới", font=("Segoe UI", 28, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        
        # Name
        ctk.CTkLabel(self.form_frame, text="Tên hiển thị", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.reg_name = ctk.CTkEntry(self.form_frame, placeholder_text="Tên hiển thị...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333")
        self.reg_name.pack(fill="x", pady=(0, 15))

        # Email
        ctk.CTkLabel(self.form_frame, text="Email", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.reg_email = ctk.CTkEntry(self.form_frame, placeholder_text="Email...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333")
        self.reg_email.pack(fill="x", pady=(0, 15))

        # Password
        ctk.CTkLabel(self.form_frame, text="Mật khẩu", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.reg_pass = ctk.CTkEntry(self.form_frame, placeholder_text="Mật khẩu...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333", show="●")
        self.reg_pass.pack(fill="x", pady=(0, 20))

        # Button Register
        ctk.CTkButton(self.form_frame, text="ĐĂNG KÝ", height=45, corner_radius=25, font=("Segoe UI", 12, "bold"), fg_color="#0068ff", hover_color="#0056d3", command=self.handle_register).pack(fill="x", pady=(0, 20))

        # Switch to Login
        footer = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        footer.pack(pady=(10, 0))
        ctk.CTkLabel(footer, text="Đã có tài khoản?", font=("Segoe UI", 11), text_color="#666").pack(side="left")
        ctk.CTkButton(footer, text="Đăng nhập", fg_color="transparent", text_color="#0068ff", font=("Segoe UI", 11, "bold"), width=0, hover=False, command=self.show_login_form).pack(side="left", padx=5)

    def clear_right_frame(self):
        for widget in self.right_frame.winfo_children(): widget.destroy()

    # =========================================================================
    # XỬ LÝ LOGIC (SOCKET)
    # =========================================================================
    def connect_server(self):
        """Tạo kết nối socket tới server nếu chưa có"""
        if self.sock: return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            return True
        except Exception as e:
            messagebox.showerror("Lỗi Mạng", f"Không thể kết nối Server!\n{e}")
            return False

    def handle_login(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_pass.get().strip()
        
        if not email or not pwd:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Email và Mật khẩu.")
            return

        if not self.connect_server(): return

        # Gửi AUTH|LOGIN|email|pass
        cmd = f"AUTH|LOGIN|{email}|{pwd}"
        self.sock.sendall(Protocol.pack(cmd))
        
        # Nhận phản hồi
        response = Protocol.recv_msg_sync(self.sock)
        if response and response.startswith("AUTH|SUCCESS|"):
            # AUTH|SUCCESS|token|username
            parts = response.split("|")
            token = parts[2]
            username = parts[3]
            # messagebox.showinfo("Thành công", f"Chào mừng {username}!")
            # Gọi callback để chuyển màn hình
            if self.on_login_success:
                self.on_login_success(username, self.sock, email, pwd)
        else:
            # AUTH|FAIL|Reason
            reason = response.split("|")[2] if response else "Mất kết nối server"
            messagebox.showerror("Đăng nhập thất bại", reason)
            self.sock.close()
            self.sock = None

    def handle_register(self):
        name = self.reg_name.get().strip()
        email = self.reg_email.get().strip()
        pwd = self.reg_pass.get().strip()
        
        if not name or not email or not pwd:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ thông tin.")
            return

        if not self.connect_server(): return

        # Gửi AUTH|REGISTER|email|pass|name
        cmd = f"AUTH|REGISTER|{email}|{pwd}|{name}"
        self.sock.sendall(Protocol.pack(cmd))

        # Nhận phản hồi
        response = Protocol.recv_msg_sync(self.sock)
        if response and response.startswith("AUTH|SUCCESS"):
            messagebox.showinfo("Thành công", "Đăng ký thành công! Vui lòng đăng nhập.")
            self.show_login_form()
            self.entry_email.insert(0, email)
        else:
            # AUTH|FAIL|Reason
            reason = response.split("|")[2] if response else "Mất kết nối server"
            messagebox.showerror("Đăng ký thất bại", reason)
            self.sock.close()
            self.sock = None

if __name__ == "__main__":
    LoginWindow()