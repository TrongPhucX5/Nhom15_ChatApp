import sqlite3
import os
import datetime
import bcrypt

class DBHandler:
    def __init__(self, db_name="chat_v2.db"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, db_name)
        self._init_db()

    def _init_db(self):
        """Khởi tạo bảng nếu chưa có"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bảng Users cập nhật thêm email và password
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                username TEXT,
                password TEXT,
                last_login TEXT,
                status TEXT
            )
        ''')
        
        # Bảng Messages (Cập nhật cho chat_v2: thêm msg_type, file_path)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                content TEXT,
                timestamp TEXT,
                msg_type TEXT DEFAULT 'text',
                file_path TEXT
            )
        ''')
        
        # Seed Default Admin
        cursor.execute("SELECT * FROM users WHERE email='admin'")
        if not cursor.fetchone():
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw("123456".encode('utf-8'), salt).decode('utf-8')
            now = str(datetime.datetime.now())
            cursor.execute('''
                INSERT INTO users (email, username, password, last_login, status)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin', 'System Admin', hashed, now, 'online'))
            print("[DB] Đã tạo tài khoản admin/123456")

        conn.commit()
        conn.close()
        print(f"[DB] SQLite đã sẵn sàng tại: {self.db_path}")

    # ... (省略 register_user, check_login, log_user_login) ...

    def save_message(self, sender, msg, msg_type="text", file_path=None):
        """Lưu tin nhắn (Text hoặc File) vào lịch sử"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = str(datetime.datetime.now())
            
            cursor.execute('''
                INSERT INTO messages (sender, content, timestamp, msg_type, file_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (sender, msg, now, msg_type, file_path))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Lỗi save_message: {e}")

    def register_user(self, email, password, username):
        """Đăng ký tài khoản mới"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Hash mật khẩu
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

            now = str(datetime.datetime.now())
            
            cursor.execute('''
                INSERT INTO users (email, username, password, last_login, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, username, hashed.decode('utf-8'), now, 'online'))
            
            conn.commit()
            conn.close()
            return True, "Đăng ký thành công"
        except sqlite3.IntegrityError:
            return False, "Email đã tồn tại"
        except Exception as e:
            return False, f"Lỗi DB: {e}"

    def check_login(self, email, password):
        """Kiểm tra đăng nhập"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT password, username FROM users WHERE email=?", (email,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return False, None
            
            stored_hash, username = row
            
            # Kiểm tra mật khẩu
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                # Update last login
                self.log_user_login(email)
                return True, username
            else:
                return False, None
        except Exception as e:
            print(f"[DB] Check Login Error: {e}")
            return False, None

    def log_user_login(self, email):
        """Cập nhật giờ đăng nhập"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = str(datetime.datetime.now())
            
            cursor.execute('''
                UPDATE users SET last_login=?, status='online' WHERE email=?
            ''', (now, email))
            
            conn.commit()
            conn.close()
        except: pass

    # Giữ lại hàm cũ để tránh lỗi gọi từ Server (nếu có)
    def log_user(self, username):
        pass # Đã xử lý trong check_login


