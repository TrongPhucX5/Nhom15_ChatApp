import firebase_admin
from firebase_admin import credentials, db
import os
import datetime

class DBHandler:
    def __init__(self):
        # Đường dẫn: Từ file này (src/database) đi ra 2 cấp (../..) để về root -> vào assets
        base_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(base_dir, '../../assets/firebase_key.json')
        
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://chatapp-3ffc4-default-rtdb.asia-southeast1.firebasedatabase.app/' 
                    # ^^^ LINK CỦA BẠN ĐÃ ĐƯỢC GIỮ NGUYÊN
                })
                print("[DB] Đã kết nối Firebase!")
            except Exception as e:
                print(f"[DB] Lỗi kết nối Firebase: {e}")
                # Nếu lỗi đường dẫn, in ra để debug
                print(f"[DEBUG] Đang tìm key tại: {key_path}")

    def log_user(self, username):
        """Lưu thông tin user khi đăng nhập"""
        try:
            ref = db.reference(f'users/{username}')
            ref.update({
                'last_login': str(datetime.datetime.now()),
                'status': 'online'
            })
        except:
            pass

    def save_message(self, sender, msg):
        """Lưu tin nhắn vào lịch sử"""
        try:
            ref = db.reference('messages')
            ref.push({
                'sender': sender,
                'content': msg,
                'timestamp': str(datetime.datetime.now())
            })
        except:
            pass