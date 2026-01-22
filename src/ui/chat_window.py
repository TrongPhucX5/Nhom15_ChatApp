import customtkinter as ctk
from tkinter import messagebox, filedialog
import socket
import threading
import datetime
import os
import sys
import base64
from PIL import Image
import io

# Thêm đường dẫn để import core.protocol nếu chạy trực tiếp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.protocol import Protocol
except ImportError:
    # Fallback nếu path chưa chuẩn
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from core.protocol import Protocol

# --- CẤU HÌNH MÀU SẮC  ---
# --- CẤU HÌNH MÀU SẮC (MODERN) ---
ZALO_BLUE = "#0084FF" # Messenger Blue
ZALO_BG_LIGHT = "#F0F2F5"
ZALO_BUBBLE_ME = "#0084FF" # Blue for me
ZALO_BUBBLE_YOU = "#3a3b3c" # Gray for others
TEXT_COLOR_ME = "white"
TEXT_COLOR_YOU = "white"

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# --- TOOLTIP CLASS ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<ButtonPress>", self.hide)

    def schedule(self, event=None):
        self.id = self.widget.after(500, self.show) # Wait 0.5s before showing

    def show(self, event=None):
        if self.tooltip: return
        try:
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25

            self.tooltip = ctk.CTkToplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            self.tooltip.attributes("-topmost", True)
            
            # Transparent bg for rounded effect (Workaround for CTk)
            # CTk Toplevel doesn't support transparent corners well on all OS, 
            # so we just make the frame black.
            
            label = ctk.CTkLabel(self.tooltip, text=self.text, fg_color="black", text_color="white", corner_radius=8, width=10, height=25)
            # Add padding within label
            label.pack(padx=1, pady=1) 
        except: pass

    def hide(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class ChatAppClient(ctk.CTkFrame):
    def __init__(self, master, username_from_login=None, host='127.0.0.1', port=65432, existing_socket=None, on_logout_callback=None, email=None, password=None):
        super().__init__(master)
        
        # --- DATA ---
        self.on_logout_callback = on_logout_callback
        self.username = username_from_login or "User"
        self.email = email
        self.password = password
        self.username = username_from_login or "User"
        self.server_host = host
        self.server_port = port
        self.client_socket = existing_socket
        self.is_running = True
        self.connect_state = "CONNECTED" # CONNECTED, RECONNECTING
        self.current_tab = "MSG"
        
        # --- CHAT STATE ---
        self.chat_mode = "DIRECT" # DIRECT or GROUP
        self.target_name = "General" # Initial dummy target 
        self.user_list_data = [] # Store list of online users
        self.group_list_data = [] # Store list of joined groups
        self.unread_counts = {} # Store unread messages count per group {group_name: int}
        self.msg_status_queues = {} # {receiver_name: [label1, label2, ...]}

        # Layout 3 cột
        self.grid_columnconfigure(0, minsize=70)   # Nav
        self.grid_columnconfigure(1, minsize=300)  # Sidebar
        self.grid_columnconfigure(2, weight=1)     # Main
        self.grid_rowconfigure(0, weight=1)

        # Kết nối
        if not self.connect_server():
            print("[CLIENT] Initial connection failed. Entering RECONNECTING state.")
            self.connect_state = "RECONNECTING"
        
        # Xây dựng giao diện (luôn xây dựng)
        self.build_nav_bar()
        self.build_sidebar()
        self.build_main_chat()
        self.build_settings_view() # Thêm view cài đặt tích hợp
        self.build_profile_view() # Thêm view profile tích hợp
        
        if self.connect_state == "RECONNECTING":
            # Nếu chưa connect được, báo UI đang đợi
            self.after(0, self._ui_on_disconnect)
            threading.Thread(target=self.reconnect_loop, daemon=True).start()
        else:
            # Thread nhận tin
            self.recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.recv_thread.start()

            # Thread Heartbeat (Ping)
            self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

    def connect_server(self):
        # Nếu đã có socket (từ Login truyền sang) thì dùng luôn
        if self.client_socket:
            return True
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            # Gửi LOGIN dùng Protocol
            # msg = Protocol.pack(f"LOGIN|{self.username}") # Legacy
            # Use AUTH|LOGIN if we have credentials, else fallback or fail
            if self.email and self.password:
                msg = Protocol.pack(f"AUTH|LOGIN|{self.email}|{self.password}")
                self.client_socket.sendall(msg)
                
                # Check response synchronously
                resp = Protocol.recv_msg_sync(self.client_socket)
                if resp and resp.startswith("AUTH|SUCCESS"):
                    return True
                else:
                     return False
            else:
                # Fallback for dev/legacy without strict auth
                msg = Protocol.pack(f"LOGIN|{self.username}")
                self.client_socket.sendall(msg)
                return True
        except Exception as e:
            # messagebox.showerror("Lỗi", f"Không kết nối được Server!\n{e}")
            # Suppress error in reconnect loop
            return False

    def handle_disconnect(self):
        if self.connect_state == "RECONNECTING": return
        self.connect_state = "RECONNECTING"
        print("[CLIENT] Lost connection. Reconnecting...")
        
        # UI Update (Thread Safe)
        self.after(0, self._ui_on_disconnect)
        
        self.client_socket = None
        
        # Start Reconnect Thread
        threading.Thread(target=self.reconnect_loop, daemon=True).start()
    
    def _ui_on_disconnect(self):
        try:
            now = datetime.datetime.now().strftime("%H:%M:%S")
            self.lbl_chat_name.configure(text=f"🔄 Waiting for server... [{now}]")
            self.entry_msg.configure(state="disabled")
            self.btn_send.configure(state="disabled")
        except Exception as e:
            print(f"Error updating UI on disconnect: {e}")

    def reconnect_loop(self):
        import time
        while self.is_running and self.connect_state == "RECONNECTING":
            time.sleep(5) # Wait 5s
            print("[CLIENT] Attempting reconnect...")
            if self.connect_server():
                print("[CLIENT] Reconnect Success!")
                self.connect_state = "CONNECTED"
                
                # Restore UI (Thread Safe)
                self.after(0, self._ui_on_reconnect)
                
                # Re-start threads
                self.recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
                self.recv_thread.start()
                
                if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
                     self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
                     self.heartbeat_thread.start()
                
                break # Exit reconnect loop

    def _ui_on_reconnect(self):
        try:
            # select_chat_target already handles header text and history reload
            self.select_chat_target(self.chat_mode, self.target_name)
            self.entry_msg.configure(state="normal")
            self.btn_send.configure(state="normal")
        except Exception as e:
            print(f"Error restoring UI: {e}")
            return False

    # =========================================================================
    # 1. NAV BAR (CỘT TRÁI CÙNG)
    # =========================================================================
    def build_nav_bar(self):
        # Đổi fg_color thành adaptive color (Light, Dark)
        self.nav_frame = ctk.CTkFrame(self, width=70, corner_radius=0, fg_color=("#0084FF", "#262626"))
        self.nav_frame.grid(row=0, column=0, sticky="nsew")
        self.nav_frame.grid_propagate(False)

        # Avatar
        btn_avatar = ctk.CTkButton(self.nav_frame, text=self.username[0].upper(), width=45, height=45, corner_radius=22,
                      fg_color=("#1a8cff", "#3a3b3c"), hover_color=("white", "#4e4f50"), text_color="white", font=("Arial", 18, "bold"),
                      command=self.open_profile_modal)
        btn_avatar.pack(pady=(30, 20))
        ToolTip(btn_avatar, "Hồ sơ của bạn")

        # Tabs
        self.btn_nav_msg = self.create_nav_btn("💬", True, lambda: self.switch_tab("MSG"), "Tin nhắn")
        self.btn_nav_contact = self.create_nav_btn("📇", False, lambda: self.switch_tab("CONTACT"), "Danh bạ")
        # self.btn_nav_todo = self.create_nav_btn("✅", False, lambda: self.switch_tab("TODO"), "Việc cần làm")
        
        # Settings
        btn_settings = ctk.CTkButton(self.nav_frame, text="⚙️", width=40, height=40, fg_color="transparent",
                      hover_color=("#1a8cff", "#3a3b3c"), font=("Segoe UI Emoji", 22),
                      command=self.open_settings_modal)
        btn_settings.pack(side="bottom", pady=20)
        ToolTip(btn_settings, "Cài đặt")

    def create_nav_btn(self, icon, is_active, command, tooltip=""):
        active_color = ("#1a8cff", "#3a3b3c")
        color = active_color if is_active else "transparent"
        btn = ctk.CTkButton(self.nav_frame, text=icon, width=45, height=45, corner_radius=12,
                            fg_color=color, hover_color=active_color, font=("Segoe UI Emoji", 22),
                            command=command)
        btn.pack(pady=8)
        if tooltip: ToolTip(btn, tooltip)
        return btn

    def switch_tab(self, tab_name):
        """Hàm chuyển đổi giữa các tab Tin nhắn, Danh bạ, Todo"""
        self.current_tab = tab_name
        
        # Reset màu nút
        self.btn_nav_msg.configure(fg_color="#1a8cff" if tab_name=="MSG" else "transparent")
        self.btn_nav_contact.configure(fg_color="#1a8cff" if tab_name=="CONTACT" else "transparent")
        # self.btn_nav_todo.configure(fg_color="#1a8cff" if tab_name=="TODO" else "transparent")

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
    # =========================================================================
    def build_sidebar(self):
        self.side_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color=("white", "#2b2b2b"))
        self.side_frame.grid(row=0, column=1, sticky="nsew")
        self.side_frame.grid_propagate(False)
        self.side_frame.grid_rowconfigure(2, weight=1)

        # Header Sidebar
        header_side = ctk.CTkFrame(self.side_frame, height=60, fg_color="transparent")
        header_side.grid(row=0, column=0, sticky="ew")
        
        self.lbl_sidebar_title = ctk.CTkLabel(header_side, text="Tìm kiếm", font=("Segoe UI", 14, "bold"), text_color=("gray", "lightgray"))
        self.lbl_sidebar_title.pack(side="left", padx=15, pady=15)
        
        btn_add = ctk.CTkButton(header_side, text="➕", width=30, height=30, fg_color="transparent", text_color=("black", "white"), 
                      hover_color=("gray90", "gray40"), font=("Arial", 16), command=self.add_new_action)
        btn_add.pack(side="right", padx=5)
        ToolTip(btn_add, "Tạo nhóm mới")

        btn_join = ctk.CTkButton(header_side, text="🔗", width=30, height=30, fg_color="transparent", text_color=("black", "white"), 
                      hover_color=("gray90", "gray40"), font=("Arial", 16), command=self.join_group_action)
        btn_join.pack(side="right", padx=5)
        ToolTip(btn_join, "Tham gia nhóm")

        # Search box
        self.entry_search = ctk.CTkEntry(self.side_frame, placeholder_text="Tìm kiếm...", height=35, 
                                         fg_color=("#eaedf0", "#3a3b3c"), border_width=0, text_color=("black", "white"))
        self.entry_search.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        # List Content
        self.user_scroll = ctk.CTkScrollableFrame(self.side_frame, fg_color="transparent")
        self.user_scroll.grid(row=2, column=0, sticky="nsew")

    # =========================================================================
    # 3. MAIN CHAT (CỘT PHẢI)
    # =========================================================================
    def build_main_chat(self):

        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=(ZALO_BG_LIGHT, "#1e1e1e"))
        self.main_frame.grid(row=0, column=2, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # --- Header ---
        # --- Header ---
        self.header = ctk.CTkFrame(self.main_frame, height=68, corner_radius=0, fg_color=("white", "#2b2b2b"))
        self.header.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkButton(self.header, text="👥", width=45, height=45, corner_radius=22, fg_color="#e5efff", 
                      text_color=ZALO_BLUE, font=("Segoe UI Emoji", 20), hover=False).pack(side="left", padx=20, pady=10)
        
        info = ctk.CTkFrame(self.header, fg_color="transparent")
        info.pack(side="left", pady=10)
        self.lbl_chat_name = ctk.CTkLabel(info, text="Phòng Chat Chung", font=("Segoe UI", 15, "bold"), text_color=("black", "white"))
        self.lbl_chat_name.pack(anchor="w")
        ctk.CTkLabel(info, text="Trực tuyến", font=("Segoe UI", 11), text_color="green").pack(anchor="w")
        
        # Icons Header (Video Call, Search)
        btn_video = ctk.CTkButton(self.header, text="📹", width=40, height=40, fg_color="transparent", text_color="#555", 
                      hover_color="#f0f0f0", font=("Segoe UI Emoji", 20), command=self.dummy_video_call)
        btn_video.pack(side="right", padx=15)
        ToolTip(btn_video, "Gọi Video (Giả lập)")
        
        btn_search_msg = ctk.CTkButton(self.header, text="🔍", width=40, height=40, fg_color="transparent", text_color="#555", 
                      hover_color="#f0f0f0", font=("Segoe UI Emoji", 20), command=lambda: messagebox.showinfo("Info", "Tìm tin nhắn cũ"))
        btn_search_msg.pack(side="right")
        ToolTip(btn_video, "Gọi Video (Giả lập)")

        # Group Action Buttons (Hidden by default)
        self.btn_leave_group = ctk.CTkButton(self.header, text="🏃", width=40, height=40, fg_color="transparent", text_color="red",
                                           hover_color="#ffe6e6", font=("Segoe UI Emoji", 20), command=self.leave_group_action)
        self.btn_delete_group = ctk.CTkButton(self.header, text="🗑️", width=40, height=40, fg_color="transparent", text_color="red",
                                            hover_color="#ffe6e6", font=("Segoe UI Emoji", 20), command=self.delete_group_action)

        # --- Chat Area ---
        # --- Chat Area ---
        self.msg_area = ctk.CTkScrollableFrame(self.main_frame, fg_color=(ZALO_BG_LIGHT, "#1e1e1e"))
        self.msg_area.grid(row=1, column=0, sticky="nsew")

        # --- Input Area ---
        # --- Input Area ---
        # --- Input Area (Floating Style) ---
        self.input_container = ctk.CTkFrame(self.main_frame, height=80, fg_color="transparent")
        self.input_container.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        # Typing Indicator (Moved here)
        self.lbl_typing = ctk.CTkLabel(self.input_container, text="", font=("Segoe UI", 11, "bold"), text_color="#0084FF")
        self.lbl_typing.pack(anchor="w", padx=10, pady=(0,2))
        
        # Inner styling frame
        self.input_bg = ctk.CTkFrame(self.input_container, fg_color=("white", "#2b2b2b"), corner_radius=25, border_width=1, border_color=("#ddd", "#444"))
        self.input_bg.pack(fill="both", expand=True)

        # Attachment Button
        btn_attach = ctk.CTkButton(self.input_bg, text="📎", width=40, height=40, fg_color="transparent", text_color="#555", 
                                   hover_color="#f0f0f0", font=("Segoe UI Emoji", 20), corner_radius=20, command=self.send_file_action)
        btn_attach.pack(side="left", padx=5, pady=5)
        
        # Text Entry
        self.entry_msg = ctk.CTkEntry(self.input_bg, placeholder_text="Nhập tin nhắn...", height=40, 
                                      border_width=0, fg_color="transparent", font=("Segoe UI", 14), text_color=("black", "white"))
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_msg.bind("<Return>", self.send_msg)
        
        # Validation & Typing
        self.last_typing_time = 0
        def validate_input(event=None):
            text = self.entry_msg.get().strip()
            if not text:
                self.btn_send.configure(state="disabled", fg_color="gray", text_color="#ccc")
            else:
                self.btn_send.configure(state="normal", fg_color="transparent", text_color=ZALO_BLUE)
            
            # Send Typing Signal (Debounced 2s)
            import time
            now = time.time()
            if now - self.last_typing_time > 2.0:
                self.last_typing_time = now
                threading.Thread(target=self.send_typing_signal).start()
        
        self.entry_msg.bind("<KeyRelease>", validate_input)

        # Emoji Button
        btn_emoji = ctk.CTkButton(self.input_bg, text="😀", width=40, height=40, fg_color="transparent", text_color="#555", 
                                   hover_color="#f0f0f0", font=("Segoe UI Emoji", 20), corner_radius=20, command=self.dummy_sticker)
        btn_emoji.pack(side="right", padx=5)

        # Send Button
        self.btn_send = ctk.CTkButton(self.input_bg, text="➤", width=45, height=40, fg_color="transparent", 
                                 text_color=ZALO_BLUE, font=("Segoe UI Emoji", 22), hover_color="#e6f2ff", corner_radius=20, command=self.send_msg)
        self.btn_send.pack(side="right", padx=(0,5))
        
        # Init State
        validate_input()

    def build_settings_view(self):
        """Xây dựng khung cài đặt tích hợp trong cửa sổ chính (Dạng 1 trang cuộn)"""
        self.settings_view = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#1e1e1e"))
        # Không grid ngay, để ẩn lúc đầu
        
        # --- 1. Header của Settings (Giữ nguyên) ---
        settings_header = ctk.CTkFrame(self.settings_view, height=68, corner_radius=0, fg_color=("white", "#2b2b2b"))
        settings_header.pack(side="top", fill="x")
        
        btn_back = ctk.CTkButton(settings_header, text="⬅ Quay lại", width=100, height=35, fg_color=ZALO_BLUE, 
                                 text_color="white", command=self.close_settings_view)
        btn_back.pack(side="left", padx=20, pady=15)
        
        ctk.CTkLabel(settings_header, text="Cài đặt hệ thống", font=("Segoe UI", 18, "bold")).pack(side="left", padx=20)

        # --- 2. Body: Dùng ScrollableFrame thay vì Tabview ---
        self.settings_body = ctk.CTkScrollableFrame(self.settings_view, fg_color="transparent")
        self.settings_body.pack(fill="both", expand=True, padx=20, pady=20)

        # ==========================
        # PHẦN 1: GIAO DIỆN
        # ==========================
        self._create_section_header("🎨 Giao diện & Hiển thị")
        
        frame_ui = ctk.CTkFrame(self.settings_body, fg_color=("white", "#2b2b2b"), corner_radius=10)
        frame_ui.pack(fill="x", pady=(0, 20))

        # Dark Mode Switch
        switch_var = ctk.StringVar(value="on" if ctk.get_appearance_mode() == "Dark" else "off")
        def toggle_mode():
            mode = "Dark" if switch_var.get() == "on" else "Light"
            ctk.set_appearance_mode(mode)
            
        row_dark = ctk.CTkFrame(frame_ui, fg_color="transparent")
        row_dark.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(row_dark, text="Chế độ Tối (Dark Mode)", font=("Segoe UI", 14)).pack(side="left")
        ctk.CTkSwitch(row_dark, text="", variable=switch_var, onvalue="on", offvalue="off", 
                      command=toggle_mode, width=50).pack(side="right")

        # ==========================
        # PHẦN 2: BẢO MẬT
        # ==========================
        self._create_section_header("🔒 Bảo mật & Mật khẩu")

        frame_sec = ctk.CTkFrame(self.settings_body, fg_color=("white", "#2b2b2b"), corner_radius=10)
        frame_sec.pack(fill="x", pady=(0, 20))

        # Form đổi mật khẩu
        sec_inner = ctk.CTkFrame(frame_sec, fg_color="transparent")
        sec_inner.pack(padx=20, pady=15, fill="x")

        ctk.CTkLabel(sec_inner, text="Đổi mật khẩu", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))

        txt_old_pass = ctk.CTkEntry(sec_inner, placeholder_text="Mật khẩu hiện tại", show="*", height=40)
        txt_old_pass.pack(fill="x", pady=5)
        
        txt_new_pass = ctk.CTkEntry(sec_inner, placeholder_text="Mật khẩu mới", show="*", height=40)
        txt_new_pass.pack(fill="x", pady=5)

        def save_pass_action():
            old = txt_old_pass.get()
            new = txt_new_pass.get()
            if not old or not new:
                messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ")
                return
            try:
                self.client_socket.sendall(Protocol.pack(f"CMD_PASS_CHANGE|{old}|{new}"))
                messagebox.showinfo("Thông báo", "Đã gửi yêu cầu đổi mật khẩu")
                txt_old_pass.delete(0, 'end')
                txt_new_pass.delete(0, 'end')
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

        ctk.CTkButton(sec_inner, text="Cập nhật mật khẩu", command=save_pass_action, 
                      fg_color=ZALO_BLUE, height=40).pack(fill="x", pady=(15, 0))

        # ==========================
        # PHẦN 3: HỆ THỐNG
        # ==========================
        self._create_section_header("ℹ️ Thông tin & Hệ thống")

        frame_sys = ctk.CTkFrame(self.settings_body, fg_color=("white", "#2b2b2b"), corner_radius=10)
        frame_sys.pack(fill="x", pady=(0, 20))

        sys_inner = ctk.CTkFrame(frame_sys, fg_color="transparent")
        sys_inner.pack(padx=20, pady=15, fill="x")

        # Thông tin user (Dạng dòng)
        def _add_info_row(parent, label, value):
            r = ctk.CTkFrame(parent, fg_color="transparent")
            r.pack(fill="x", pady=5)
            ctk.CTkLabel(r, text=label, font=("Segoe UI", 14), text_color="gray").pack(side="left")
            ctk.CTkLabel(r, text=value, font=("Segoe UI", 14, "bold")).pack(side="right")

        _add_info_row(sys_inner, "Tài khoản:", self.username)
        _add_info_row(sys_inner, "Email ID:", self.email or "Chưa cập nhật")
        
        # Divider line
        ctk.CTkFrame(sys_inner, height=2, fg_color=("#eee", "#444")).pack(fill="x", pady=15)

        # Nút đăng xuất
        ctk.CTkButton(sys_inner, text="Đăng xuất khỏi thiết bị", fg_color="#ff4d4d", hover_color="#cc0000", 
                      text_color="white", command=self.on_close, height=40).pack(fill="x")

    def _create_section_header(self, text):
        """Hàm hỗ trợ tạo tiêu đề nhỏ cho từng phần"""
        container = ctk.CTkFrame(self.settings_body, fg_color="transparent")
        container.pack(fill="x", pady=(5, 5))
        ctk.CTkLabel(container, text=text, font=("Segoe UI", 13, "bold"), text_color=ZALO_BLUE).pack(anchor="w")
        
        
    def open_settings_modal(self):
        """Thay thế việc mở cửa sổ mới bằng cách hiển thị frame cài đặt tích hợp"""
        self.main_frame.grid_remove() # Ẩn màn hình chat
        self.settings_view.grid(row=0, column=2, sticky="nsew") # Hiện màn hình settings ở cùng vị trí

    def close_settings_view(self):
        """Quay lại màn hình chat"""
        self.settings_view.grid_remove()
        self.main_frame.grid()

    def create_tool_btn(self, parent, icon, cmd, tooltip=""):
        btn = ctk.CTkButton(parent, text=icon, width=40, height=35, fg_color="transparent", 
                      text_color="#555", hover_color="#f0f0f0", font=("Segoe UI Emoji", 18), 
                      command=cmd)
        btn.pack(side="left", padx=2)
        if tooltip: ToolTip(btn, tooltip)
        return btn

    # =========================================================================
    # 4. CÁC HÀM XỬ LÝ SỰ KIỆN (INTERACTIONS)
    # =========================================================================
    
    # --- Chức năng Profile ---
    def build_profile_view(self):
        """Xây dựng khung hồ sơ cá nhân tích hợp"""
        self.profile_view = ctk.CTkFrame(self, corner_radius=0, fg_color=("white", "#1e1e1e"))

        # Header Profile
        profile_header = ctk.CTkFrame(self.profile_view, height=68, corner_radius=0, fg_color=("white", "#2b2b2b"))
        profile_header.pack(side="top", fill="x")

        btn_back = ctk.CTkButton(profile_header, text="⬅ Quay lại", width=100, height=35, fg_color=ZALO_BLUE,
                                 text_color="white", command=self.close_profile_view)
        btn_back.pack(side="left", padx=20, pady=15)

        ctk.CTkLabel(profile_header, text="Hồ sơ cá nhân", font=("Segoe UI", 18, "bold")).pack(side="left", padx=20)
        
        # Content Scrollable Frame
        content_frame = ctk.CTkFrame(self.profile_view, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Avatar Preview
        self.lbl_avatar_preview = ctk.CTkButton(content_frame, text=self.username[0].upper(), width=120, height=120, corner_radius=60,
                      fg_color=ZALO_BLUE, font=("Arial", 50, "bold"), hover=False)
        self.lbl_avatar_preview.pack(pady=(20, 10))
        
        # Upload Avatar Button
        def upload_avatar_handler():
            file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                    b64_data = base64.b64encode(data).decode('utf-8')
                    filename = os.path.basename(file_path)
                    
                    self.client_socket.sendall(Protocol.pack(f"CMD_UPDATE_AVATAR|{filename}|{b64_data}"))
                    messagebox.showinfo("Thông báo", "Đang tải ảnh lên...")
                except Exception as e:
                    messagebox.showerror("Lỗi", str(e))

        ctk.CTkButton(content_frame, text="📷 Đổi Avatar", width=120, fg_color="gray", command=upload_avatar_handler).pack(pady=10)
        
        # Edit Info Form
        form_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        form_frame.pack(pady=30)
        
        ctk.CTkLabel(form_frame, text="Tên hiển thị:", anchor="w", font=("Segoe UI", 14)).pack(fill="x", pady=(10,5))
        self.txt_profile_name = ctk.CTkEntry(form_frame, width=300, height=40)
        self.txt_profile_name.pack(fill="x", pady=5)
        self.txt_profile_name.insert(0, self.username)
        
        ctk.CTkLabel(form_frame, text="Email (ID):", anchor="w", font=("Segoe UI", 14)).pack(fill="x", pady=(15,5))
        self.txt_profile_email = ctk.CTkEntry(form_frame, width=300, height=40) 
        self.txt_profile_email.pack(fill="x", pady=5)
        if self.email:
             self.txt_profile_email.insert(0, self.email)

        def save_info():
            new_name = self.txt_profile_name.get()
            new_email = self.txt_profile_email.get()
            if not new_name or not new_email: return
            try:
                self.client_socket.sendall(Protocol.pack(f"CMD_UPDATE_INFO|{new_name}|{new_email}"))
                messagebox.showinfo("Thông báo", "Đã gửi yêu cầu cập nhật")
                # Update local username display if needed immediately, or wait for server confirmation/re-login
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

        ctk.CTkButton(form_frame, text="Lưu thông tin", command=save_info, width=200, height=40, font=("Segoe UI", 14, "bold")).pack(pady=40)

    def open_profile_modal(self):
        self.main_frame.grid_remove()
        self.profile_view.grid(row=0, column=2, sticky="nsew")

    def close_profile_view(self):
        self.profile_view.grid_remove()
        self.main_frame.grid()

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
            # Tạo nhóm mới
            self.create_group_action()
        elif self.current_tab == "CONTACT":
            messagebox.showinfo("Mới", "Thêm bạn mới")
        else:
            messagebox.showinfo("Mới", "Thêm công việc mới")

    def create_group_action(self):
        dialog = ctk.CTkInputDialog(text="Nhập tên nhóm mới:", title="Tạo nhóm")
        name = dialog.get_input()
        if name:
            # Gửi lệnh tạo nhóm
            try:
                self.client_socket.sendall(Protocol.pack(f"GROUP_CREATE|{name}"))
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

    def join_group_action(self):
        dialog = ctk.CTkInputDialog(text="Nhập tên nhóm muốn tham gia:", title="Tham gia nhóm")
        name = dialog.get_input()
        if name:
            try:
                self.client_socket.sendall(Protocol.pack(f"GROUP_JOIN|{name}"))
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

    def leave_group_action(self):
        if self.chat_mode != "GROUP": return
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn rời nhóm {self.target_name}?")
        if confirm:
            try:
                self.client_socket.sendall(Protocol.pack(f"GROUP_LEAVE|{self.target_name}"))
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

    def delete_group_action(self):
        if self.chat_mode != "GROUP": return
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa vĩnh viễn nhóm {self.target_name}?\n(Hành động này không thể hoàn tác)")
        if confirm:
            try:
                self.client_socket.sendall(Protocol.pack(f"GROUP_DELETE|{self.target_name}"))
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

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
        if f: 
            self.process_and_send_file(f)

    def send_image_action(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if f: 
            self.process_and_send_file(f)

    def send_video_action(self):
        f = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4;*.avi;*.mov;*.mkv")])
        if f:
            self.process_and_send_file(f)

    def process_and_send_file(self, filepath):
        """Xử lý gửi file trong luồng riêng để không treo UI"""
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)

        # 1. Check size (Limit: 200MB)
        if file_size > 200 * 1024 * 1024:
            messagebox.showwarning("File quá lớn", "Vui lòng chọn file nhỏ hơn 200MB.")
            return

        # 2. Thông báo đang gửi (Có thể hiện ProgressBar nếu muốn, ở đây dùng Label tạm)
        self.lbl_chat_name.configure(text=f"Đang gửi {filename} ({round(file_size/1024/1024, 1)} MB)...")
        # Đổi trỏ chuột để báo bận
        self.configure(cursor="watch")

        # 3. Worker Function (Chạy trong Thread)
        def _send_worker():
            try:
                # Đọc và Encode (Nặng)
                with open(filepath, "rb") as file:
                    b64_data = base64.b64encode(file.read()).decode('utf-8')
                
                # Gửi qua Socket (Nặng nếu mạng chậm)
                data = Protocol.pack(f"FILE|{filename}|{b64_data}")
                self.client_socket.sendall(data)

                # Callback Success (Về Main Thread)
                self.after(0, lambda: self._on_send_success(filename, b64_data))
            
            except Exception as e:
                # Callback Error
                self.after(0, lambda: self._on_send_error(str(e)))
        
        # 4. Start Thread
        threading.Thread(target=_send_worker, daemon=True).start()

    def _on_send_success(self, filename, b64_data):
        self.configure(cursor="")
        self.lbl_chat_name.configure(text="Phòng Chat Chung") # Reset title
        # Hiện bubble
        self.add_message_bubble("Bạn", filename, is_me=True, msg_type="file", file_data=b64_data)
        print(f"[CLIENT] Đã gửi file: {filename}")

    def _on_send_error(self, error_msg):
        self.configure(cursor="")
        self.lbl_chat_name.configure(text="Phòng Chat Chung (Lỗi Gửi)")
        messagebox.showerror("Lỗi gửi file", error_msg)

    # --- LOGIC MẠNG (CORE) ---
    # --- LOGIC MẠNG (CORE) ---
    def send_typing_signal(self):
        try:
            target = self.target_name if self.chat_mode == "GROUP" else "General"
            # Protocol: CMD_TYPING|target|username
            msg = f"CMD_TYPING|{target}|{self.username}"
            self.client_socket.sendall(Protocol.pack(msg))
        except: pass

    def show_typing_label(self, sender):
        self.lbl_typing.configure(text=f"{sender} đang gõ...")
        # Auto clear after 3s
        if hasattr(self, 'typing_clear_timer') and self.typing_clear_timer:
            self.after_cancel(self.typing_clear_timer)
        self.typing_clear_timer = self.after(3000, lambda: self.lbl_typing.configure(text=""))
    
    def send_msg(self, event=None):
        msg = self.entry_msg.get().strip()
        if not msg: return
        try:
            if self.chat_mode == "GROUP":
                # Gửi tin nhóm: GROUP_MSG|group_name|content
                data = Protocol.pack(f"GROUP_MSG|{self.target_name}|{msg}")
                self.client_socket.sendall(data)
                # Hiển thị ngay
                self.add_message_bubble("Bạn", msg, is_me=True, msg_type="text")
            else:
                # Private or General
                target = self.target_name if self.target_name else "General"
                # Protocol: MSG|receiver|content
                data = Protocol.pack(f"MSG|{target}|{msg}")
                self.client_socket.sendall(data)
                
                lbl = self.add_message_bubble("Bạn", msg, is_me=True, msg_type="text")
                
                # Queue for status update (Only for Private)
                if self.chat_mode == "PRIVATE" and target != "General":
                    if target not in self.msg_status_queues:
                        self.msg_status_queues[target] = []
                    # Append (Store weakref or just ref? Ref is fine as bubble exists)
                    if lbl: self.msg_status_queues[target].append(lbl)
            
            self.entry_msg.delete(0, "end")
        except: pass

    def update_user_list_ui(self, user_str=None):
        if self.current_tab != "MSG": return
        for w in self.user_scroll.winfo_children(): w.destroy()
        
        # 1. GROUPS SECTION
        if self.group_list_data:
            ctk.CTkLabel(self.user_scroll, text="NHÓM CỦA BẠN", font=("Segoe UI", 11, "bold"), text_color=("gray", "lightgray")).pack(anchor="w", padx=10, pady=(10,5))
            for g in self.group_list_data:
                # Active style
                is_selected = (self.chat_mode == "GROUP" and self.target_name == g)
                bg_color = ("#e5efff", "#3a3b3c") if is_selected else "transparent"
                
                frame = ctk.CTkFrame(self.user_scroll, fg_color=bg_color, corner_radius=6)
                frame.pack(fill="x", pady=2, padx=5)
                
                # Bind click
                frame.bind("<Button-1>", lambda e, name=g: self.select_chat_target("GROUP", name))
                
                btn_icon = ctk.CTkButton(frame, text="🛡️", width=35, height=35, corner_radius=10, 
                              fg_color="#ffecd1", text_color="#d97706", hover=False)
                btn_icon.pack(side="left", padx=10, pady=5)
                btn_icon.bind("<Button-1>", lambda e, name=g: self.select_chat_target("GROUP", name))

                lbl = ctk.CTkLabel(frame, text=g, font=("Segoe UI", 13, "bold"), text_color=("black", "white"))
                lbl.pack(side="left", anchor="w")
                lbl.bind("<Button-1>", lambda e, name=g: self.select_chat_target("GROUP", name))

                # Notification Dot
                count = self.unread_counts.get(g, 0)
                if count > 0:
                     ctk.CTkLabel(frame, text=f"{count}", width=20, height=20, corner_radius=10, 
                                  fg_color="red", text_color="white", font=("Arial", 10, "bold")).pack(side="right", padx=5)

        # 2. ONLINE USERS SECTION
        ctk.CTkLabel(self.user_scroll, text="TRỰC TUYẾN", font=("Segoe UI", 12, "bold"), text_color=("gray", "lightgray")).pack(anchor="w", padx=15, pady=(15,8))
        
        for u in self.user_list_data:
            frame = ctk.CTkFrame(self.user_scroll, fg_color="transparent")
            frame.pack(fill="x", pady=4, padx=5) # Increased spacing
            
            # Active State Logic
            is_active = (self.chat_mode == "PRIVATE" and self.target_name == u)
            
            # Background Color for Row
            bg_color = ("#e5efff", "#333333") if is_active else ("white", "#2b2b2b")
            
            # Hover effect frame
            inner_frame = ctk.CTkFrame(frame, fg_color=bg_color, corner_radius=10)
            inner_frame.pack(fill="x")
            
            # Avatar (Create & Pack First)
            avatar_color = ZALO_BLUE if u == self.username else ("#e6e8eb", "#3a3b3c")
            avatar_txt = "white" if u == self.username else ("#333", "white")
            
            # Determine command based on user
            cmd = self.open_profile_modal if u == self.username else lambda name=u: self.select_chat_target("PRIVATE", name)
            
            btn_avatar = ctk.CTkButton(inner_frame, text=u[0].upper(), width=40, height=40, corner_radius=20, 
                          fg_color=avatar_color, text_color=avatar_txt, hover=False, font=("Arial", 16, "bold"),
                          command=cmd)
            btn_avatar.pack(side="left", padx=10, pady=8)
            
            # Notification Dot (Unread)
            count = self.unread_counts.get(u, 0)
            if count > 0:
                 ctk.CTkLabel(inner_frame, text=f"{count}", width=22, height=22, corner_radius=11, 
                              fg_color="red", text_color="white", font=("Arial", 10, "bold")).pack(side="right", padx=10)
            
            # Info (Pack Second)
            info = ctk.CTkFrame(inner_frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)
            
            lbl_name = ctk.CTkLabel(info, text=u, font=("Segoe UI", 14, "bold"), text_color=("black", "white"))
            lbl_name.pack(anchor="w")
            
            lbl_status = ctk.CTkLabel(info, text="Online", font=("Segoe UI", 11), text_color="green")
            lbl_status.pack(anchor="w")

            # --- Bind Click Check ---
            # Chỉ bind click nếu KHÔNG phải chính mình
            if u != self.username:
                inner_frame.bind("<Button-1>", lambda e, name=u: self.select_chat_target("PRIVATE", name))
                info.bind("<Button-1>", lambda e, name=u: self.select_chat_target("PRIVATE", name))
                lbl_name.bind("<Button-1>", lambda e, name=u: self.select_chat_target("PRIVATE", name))
                lbl_status.bind("<Button-1>", lambda e, name=u: self.select_chat_target("PRIVATE", name))

    def select_chat_target(self, mode, name):
        self.chat_mode = mode
        self.target_name = name
        
        # Reset unread count
        # Reset unread count
        if name in self.unread_counts:
            self.unread_counts[name] = 0
        
        # Clear chat area (Giả lập chuyển phòng)
        for w in self.msg_area.winfo_children(): w.destroy()
        
        # Update Header
        if mode == "GROUP":
            self.lbl_chat_name.configure(text=f"Nhóm: {name}")
        elif mode == "PRIVATE":
            self.lbl_chat_name.configure(text=f"Chat với: {name}")
        else:
            self.lbl_chat_name.configure(text="Phòng Chat Chung")
            
        # Request History
        if mode in ["GROUP", "PRIVATE"]:
             # Send CMD_HISTORY|target|mode
             try:
                 self.client_socket.sendall(Protocol.pack(f"CMD_HISTORY|{name}|{mode}"))
             except: pass
        
        # Toggle Group Buttons
        if mode == "GROUP":
            self.btn_leave_group.pack(side="right", padx=5)
            self.btn_delete_group.pack(side="right", padx=5)
            ToolTip(self.btn_leave_group, "Rời nhóm")
            ToolTip(self.btn_delete_group, "Xóa nhóm (Admin)")
        else:
            self.btn_leave_group.pack_forget()
            self.btn_delete_group.pack_forget()

        # Refresh Sidebar UI (Refresh highlight)
        self.update_user_list_ui()

    def add_message_bubble(self, sender, content, is_me, msg_type="text", file_data=None, timestamp_str=None):
        if is_me:
            bg, align, anchor = ZALO_BUBBLE_ME, "right", "e"
            txt_col = TEXT_COLOR_ME
            sub_col = "#E8E8E8" # Lighter text for timestamp etc on blue bg
        else:
            bg, align, anchor = ZALO_BUBBLE_YOU, "left", "w"
            txt_col = TEXT_COLOR_YOU
            sub_col = "gray"

        row = ctk.CTkFrame(self.msg_area, fg_color="transparent")
        row.pack(fill="x", pady=2, padx=20) # Tighter vertical spacing

        if not is_me:
            # Avatar small
            ctk.CTkButton(row, text=sender[0], width=28, height=28, corner_radius=14, 
                          fg_color="#e6e8eb", text_color="#555", hover=False, font=("Arial", 10, "bold")).pack(side="left", anchor="s", pady=(0,5))

        # Bubble
        bubble = ctk.CTkFrame(row, fg_color=bg, corner_radius=18, border_width=0) # Rounder corners, no border
        bubble.pack(side=align, padx=(8 if not is_me else 0, 0), anchor=anchor, pady=2)

        if not is_me:
             ctk.CTkLabel(bubble, text=sender, font=("Segoe UI", 9, "bold"), text_color="gray").pack(anchor="w", padx=12, pady=(5,0))
        
        if msg_type == "text":
            # Font size 13, consistent padding
            msg_font = ("Segoe UI", 13)
            ctk.CTkLabel(bubble, text=content, font=msg_font, text_color=txt_col, wraplength=480, justify="left").pack(padx=12, pady=(8, 2))
        
        elif msg_type == "file":
            filename = content
            ext = filename.split('.')[-1].lower() if '.' in filename else ""
            
            # --- XỬ LÝ ẢNH ---
            if ext in ['png', 'jpg', 'jpeg']:
                try:
                    if file_data:
                        img_data = base64.b64decode(file_data)
                        pil_img = Image.open(io.BytesIO(img_data))
                        # Calc ratio to max 250px
                        w, h = pil_img.size
                        ratio = min(250/w, 250/h)
                        new_w, new_h = int(w*ratio), int(h*ratio)
                        
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
                        label = ctk.CTkLabel(bubble, text="", image=ctk_img)
                        label.pack(padx=5, pady=5)
                        
                        # Bind Click to Open Viewer
                        label.bind("<Button-1>", lambda e, p=pil_img, n=filename: self.open_image_viewer(p, n))
                        label.configure(cursor="hand2")
                    else:
                        ctk.CTkLabel(bubble, text=f"[Ảnh] {filename}", text_color="gray").pack(padx=12, pady=8)
                except Exception as e:
                    ctk.CTkLabel(bubble, text=f"[Lỗi Ảnh] {filename}", text_color="red").pack(padx=12, pady=8)

            # --- XỬ LÝ TEXT (PREVIEW) ---
            elif ext == 'txt':
                preview_text = f"📄 {filename}\n"
                try:
                    if file_data:
                        raw_txt = base64.b64decode(file_data).decode('utf-8')
                        # Lấy 300 ký tự đầu
                        short_txt = raw_txt[:300] + ("..." if len(raw_txt) > 300 else "")
                        preview_text += "-" * 20 + "\n" + short_txt
                except:
                    preview_text += "(Không thể đọc nội dung)"
                
                ctk.CTkLabel(bubble, text=preview_text, font=("Consolas", 11), text_color="black", justify="left", wraplength=400).pack(padx=12, pady=5)
                
                # Nút tải
                btn_text = "⬇ Tải về"
                ctk.CTkButton(bubble, text=btn_text, height=25, width=60, font=("Segoe UI", 11), fg_color="#e6f2ff", text_color="#0068ff", hover_color="#cce5ff",
                              command=lambda: self.save_file_local(filename, file_data)).pack(padx=12, pady=(0, 8), anchor="w")

            # --- XỬ LÝ VIDEO ---
            elif ext in ['mp4', 'avi', 'mov', 'mkv']:
                ctk.CTkLabel(bubble, text="🎥 " + filename, font=("Segoe UI", 13, "bold"), text_color="#e01b24").pack(padx=12, pady=(8,0), anchor="w")
                ctk.CTkLabel(bubble, text="(Video)", font=("Segoe UI", 10), text_color="gray").pack(padx=12, pady=(0,5), anchor="w")
                
                # Nút tải
                ctk.CTkButton(bubble, text="⬇ Lưu Video", height=25, width=80, font=("Segoe UI", 11), fg_color="#ffe6e6", text_color="#e01b24", hover_color="#ffd1d1",
                              command=lambda: self.save_file_local(filename, file_data)).pack(padx=12, pady=8, anchor="w")

            # --- FILE KHÁC ---
            else:
                ctk.CTkLabel(bubble, text="📁 " + filename, font=("Segoe UI", 13, "bold"), text_color="#0068ff").pack(padx=12, pady=(8,0), anchor="w")
                # Luôn hiện nút tải nếu có data
                if file_data: 
                     ctk.CTkButton(bubble, text="⬇ Tải về", height=25, width=60, font=("Segoe UI", 11), fg_color="#e6f2ff", text_color="#0068ff", hover_color="#cce5ff",
                                  command=lambda: self.save_file_local(filename, file_data)).pack(padx=12, pady=8, anchor="w")
                else:
                    ctk.CTkLabel(bubble, text="Đã gửi", font=("Segoe UI", 10), text_color="gray").pack(padx=12, pady=5, anchor="w")

        # --- TIME & STATUS FRAME ---
        info_frame = ctk.CTkFrame(bubble, fg_color="transparent")
        info_frame.pack(anchor="e", padx=10, pady=(0, 4))

        # 1. Timestamp
        import datetime
        ts = ""
        if timestamp_str:
            try:
                dt = datetime.datetime.strptime(timestamp_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                ts = dt.strftime("%H:%M")
            except: ts = timestamp_str
        else:
            ts = datetime.datetime.now().strftime("%H:%M")

        ts_col = "#999999" if not is_me else "#B0C4DE"
        ctk.CTkLabel(info_frame, text=ts, font=("Segoe UI", 9), text_color=ts_col).pack(side="left")

        # 2. Status Icon (Only for Me & Private Chat)
        status_lbl = None
        if is_me and self.chat_mode == "PRIVATE":
             # If timestamp_str is present (loaded from history), assume Sent (✔)
             # If None (sending live), assume Pending (...)
             code = "✔" if timestamp_str else "..." 
             status_lbl = ctk.CTkLabel(info_frame, text=code, font=("Arial", 10, "bold"), text_color=ts_col)
             status_lbl.pack(side="left", padx=(3, 0))
        
        return status_lbl # Return for queuing

        # Smart Auto-scroll
        # Only scroll if user is near bottom (e.g. within last 10%)
        # But if it's MY message, always scroll.
        try:
             y_pos = self.msg_area._parent_canvas.yview()[1]
             if is_me or y_pos > 0.9:
                 self.msg_area._parent_canvas.yview_moveto(1.0)
        except:
             pass

    def add_system_message(self, text):
        """Displays a centered system notification in the chat."""
        frame = ctk.CTkFrame(self.msg_area, fg_color="transparent")
        frame.pack(fill="x", pady=(10, 10)) # Increased vertical margin for less noise
        
        lbl = ctk.CTkLabel(frame, text=text, font=("Segoe UI", 11), text_color="gray50")
        lbl.pack(anchor="center")
        
        # Auto scroll for system messages too
        try:
             self.msg_area._parent_canvas.yview_moveto(1.0)
        except: pass

    def save_file_local(self, filename, b64_data):
        try:
            save_path = filedialog.asksaveasfilename(initialfile=filename, title="Lưu file")
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(b64_data))
                messagebox.showinfo("Thành công", f"Đã lưu file tại:\n{save_path}")
                os.startfile(os.path.dirname(save_path))
        except Exception as e:
            messagebox.showerror("Lỗi lưu file", str(e))

    def receive_loop(self):
        while self.is_running and self.client_socket:
            res_type = None # Initialize to avoid UnboundLocalError
            try:
                msg = Protocol.recv_msg_sync(self.client_socket)
                if not msg:
                    print("[CLIENT] Server closed connection.")
                    self.handle_disconnect()
                    break
                
                parts = msg.split("|")
                cmd = parts[0]

                if cmd == "MSG":
                    # MSG|sender|content
                    sender, content = parts[1], parts[2]
                    
                    if sender != self.username:
                        # Logic Chat 1-1 (Giả lập Private từ Broadcast)
                        # Chỉ hiển thị nếu đang chat với đúng người này
                        if self.chat_mode == "PRIVATE" and self.target_name == sender:
                             self.after(0, lambda s=sender, c=content: self.add_message_bubble(s, c, is_me=False, msg_type="text"))
                        else:
                             # Nếu đang ở nhóm hoặc người khác -> Tính là tin nhắn chờ (Unread)
                             self.unread_counts[sender] = self.unread_counts.get(sender, 0) + 1
                             self.after(0, self.update_user_list_ui)

                elif cmd == "GROUP_MSG":
                    # GROUP_MSG|group_name|sender|content
                    g_name, sender, content = parts[1], parts[2], parts[3]
                    
                    # Logic: Nếu đang ở trong Group đó thì hiện
                    if self.chat_mode == "GROUP" and self.target_name == g_name:
                        self.after(0, lambda s=sender, c=content: self.add_message_bubble(f"{s}", c, is_me=False, msg_type="text"))
                    else:
                        # Increment Unread Count
                        self.unread_counts[g_name] = self.unread_counts.get(g_name, 0) + 1
                        self.after(0, self.update_user_list_ui)

                elif cmd == "FILE":
                    # FILE|sender|filename|b64
                    sender, filename, b64 = parts[1], parts[2], parts[3]
                    if sender != self.username:
                        self.after(0, lambda s=sender, f=filename, b=b64: self.add_message_bubble(s, f, is_me=False, msg_type="file", file_data=b))

                elif cmd == "TYPING":
                     # TYPING|group|user
                     if len(parts) >= 3:
                         g_name, sender = parts[1], parts[2]
                         # Check context and self
                         # Check context and self
                         if sender != self.username:
                             # Allow General typing (if supported) OR Group typing OR Private Typing (sender == target_name)
                             if (self.chat_mode == "GROUP" and self.target_name == g_name) or \
                                (self.chat_mode == "PRIVATE" and (g_name == "General" or g_name == self.target_name)):
                                  self.after(0, lambda s=sender: self.show_typing_label(s))

                elif cmd == "GROUP_NOTIFY":
                    # GROUP_NOTIFY|group_name|content
                    g_name, notify_content = parts[1], parts[2]
                    # Show if in that group
                    if self.chat_mode == "GROUP" and self.target_name == g_name:
                        self.after(0, lambda t=notify_content: self.add_system_message(t))

                elif cmd == "LIST":
                    # LIST|u1,u2,...
                    if len(parts) > 1:
                        self.user_list_data = parts[1].split(",")
                        self.after(0, self.update_user_list_ui)

                elif cmd == "GROUPS":
                    # GROUPS|g1,g2,...
                    if len(parts) > 1:
                        self.group_list_data = parts[1].split(",") if parts[1] else []
                        self.after(0, self.update_user_list_ui)

                elif cmd == "GROUP_OK":
                    g_name = parts[1]
                    messagebox.showinfo("Thành công", f"Đã tham gia nhóm {g_name}")

                elif cmd == "ERR":
                    messagebox.showerror("Lỗi Server", parts[1])

                elif cmd == "GROUP_LEFT":
                    g_name = parts[1]
                    messagebox.showinfo("Thông báo", f"Bạn đã rời nhóm {g_name}")
                    if g_name in self.group_list_data:
                        self.group_list_data.remove(g_name)
                    if self.chat_mode == "GROUP" and self.target_name == g_name:
                         self.after(0, lambda: self.select_chat_target("HOME", "General")) # Về màn hình chính
                    self.after(0, self.update_user_list_ui)

                elif cmd == "GROUP_DELETED":
                    g_name = parts[1]
                    if g_name in self.group_list_data:
                        self.group_list_data.remove(g_name)
                        # Nếu đang xem nhóm đó thì đá ra
                        if self.chat_mode == "GROUP" and self.target_name == g_name:
                            messagebox.showwarning("Thông báo", f"Nhóm {g_name} đã bị giải tán.")
                            self.after(0, lambda: self.select_chat_target("HOME", "General"))
                    self.after(0, self.update_user_list_ui)

                elif cmd == "CMD_RES":
                    # CMD_RES|TYPE|STATUS|MSG
                    res_type, status, msg_content = parts[2], parts[3], parts[4]
                    if res_type == "PASS" and status == "True":
                        messagebox.showinfo("Thành công", "Đổi mật khẩu thành công")
                    elif res_type == "PASS":
                        messagebox.showerror("Lỗi", msg_content)

                elif cmd == "HISTORY_DATA":
                    # HISTORY_DATA|target|json_str
                    # target = parts[1] # Not actually needed if we trust the flow
                    # json_str is the rest (could contain pipes, so be careful with split)
                    # Use index to split
                    # msg is "HISTORY_DATA|target|json..."
                    try:
                        first_pipe = msg.find("|")
                        second_pipe = msg.find("|", first_pipe + 1)
                        json_str = msg[second_pipe+1:]
                        
                        import json
                        history = json.loads(json_str)
                        
                        # Only render if still looking at that target?
                        # Yes, or just render to current buffer. 
                        # Ideally check target matches self.target_name.
                        
                        # Render loop
                        self.after(0, lambda h=history: self.render_history(h))
                    except Exception as e:
                        print(f"Error parsing history: {e}")

                elif cmd == "MSG_SENT":
                    # MSG_SENT|receiver
                    if len(parts) >= 2:
                        receiver = parts[1]
                        # Update first "..." to "✔"
                        labels = self.msg_status_queues.get(receiver, [])
                        for lbl in labels:
                            try:
                                if lbl.cget("text") == "...":
                                    self.after(0, lambda l=lbl: l.configure(text="✔"))
                                    break
                            except: pass

                elif cmd == "MSG_DELIVERED":
                    # MSG_DELIVERED|receiver
                    if len(parts) >= 2:
                        receiver = parts[1]
                        # Update first "✔" or "..." to "✔✔"
                        labels = self.msg_status_queues.get(receiver, [])
                        for lbl in labels:
                            try:
                                txt = lbl.cget("text")
                                if txt == "..." or txt == "✔":
                                    self.after(0, lambda l=lbl: l.configure(text="✔✔"))
                                    break
                            except: pass

            except Exception as e:
                print(f"[RECV ERROR] {e}")
                self.handle_disconnect()
                break
    
    def open_image_viewer(self, pil_image, filename):
        """Mở cửa sổ xem ảnh phóng to với chức năng Zoom"""
        viewer = ctk.CTkToplevel(self)
        viewer.title(filename)
        viewer.geometry("800x600")
        viewer.attributes("-topmost", True)
        viewer.configure(fg_color="black")
        
        # State cho Zoom
        self.current_scale = 1.0
        self.base_image = pil_image.copy()
        
        # Canvas để hiển thị ảnh
        canvas = ctk.CTkCanvas(viewer, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Hàm hiển thị ảnh theo scale
        def update_image():
            w, h = self.base_image.size
            new_w = int(w * self.current_scale)
            new_h = int(h * self.current_scale)
            
            # Resize
            # Dùng LANCZOS hoặc BILINEAR cho đẹp
            resized = self.base_image.resize((new_w, new_h), Image.LANCZOS)
            
            # Convert sang PhotoImage (tkinter compatible)
            # Lưu ý: Phải giữ reference để không bị GC thu hồi
            from PIL import ImageTk
            self.tk_image = ImageTk.PhotoImage(resized)
            
            # Tính tọa độ giữa canvas
            cw = canvas.winfo_width()
            ch = canvas.winfo_height()
            x = cw // 2
            y = ch // 2
            
            canvas.delete("all")
            canvas.create_image(x, y, image=self.tk_image, anchor="center")

        # Handle Zoom (MouseWheel)
        def on_mouse_wheel(event):
            # Windows: event.delta = 120 (up) or -120 (down)
            if event.delta > 0:
                self.current_scale *= 1.1
            else:
                self.current_scale /= 1.1
            update_image()

        # Update lại ảnh khi resize cửa sổ
        viewer.bind("<Configure>", lambda e: update_image())
        
        # Bind MouseWheel
        viewer.bind("<MouseWheel>", on_mouse_wheel)
        
        # Click outside to close (Bind vào canvas)
        canvas.bind("<Button-1>", lambda e: viewer.destroy())
        
        # Nút Close (X)
        btn_close = ctk.CTkButton(viewer, text="✕", width=40, height=40, fg_color="transparent", 
                                  text_color="white", font=("Arial", 20, "bold"), hover_color="#333",
                                  command=viewer.destroy)
        btn_close.place(relx=0.95, rely=0.05, anchor="center")

        # Init lần đầu (delay nhẹ để canvas có kích thước)
        viewer.after(100, update_image)

    def on_close(self):
        self.is_running = False
        if self.client_socket: 
            try: self.client_socket.close()
            except: pass
            
        if self.on_logout_callback:
            self.on_logout_callback()
        else:
            self.destroy()

    def render_history(self, history):
        """Hiển thị danh sách tin nhắn lịch sử"""
        for msg in history:
            sender = msg.get('sender', 'Unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            msg_type = msg.get('type', 'text')
            
            is_me = (sender == self.username)
            self.add_message_bubble(sender, content, is_me, msg_type, file_data=None, timestamp_str=timestamp)
        
        # Force scroll to bottom after loading history
        try:
            self.msg_area._parent_canvas.yview_moveto(1.0)
        except: pass

    def heartbeat_loop(self):
        """Gửi PING định kỳ"""
        import time
        while self.is_running:
            if self.client_socket:
                try:
                    self.client_socket.sendall(Protocol.pack("PING"))
                except:
                    print("[HEARTBEAT] Ping failed!")
                    self.handle_disconnect()
                    break
            time.sleep(30) # 30s

# if __name__ == "__main__":
#     # Standalone testing not supported without MainApp
#     pass