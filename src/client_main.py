import sys
import os

# --- THÊM ĐƯỜNG DẪN ĐỂ IMPORT MODULE ---
# Giúp python tìm thấy folder 'ui' và 'database'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ui.login_window import LoginWindow
    from ui.chat_window import ChatAppClient
except ImportError as e:
    print("LỖI IMPORT: Không tìm thấy file giao diện!")
    print("Hãy chắc chắn bạn đã tạo file login_window.py và chat_window.py trong thư mục src/ui/")
    print(f"Chi tiết lỗi: {e}")
    sys.exit()

def main():
    # --- HÀM CHUYỂN ĐỔI TỪ LOGIN SANG CHAT ---
    def on_login_success(username):
        print(f"[SYSTEM] Đăng nhập thành công! User: {username}")
        print("[SYSTEM] Đang mở giao diện Chat...")
        
        # Sau khi LoginWindow tự hủy (destroy), ta khởi tạo ChatAppClient
        # Lưu ý: ChatAppClient là một mainloop mới
        try:
            chat_app = ChatAppClient(username_from_login=username)
            # app.mainloop() đã được gọi bên trong __init__ của ChatAppClient rồi 
            # (nếu bạn dùng code chat_window.py tôi đưa ở bước trước)
        except Exception as e:
            print(f"Lỗi khi mở Chat: {e}")

    # --- CHẠY MÀN HÌNH LOGIN TRƯỚC ---
    print("[SYSTEM] Đang khởi động ứng dụng...")
    # Khi login thành công, hàm on_login_success sẽ được gọi
    LoginWindow(on_login_success_callback=on_login_success)

if __name__ == "__main__":
    main()