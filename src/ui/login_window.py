import customtkinter as ctk # Thư viện giao diện hiện đại
from tkinter import messagebox
from PIL import Image
import os

# --- CẤU HÌNH GIAO DIỆN CHUNG ---
ctk.set_appearance_mode("Light")  # Chế độ Sáng (hoặc "Dark" nếu thích tối)
ctk.set_default_color_theme("blue") # Theme màu xanh

class LoginWindow:
    def __init__(self, on_login_success_callback=None):
        self.on_login_success = on_login_success_callback
        
        # --- ĐƯỜNG DẪN ẢNH ---
        # Tự động tìm folder assets
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assets_dir = os.path.join(base_dir, 'assets')

        # --- CỬA SỔ CHÍNH ---
        self.root = ctk.CTk() # Dùng CTk thay vì Tk
        self.root.title("ChatApp Enterprise")
        self.root.geometry("1000x650")
        self.root.resizable(False, False)
        
        # Căn giữa màn hình
        self.center_window()
        
        # Load hình ảnh
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
        """Load ảnh Google và Logo"""
        # Load ảnh Google (File google.jpg của bạn)
        try:
            google_path = os.path.join(self.assets_dir, "google.jpg")
            self.google_img = ctk.CTkImage(light_image=Image.open(google_path), 
                                          dark_image=Image.open(google_path), 
                                          size=(20, 20))
        except:
            print("Lỗi: Không tìm thấy google.jpg trong assets!")
            self.google_img = None

        # Load ảnh trang trí bên trái (Nếu không có thì dùng ảnh trên mạng hoặc để trống)
        # Ở đây mình sẽ tạo 1 cái ảnh ảo (placeholder) để demo layout
        self.banner_img = None 
        # Nếu bạn có ảnh banner đẹp, bỏ vào assets và uncomment dòng dưới:
        # self.banner_img = ctk.CTkImage(Image.open(os.path.join(self.assets_dir, "banner.png")), size=(500, 650))

    def build_ui(self):
        # --- CHIA 2 CỘT ---
        # Cột trái (Màu xanh, chứa Logo)
        self.left_frame = ctk.CTkFrame(self.root, width=400, corner_radius=0, fg_color="#0068ff")
        self.left_frame.pack(side="left", fill="both")
        
        # Nội dung bên trái
        ctk.CTkLabel(self.left_frame, text="💬", font=("Segoe UI Emoji", 80), text_color="white").place(relx=0.5, rely=0.35, anchor="center")
        ctk.CTkLabel(self.left_frame, text="ChatApp", font=("Segoe UI", 36, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self.left_frame, text="Kết nối không giới hạn", font=("Segoe UI", 14), text_color="#dceeff").place(relx=0.5, rely=0.58, anchor="center")

        # Cột phải (Màu trắng, chứa Form)
        self.right_frame = ctk.CTkFrame(self.root, fg_color="white", corner_radius=0)
        self.right_frame.pack(side="right", fill="both", expand=True)

        # --- FORM CONTAINER ---
        self.form_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7)

        # Header
        ctk.CTkLabel(self.form_frame, text="Chào mừng trở lại!", font=("Segoe UI", 28, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self.form_frame, text="Đăng nhập tài khoản của bạn", font=("Segoe UI", 12), text_color="#666").pack(anchor="w", pady=(0, 30))

        # --- Ô NHẬP EMAIL (Bo tròn góc) ---
        ctk.CTkLabel(self.form_frame, text="Email / Tài khoản", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        
        self.entry_user = ctk.CTkEntry(
            self.form_frame, 
            placeholder_text="Nhập email...",
            width=300, 
            height=40, 
            corner_radius=20, # <--- BO TRÒN Ở ĐÂY (20px)
            border_color="#e0e0e0", 
            fg_color="#f9f9f9",
            text_color="#333"
        )
        self.entry_user.pack(fill="x", pady=(0, 15))

        # --- Ô NHẬP PASS (Bo tròn góc) ---
        ctk.CTkLabel(self.form_frame, text="Mật khẩu", font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", pady=(0, 5))
        
        self.entry_pass = ctk.CTkEntry(
            self.form_frame, 
            placeholder_text="Nhập mật khẩu...",
            width=300, 
            height=40,
            corner_radius=20, # <--- BO TRÒN Ở ĐÂY
            border_color="#e0e0e0", 
            fg_color="#f9f9f9",
            text_color="#333",
            show="●"
        )
        self.entry_pass.pack(fill="x", pady=(0, 10))

        # Tùy chọn (Quên MK)
        ctk.CTkButton(self.form_frame, text="Quên mật khẩu?", fg_color="transparent", hover=False, text_color="#0068ff", font=("Segoe UI", 11, "bold"), width=0, command=lambda: print("Quên MK")).pack(anchor="e", pady=(0, 20))

        # --- NÚT ĐĂNG NHẬP (Bo tròn mạnh) ---
        self.btn_login = ctk.CTkButton(
            self.form_frame, 
            text="ĐĂNG NHẬP", 
            height=45,
            corner_radius=25, # <--- NÚT BO TRÒN NHƯ HÌNH VIÊN THUỐC
            font=("Segoe UI", 12, "bold"),
            fg_color="#0068ff", 
            hover_color="#0056d3",
            command=self.handle_login
        )
        self.btn_login.pack(fill="x", pady=(0, 25))

        # --- PHÂN CÁCH ---
        ctk.CTkLabel(self.form_frame, text="HOẶC ĐĂNG NHẬP VỚI", font=("Segoe UI", 10, "bold"), text_color="#999").pack()

        # --- NÚT GOOGLE (Bo tròn + Ảnh) ---
        self.btn_google = ctk.CTkButton(
            self.form_frame,
            text="Tiếp tục với Google",
            image=self.google_img, # Chèn ảnh google.jpg vào đây
            compound="left",       # Ảnh nằm bên trái chữ
            height=45,
            corner_radius=25,      # <--- BO TRÒN
            fg_color="white",      # Nền trắng
            text_color="#333",     # Chữ đen
            font=("Segoe UI", 11, "bold"),
            border_width=1,
            border_color="#ddd",
            hover_color="#f1f1f1",
            command=self.handle_google_login
        )
        self.btn_google.pack(fill="x", pady=(15, 0))
        
        # Footer
        footer = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        footer.pack(pady=(30, 0))
        ctk.CTkLabel(footer, text="Chưa có tài khoản?", font=("Segoe UI", 11), text_color="#666").pack(side="left")
        ctk.CTkButton(footer, text="Đăng ký ngay", fg_color="transparent", text_color="#0068ff", font=("Segoe UI", 11, "bold"), width=0, hover=False).pack(side="left", padx=5)

    def handle_login(self):
        user = self.entry_user.get()
        password = self.entry_pass.get()
        
        if user and password:
            if self.on_login_success:
                self.root.destroy()
                self.on_login_success(user)
        else:
            messagebox.showwarning("Thông báo", "Vui lòng nhập đầy đủ thông tin!")

    def handle_google_login(self):
        messagebox.showinfo("Google", "Sẽ mở trình duyệt để xác thực OAuth2!")

if __name__ == "__main__":
    LoginWindow()