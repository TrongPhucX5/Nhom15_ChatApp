import customtkinter as ctk
from tkinter import messagebox, filedialog
import socket
import threading
import datetime
import os

# --- CẤU HÌNH MÀU SẮC ZALO ---
ZALO_BLUE = "#0068ff"
ZALO_BG_LIGHT = "#f4f5f7"
ZALO_BUBBLE_ME = "#e5efff"
ZALO_BUBBLE_YOU = "#ffffff"

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class ChatAppClient(ctk.CTk):
    def __init__(self, username_from_login=None, host='127.0.0.1', port=65432):
        super().__init__()
        
        # --- DATA ---
        self.username = username_from_login or "User"
        self.server_host = host
        self.server_port = port
        self.client_socket = None
        self.is_running = True
        self.current_tab = "MSG" # Quản lý tab đang mở (MSG, CONTACT, TODO)

        # --- SETUP WINDOW ---
        self.title(f"Zalo PC - {self.username}")
        self.geometry("1100x700")
        self.minsize(950, 600)
        
        # Layout 3 cột
        self.grid_columnconfigure(0, minsize=70)   # Nav
        self.grid_columnconfigure(1, minsize=300)  # Sidebar
        self.grid_columnconfigure(2, weight=1)     # Main
        self.grid_rowconfigure(0, weight=1)

        # Kết nối
        if not self.connect_server(): return

        # Xây dựng giao diện
        self.build_nav_bar()
        self.build_sidebar()
        self.build_main_chat()
        
        # Thread nhận tin
        self.recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.recv_thread.start()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.mainloop()

    def connect_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            self.client_socket.send(f"LOGIN|{self.username}".encode('utf-8'))
            return True
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không kết nối được Server!\n{e}")
            self.destroy()
            return False

    # =========================================================================
    # 1. NAV BAR (CỘT TRÁI CÙNG)
    # =========================================================================
    def build_nav_bar(self):
        self.nav_frame = ctk.CTkFrame(self, width=70, corner_radius=0, fg_color=ZALO_BLUE)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")
        self.nav_frame.grid_propagate(False)

        # Avatar
        ctk.CTkButton(self.nav_frame, text=self.username[0].upper(), width=45, height=45, corner_radius=22,
                      fg_color="#1a8cff", hover_color="white", text_color="white", font=("Arial", 18, "bold"),
                      command=self.open_profile_modal).pack(pady=(30, 20))

        # Tabs
        self.btn_nav_msg = self.create_nav_btn("💬", True, command=lambda: self.switch_tab("MSG"))
        self.btn_nav_contact = self.create_nav_btn("📇", False, command=lambda: self.switch_tab("CONTACT"))
        self.btn_nav_todo = self.create_nav_btn("✅", False, command=lambda: self.switch_tab("TODO"))
        
        # Settings (Fix lỗi: Gắn đúng hàm open_settings_modal)
        ctk.CTkButton(self.nav_frame, text="⚙️", width=40, height=40, fg_color="transparent",
                      hover_color="#1a8cff", font=("Segoe UI Emoji", 22),
                      command=self.open_settings_modal).pack(side="bottom", pady=20)

    def create_nav_btn(self, icon, is_active, command):
        color = "#1a8cff" if is_active else "transparent"
        btn = ctk.CTkButton(self.nav_frame, text=icon, width=45, height=45, corner_radius=12,
                            fg_color=color, hover_color="#1a8cff", font=("Segoe UI Emoji", 22),
                            command=command)
        btn.pack(pady=8)
        return btn

    def switch_tab(self, tab_name):
        """Hàm chuyển đổi giữa các tab Tin nhắn, Danh bạ, Todo"""
        self.current_tab = tab_name
        
        # Reset màu nút
        self.btn_nav_msg.configure(fg_color="#1a8cff" if tab_name=="MSG" else "transparent")
        self.btn_nav_contact.configure(fg_color="#1a8cff" if tab_name=="CONTACT" else "transparent")
        self.btn_nav_todo.configure(fg_color="#1a8cff" if tab_name=="TODO" else "transparent")

        # Thay đổi nội dung Sidebar tương ứng
        if tab_name == "MSG":
            self.lbl_sidebar_title.configure(text="Tin nhắn")
            # Hiện lại list chat (Logic thực tế sẽ load lại list khác)
        elif tab_name == "CONTACT":
            self.lbl_sidebar_title.configure(text="Danh bạ")
            self.show_dummy_contacts()
        elif tab_name == "TODO":
            self.lbl_sidebar_title.configure(text="Việc cần làm")
            self.show_dummy_todos()

    # =========================================================================
    # 2. SIDEBAR (CỘT GIỮA)
    # =========================================================================
    def build_sidebar(self):
        self.side_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="white")
        self.side_frame.grid(row=0, column=1, sticky="nsew")
        self.side_frame.grid_propagate(False)
        self.side_frame.grid_rowconfigure(2, weight=1)

        # Header Sidebar
        header_side = ctk.CTkFrame(self.side_frame, height=60, fg_color="transparent")
        header_side.grid(row=0, column=0, sticky="ew")
        
        self.lbl_sidebar_title = ctk.CTkLabel(header_side, text="Tìm kiếm", font=("Segoe UI", 14, "bold"), text_color="gray")
        self.lbl_sidebar_title.pack(side="left", padx=15, pady=15)
        
        ctk.CTkButton(header_side, text="➕", width=30, height=30, fg_color="transparent", text_color="black", 
                      hover_color="#eee", font=("Arial", 16), command=self.add_new_action).pack(side="right", padx=10)

        # Search box
        self.entry_search = ctk.CTkEntry(self.side_frame, placeholder_text="Tìm bạn bè, tin nhắn...", height=35, 
                                         fg_color="#eaedf0", border_width=0, text_color="black")
        self.entry_search.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        # List Content
        self.user_scroll = ctk.CTkScrollableFrame(self.side_frame, fg_color="transparent")
        self.user_scroll.grid(row=2, column=0, sticky="nsew")

    # =========================================================================
    # 3. MAIN CHAT (CỘT PHẢI)
    # =========================================================================
    def build_main_chat(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=ZALO_BG_LIGHT)
        self.main_frame.grid(row=0, column=2, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # --- Header ---
        self.header = ctk.CTkFrame(self.main_frame, height=68, corner_radius=0, fg_color="white")
        self.header.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkButton(self.header, text="👥", width=45, height=45, corner_radius=22, fg_color="#e5efff", 
                      text_color=ZALO_BLUE, font=("Segoe UI Emoji", 20), hover=False).pack(side="left", padx=20, pady=10)
        
        info = ctk.CTkFrame(self.header, fg_color="transparent")
        info.pack(side="left", pady=10)
        self.lbl_chat_name = ctk.CTkLabel(info, text="Phòng Chat Chung", font=("Segoe UI", 16, "bold"), text_color="black")
        self.lbl_chat_name.pack(anchor="w")
        ctk.CTkLabel(info, text="Trực tuyến", font=("Segoe UI", 11), text_color="green").pack(anchor="w")
        
        # Icons Header (Video Call, Search)
        ctk.CTkButton(self.header, text="📹", width=40, height=40, fg_color="transparent", text_color="#555", 
                      hover_color="#f0f0f0", font=("Segoe UI Emoji", 20), command=self.dummy_video_call).pack(side="right", padx=15)
        ctk.CTkButton(self.header, text="🔍", width=40, height=40, fg_color="transparent", text_color="#555", 
                      hover_color="#f0f0f0", font=("Segoe UI Emoji", 20), command=lambda: messagebox.showinfo("Info", "Tìm tin nhắn cũ")).pack(side="right")

        # --- Chat Area ---
        self.msg_area = ctk.CTkScrollableFrame(self.main_frame, fg_color=ZALO_BG_LIGHT)
        self.msg_area.grid(row=1, column=0, sticky="nsew")

        # --- Input Area ---
        self.input_container = ctk.CTkFrame(self.main_frame, height=140, corner_radius=0, fg_color="white")
        self.input_container.grid(row=2, column=0, sticky="ew")

        # Toolbar
        toolbar = ctk.CTkFrame(self.input_container, height=40, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(5,0))
        
        # Các nút chức năng Toolbar (Đã gắn hàm giả lập)
        self.create_tool_btn(toolbar, "📎", self.send_file_action) # File
        self.create_tool_btn(toolbar, "🖼️", self.send_image_action) # Ảnh
        self.create_tool_btn(toolbar, "😀", self.dummy_sticker)     # Sticker
        self.create_tool_btn(toolbar, "📅", lambda: messagebox.showinfo("Lịch", "Tạo nhắc hẹn"))

        # Ô nhập
        self.entry_msg = ctk.CTkEntry(self.input_container, placeholder_text="Nhập tin nhắn...",
                                      height=45, border_width=0, fg_color="transparent", 
                                      font=("Segoe UI", 14), text_color="black")
        self.entry_msg.pack(fill="x", padx=10)
        self.entry_msg.bind("<Return>", self.send_msg)

        # Nút Gửi
        bottom_bar = ctk.CTkFrame(self.input_container, height=40, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(bottom_bar, text="GỬI", width=90, height=35, corner_radius=5,
                      fg_color="#e5efff", text_color=ZALO_BLUE, hover_color="#c7e0ff", 
                      font=("Segoe UI", 12, "bold"), command=self.send_msg).pack(side="right")

    def create_tool_btn(self, parent, icon, cmd):
        ctk.CTkButton(parent, text=icon, width=40, height=35, fg_color="transparent", 
                      text_color="#555", hover_color="#f0f0f0", font=("Segoe UI Emoji", 18), 
                      command=cmd).pack(side="left", padx=2)

    # =========================================================================
    # 4. CÁC HÀM XỬ LÝ SỰ KIỆN (INTERACTIONS)
    # =========================================================================
    
    # --- Chức năng Cài đặt (Fix lỗi cũ) ---
    def open_settings_modal(self):
        win = ctk.CTkToplevel(self)
        win.title("Cài đặt")
        win.geometry("500x400")
        win.attributes("-topmost", True)
        
        ctk.CTkLabel(win, text="Cài đặt Ứng dụng", font=("Segoe UI", 20, "bold")).pack(pady=20)
        
        # Tabs setting
        tab = ctk.CTkTabview(win, width=450, height=300)
        tab.pack()
        tab.add("Giao diện")
        tab.add("Tài khoản")
        
        # Tab Giao diện
        switch_var = ctk.StringVar(value="off")
        def toggle_mode():
            mode = "Dark" if switch_var.get() == "on" else "Light"
            ctk.set_appearance_mode(mode)
            
        ctk.CTkSwitch(tab.tab("Giao diện"), text="Chế độ Tối (Dark Mode)", 
                      variable=switch_var, onvalue="on", offvalue="off", command=toggle_mode).pack(pady=20)
        
        # Tab Tài khoản
        ctk.CTkLabel(tab.tab("Tài khoản"), text=f"Đang đăng nhập: {self.username}").pack(pady=10)
        ctk.CTkButton(tab.tab("Tài khoản"), text="Đổi mật khẩu", fg_color="gray").pack(pady=5)
        ctk.CTkButton(tab.tab("Tài khoản"), text="Đăng xuất", fg_color="red", command=self.on_close).pack(pady=20)

    # --- Chức năng Profile ---
    def open_profile_modal(self):
        win = ctk.CTkToplevel(self)
        win.title("Hồ sơ")
        win.geometry("300x400")
        win.attributes("-topmost", True)
        
        ctk.CTkButton(win, text=self.username[0].upper(), width=100, height=100, corner_radius=50,
                      fg_color=ZALO_BLUE, font=("Arial", 40, "bold"), hover=False).pack(pady=40)
        ctk.CTkLabel(win, text=self.username, font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(win, text="Project Manager", text_color="gray").pack()
        
        ctk.CTkButton(win, text="Cập nhật thông tin", fg_color="transparent", border_width=1, border_color="#ddd", text_color="black").pack(pady=30)

    # --- Các chức năng giả lập khác ---
    def show_dummy_contacts(self):
        """Hiển thị danh sách bạn bè giả khi bấm tab Danh bạ"""
        for w in self.user_scroll.winfo_children(): w.destroy()
        
        contacts = ["An Nguyen", "Binh Tran", "Chi Le", "Dung Pham", "Giang Vo"]
        for c in contacts:
            frame = ctk.CTkFrame(self.user_scroll, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkButton(frame, text=c[0], width=40, height=40, corner_radius=20, fg_color="#e6e8eb", text_color="black", hover=False).pack(side="left", padx=10)
            ctk.CTkLabel(frame, text=c, font=("Segoe UI", 12, "bold"), text_color="black").pack(side="left")
            ctk.CTkButton(frame, text="📞", width=30, fg_color="transparent", text_color="green", font=("Arial", 16)).pack(side="right", padx=10)

    def show_dummy_todos(self):
        """Hiển thị Todo list giả"""
        for w in self.user_scroll.winfo_children(): w.destroy()
        
        todos = ["Nộp báo cáo LTM", "Code module File", "Họp nhóm 8h tối", "Fix lỗi Server"]
        for t in todos:
            chk = ctk.CTkCheckBox(self.user_scroll, text=t, text_color="black", font=("Segoe UI", 12))
            chk.pack(fill="x", pady=10, padx=20)

    def add_new_action(self):
        if self.current_tab == "MSG":
            messagebox.showinfo("Mới", "Tạo nhóm chat mới")
        elif self.current_tab == "CONTACT":
            messagebox.showinfo("Mới", "Thêm bạn mới")
        else:
            messagebox.showinfo("Mới", "Thêm công việc mới")

    def dummy_video_call(self):
        win = ctk.CTkToplevel(self)
        win.geometry("400x300")
        win.title("Video Call")
        ctk.CTkLabel(win, text="📞", font=("Arial", 60)).pack(pady=50)
        ctk.CTkLabel(win, text="Đang gọi...", font=("Segoe UI", 16)).pack()
        ctk.CTkButton(win, text="Kết thúc", fg_color="red", command=win.destroy).pack(pady=20)

    def dummy_sticker(self):
        messagebox.showinfo("Sticker", "Hiện bảng chọn Sticker (Mèo, Gấu, Vịt...)")

    def send_file_action(self):
        f = filedialog.askopenfilename()
        if f: self.entry_msg.insert(0, f"[FILE] {os.path.basename(f)}")

    def send_image_action(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if f: self.entry_msg.insert(0, f"[IMAGE] {os.path.basename(f)}")

    # --- LOGIC MẠNG (CORE) ---
    def send_msg(self, event=None):
        msg = self.entry_msg.get().strip()
        if not msg: return
        try:
            self.client_socket.send(f"MSG|{msg}".encode('utf-8'))
            self.add_message_bubble("Bạn", msg, is_me=True)
            self.entry_msg.delete(0, "end")
        except: pass

    def update_user_list_ui(self, user_str):
        if self.current_tab != "MSG": return # Chỉ hiện user online khi ở tab MSG
        for w in self.user_scroll.winfo_children(): w.destroy()
        
        users = user_str.split(",")
        for u in users:
            color = ZALO_BLUE if u == self.username else "#e6e8eb"
            txt = "white" if u == self.username else "black"
            
            frame = ctk.CTkFrame(self.user_scroll, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            ctk.CTkButton(frame, text=u[0].upper(), width=40, height=40, corner_radius=20, 
                          fg_color=color, text_color=txt, hover=False).pack(side="left", padx=15)
            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left")
            ctk.CTkLabel(info, text=u, font=("Segoe UI", 13, "bold"), text_color="black").pack(anchor="w")
            ctk.CTkLabel(info, text="Online", font=("Segoe UI", 11), text_color="green").pack(anchor="w")

    def add_message_bubble(self, sender, content, is_me):
        if is_me:
            bg, align, anchor = ZALO_BUBBLE_ME, "right", "e"
        else:
            bg, align, anchor = ZALO_BUBBLE_YOU, "left", "w"

        row = ctk.CTkFrame(self.msg_area, fg_color="transparent")
        row.pack(fill="x", pady=5, padx=20)

        if not is_me:
            ctk.CTkButton(row, text=sender[0], width=30, height=30, corner_radius=15, 
                          fg_color="#e6e8eb", text_color="#555", hover=False).pack(side="left", anchor="n")

        bubble = ctk.CTkFrame(row, fg_color=bg, corner_radius=12, border_width=1, border_color="#ddd")
        bubble.pack(side=align, padx=(5 if not is_me else 0, 0), anchor=anchor)

        if not is_me:
             ctk.CTkLabel(bubble, text=sender, font=("Segoe UI", 10, "bold"), text_color="gray").pack(anchor="w", padx=12, pady=(5,0))
        
        ctk.CTkLabel(bubble, text=content, font=("Segoe UI", 13), text_color="black", wraplength=450, justify="left").pack(padx=12, pady=8)
        self.msg_area._parent_canvas.yview_moveto(1.0)

    def receive_loop(self):
        while self.is_running:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data: break
                if data.startswith("MSG|"):
                    parts = data.split("|")
                    self.add_message_bubble(parts[1], parts[2], is_me=False)
                elif data.startswith("LIST|"):
                    self.update_user_list_ui(data.split("|")[1])
            except: break
    
    def on_close(self):
        self.is_running = False
        if self.client_socket: self.client_socket.close()
        self.destroy()

if __name__ == "__main__":
    ChatAppClient(username_from_login="Dev")