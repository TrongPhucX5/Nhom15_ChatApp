import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
import os
import pyrebase
from chat_window import ChatAppClient  # Import file chat cũ của bạn
import datetime

# --- CẤU HÌNH FIREBASE (Dùng Web Config, KHÔNG dùng file json service account) ---
# Bạn hãy thay bằng thông tin thật lấy từ Firebase Console
firebase_config = {
    "apiKey": "AIzaSyAcBOeee6qDUztnh7OCDbqqeO1gc08Omhw",
    "authDomain": "chatapp-3ffc4.firebaseapp.com",
    "databaseURL": "https://chatapp-3ffc4-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "chatapp-3ffc4",
    "storageBucket": "chatapp-3ffc4.appspot.com",
    "messagingSenderId": "496964501572",
    "appId": "1:496964501572:web:b6b609dd82aed0c7593c11"
}

try:
    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    db = firebase.database()
except Exception as e:
    print(f"Lỗi Config Firebase: {e}")
    auth = None

# --- CẤU HÌNH GIAO DIỆN CHUNG ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class LoginWindow:
    def __init__(self):
        # --- ĐƯỜNG DẪN ẢNH ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(base_dir, 'assets')

        # --- CỬA SỔ CHÍNH ---
        self.root = ctk.CTk()
        self.root.title("ChatApp Enterprise - Login")
        self.root.geometry("1000x650")
        self.root.resizable(False, False)
        
        self.center_window()
        self.load_images()
        self.build_ui()
        self.root.mainloop()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

    def load_images(self):
        try:
            google_path = os.path.join(self.assets_dir, "google.jpg")
            self.google_img = ctk.CTkImage(light_image=Image.open(google_path), size=(20, 20))
        except:
            self.google_img = None

    def build_ui(self):
        # --- CỘT TRÁI (LOGO) ---
        self.left_frame = ctk.CTkFrame(self.root, width=400, corner_radius=0, fg_color="#0068ff")
        self.left_frame.pack(side="left", fill="both")
        
        ctk.CTkLabel(self.left_frame, text="💬", font=("Segoe UI Emoji", 80), text_color="white").place(relx=0.5, rely=0.35, anchor="center")
        ctk.CTkLabel(self.left_frame, text="ChatApp", font=("Segoe UI", 36, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self.left_frame, text="Kết nối không giới hạn", font=("Segoe UI", 14), text_color="#dceeff").place(relx=0.5, rely=0.58, anchor="center")

        # --- CỘT PHẢI (CONTAINER CHÍNH) ---
        self.right_frame = ctk.CTkFrame(self.root, fg_color="white", corner_radius=0)
        self.right_frame.pack(side="right", fill="both", expand=True)

        # Mặc định hiện Form Đăng nhập
        self.show_login_form()

    # =========================================================================
    # GIAO DIỆN 1: FORM ĐĂNG NHẬP
    # =========================================================================
    def show_login_form(self):
        self.clear_right_frame() # Xóa nội dung cũ

        self.form_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7)

        # Header
        ctk.CTkLabel(self.form_frame, text="Chào mừng trở lại!", font=("Segoe UI", 28, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.form_frame, text="Đăng nhập tài khoản của bạn", font=("Segoe UI", 12), text_color="#666").pack(anchor="w", pady=(0, 30))

        # Email
        ctk.CTkLabel(self.form_frame, text="Email", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.entry_email = ctk.CTkEntry(self.form_frame, placeholder_text="Nhập email...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333")
        self.entry_email.pack(fill="x", pady=(0, 15))

        # Password
        ctk.CTkLabel(self.form_frame, text="Mật khẩu", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.entry_pass = ctk.CTkEntry(self.form_frame, placeholder_text="Nhập mật khẩu...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333", show="●")
        self.entry_pass.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(self.form_frame, text="Quên mật khẩu?", fg_color="transparent", hover=False, text_color="#0068ff", font=("Segoe UI", 11, "bold"), width=0).pack(anchor="e", pady=(0, 20))

        # Nút Login
        ctk.CTkButton(self.form_frame, text="ĐĂNG NHẬP", height=45, corner_radius=25, font=("Segoe UI", 12, "bold"), fg_color="#0068ff", hover_color="#0056d3", command=self.handle_login).pack(fill="x", pady=(0, 25))

        # Chuyển sang Đăng ký
        footer = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        footer.pack(pady=(30, 0))
        ctk.CTkLabel(footer, text="Chưa có tài khoản?", font=("Segoe UI", 11), text_color="#666").pack(side="left")
        ctk.CTkButton(footer, text="Đăng ký ngay", fg_color="transparent", text_color="#0068ff", font=("Segoe UI", 11, "bold"), width=0, hover=False, command=self.show_register_form).pack(side="left", padx=5)

    # =========================================================================
    # GIAO DIỆN 2: FORM ĐĂNG KÝ (Hiện ngay trên cửa sổ hiện tại)
    # =========================================================================
    def show_register_form(self):
        self.clear_right_frame() # Xóa Form Đăng nhập

        self.form_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7)

        # Header
        ctk.CTkLabel(self.form_frame, text="Tạo tài khoản mới", font=("Segoe UI", 28, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.form_frame, text="Miễn phí và chỉ mất vài giây", font=("Segoe UI", 12), text_color="#666").pack(anchor="w", pady=(0, 30))

        # ===============================================================
        # [CHÈN ĐOẠN NÀY VÀO ĐÂY] - Ô NHẬP TÊN HIỂN THỊ
        # ===============================================================
        ctk.CTkLabel(self.form_frame, text="Tên hiển thị", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.reg_name = ctk.CTkEntry(self.form_frame, placeholder_text="Tên hiển thị...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333")
        self.reg_name.pack(fill="x", pady=(0, 15))
        # ===============================================================

        # Email
        ctk.CTkLabel(self.form_frame, text="Email", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.reg_email = ctk.CTkEntry(self.form_frame, placeholder_text="Email của bạn...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333")
        self.reg_email.pack(fill="x", pady=(0, 15))

        # Password
        ctk.CTkLabel(self.form_frame, text="Mật khẩu", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.reg_pass = ctk.CTkEntry(self.form_frame, placeholder_text="Tạo mật khẩu...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333", show="●")
        self.reg_pass.pack(fill="x", pady=(0, 15))

        # Confirm Password
        ctk.CTkLabel(self.form_frame, text="Nhập lại Mật khẩu", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        self.reg_confirm = ctk.CTkEntry(self.form_frame, placeholder_text="Xác nhận mật khẩu...", width=300, height=40, corner_radius=20, border_color="#e0e0e0", fg_color="#f9f9f9", text_color="#333", show="●")
        self.reg_confirm.pack(fill="x", pady=(0, 25))

        # Nút Register
        ctk.CTkButton(self.form_frame, text="ĐĂNG KÝ TÀI KHOẢN", height=45, corner_radius=25, font=("Segoe UI", 12, "bold"), fg_color="#0068ff", hover_color="#0056d3", command=self.handle_register).pack(fill="x", pady=(0, 20))

        # Quay lại Đăng nhập
        footer = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        footer.pack(pady=(10, 0))
        ctk.CTkLabel(footer, text="Đã có tài khoản?", font=("Segoe UI", 11), text_color="#666").pack(side="left")
        ctk.CTkButton(footer, text="Đăng nhập", fg_color="transparent", text_color="#0068ff", font=("Segoe UI", 11, "bold"), width=0, hover=False, command=self.show_login_form).pack(side="left", padx=5)

    def clear_right_frame(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

    # =========================================================================
    # XỬ LÝ LOGIC (FIREBASE)
    # =========================================================================
    def handle_login(self):
        email = self.entry_email.get()
        pwd = self.entry_pass.get()
        
        if not email or not pwd:
            messagebox.showwarning("Lỗi", "Vui lòng nhập đủ thông tin!")
            return

        try:
            # 1. Đăng nhập Firebase Auth
            user = auth.sign_in_with_email_and_password(email, pwd)
            user_email = user['email']
            
            # ========================================================
            # [PHẦN MỚI THÊM VÀO] CẬP NHẬT GIỜ ĐĂNG NHẬP
            # ========================================================
            user_id = user['localId'] # Lấy ID duy nhất của user
            
            # Cập nhật thời gian vào Database
            db.child("users").child(user_id).update({
                "last_login": str(datetime.datetime.now()),
                "status": "online"
            })
            # ========================================================

            messagebox.showinfo("Thành công", f"Chào mừng {user_email}!")
            
            # 2. Đóng cửa sổ Login và Mở cửa sổ Chat
            self.root.destroy()
            
            # Mở Chat Client
            ChatAppClient(username_from_login=user_email)

        except Exception as e:
            err = str(e)
            if "INVALID_PASSWORD" in err: msg = "Sai mật khẩu!"
            elif "EMAIL_NOT_FOUND" in err: msg = "Email không tồn tại!"
            else: msg = "Lỗi đăng nhập. Kiểm tra lại mạng."
            messagebox.showerror("Thất bại", msg)

    def handle_register(self):
        # Lấy tên từ ô nhập liệu mới
        try:
            name = self.reg_name.get()
        except:
            name = "" # Phòng trường hợp chưa có ô nhập tên

        email = self.reg_email.get()
        pwd = self.reg_pass.get()
        confirm = self.reg_confirm.get()

        # Kiểm tra nhập thiếu
        if not name:
            messagebox.showwarning("Lỗi", "Vui lòng nhập Tên hiển thị!")
            return
        if not email or not pwd:
            messagebox.showwarning("Lỗi", "Vui lòng nhập đủ Email và Mật khẩu!")
            return

        if pwd != confirm:
            messagebox.showerror("Lỗi", "Mật khẩu xác nhận không khớp!")
            return
        
        try:
            # 1. Tạo tài khoản Authentication
            user = auth.create_user_with_email_and_password(email, pwd)
            user_id = user['localId']
            
            # 2. Lưu thông tin vào Database
            user_data = {
                "email": email,
                "username": name,  # Lưu tên bạn nhập
                "uid": user_id,
                "created_at": str(datetime.datetime.now()),
                "last_login": str(datetime.datetime.now())
            }
            
            db.child("users").child(user_id).set(user_data)

            messagebox.showinfo("Thành công", "Đăng ký thành công! Vui lòng đăng nhập.")
            
            # === [SỬA LẠI DÒNG NÀY CHO ĐÚNG] ===
            self.show_login_form() 
            # ===================================
            
            # Tự động điền email vừa đăng ký vào ô đăng nhập
            self.entry_email.insert(0, email)

        except Exception as e:
            err = str(e)
            if "EMAIL_EXISTS" in err: msg = "Email này đã được sử dụng!"
            elif "WEAK_PASSWORD" in err: msg = "Mật khẩu phải có ít nhất 6 ký tự."
            else: msg = f"Lỗi đăng ký: {err}"
            messagebox.showerror("Thất bại", msg)
if __name__ == "__main__":
    LoginWindow()