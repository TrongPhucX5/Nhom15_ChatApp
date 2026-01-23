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
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        # Bảng Users cập nhật thêm email và password
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                username TEXT,
                password TEXT,
                last_login TEXT,
                status TEXT,
                avatar TEXT
            )
        ''')

        # Migration: Add avatar column if not exists
        try:
            conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
        except: pass
        
        # Bảng Messages (Cập nhật cho chat_v2: thêm msg_type, file_path, receiver)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                receiver TEXT,
                content TEXT,
                timestamp TEXT,
                msg_type TEXT DEFAULT 'text',
                file_path TEXT
            )
        ''')
        
        # Migration: Add receiver column if not exists
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN receiver TEXT")
        except: pass
        
        # Bảng Groups
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                created_by TEXT,
                created_at TEXT
            )
        ''')

        # Bảng Group Members
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                username TEXT,
                role TEXT,
                UNIQUE(group_id, username)
            )
        ''')
        
        # Bảng Reactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                username TEXT,
                emoji TEXT,
                timestamp TEXT,
                UNIQUE(message_id, username, emoji)
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

    # --- GROUP METHODS ---
    def create_group(self, name, created_by):
        """Tạo nhóm mới và thêm người tạo làm admin"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            now = str(datetime.datetime.now())
            cursor.execute("INSERT INTO groups (name, created_by, created_at) VALUES (?, ?, ?)", (name, created_by, now))
            group_id = cursor.lastrowid
            
            # Add creator as admin
            cursor.execute("INSERT INTO group_members (group_id, username, role) VALUES (?, ?, ?)", (group_id, created_by, 'admin'))
            
            conn.commit()
            conn.close()
            return True, group_id
        except sqlite3.IntegrityError:
            return False, "Tên nhóm đã tồn tại"
        except Exception as e:
            return False, str(e)

    def add_group_member(self, group_name, username, role='member'):
        """Thêm thành viên vào nhóm"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Get Group ID
            cursor.execute("SELECT id FROM groups WHERE name=?", (group_name,))
            row = cursor.fetchone()
            if not row: return False, "Nhóm không tồn tại"
            group_id = row[0]
            
            cursor.execute("INSERT INTO group_members (group_id, username, role) VALUES (?, ?, ?)", (group_id, username, role))
            
            conn.commit()
            conn.close()
            return True, "Success"
        except sqlite3.IntegrityError:
            return False, "User đã ở trong nhóm"
        except Exception as e:
            return False, str(e)

    def remove_group_member(self, group_name, username):
        """Xóa thành viên khỏi nhóm (Rời nhóm)"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM groups WHERE name=?", (group_name,))
            row = cursor.fetchone()
            if not row: return False, "Nhóm không tồn tại"
            group_id = row[0]
            
            cursor.execute("DELETE FROM group_members WHERE group_id=? AND username=?", (group_id, username))
            conn.commit()
            conn.close()
            return True, "Đã rời nhóm"
        except Exception as e:
            return False, str(e)

    def delete_group(self, group_name, username):
        """Xóa nhóm (Chỉ Admin/Creator thực hiện được)"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, created_by FROM groups WHERE name=?", (group_name,))
            row = cursor.fetchone()
            if not row: return False, "Nhóm không tồn tại"
            group_id, created_by = row
            
            if created_by != username:
                return False, "Bạn không phải Admin nhóm này"
            
            cursor.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
            cursor.execute("DELETE FROM groups WHERE id=?", (group_id,))
            
            conn.commit()
            conn.close()
            return True, "Đã xóa nhóm"
        except Exception as e:
            return False, str(e)

    def get_user_groups(self, username):
        """Lấy danh sách nhóm mà user tham gia"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT g.name FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.username = ?
            ''', (username,))
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows]
        except: return []

    def get_group_members(self, group_name):
        """Lấy danh sách thành viên của nhóm (để broadcast)"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT gm.username FROM group_members gm
                JOIN groups g ON g.id = gm.group_id
                WHERE g.name = ?
            ''', (group_name,))
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows]
        except: return []

    # ... (Keep existing methods register_user, check_login, etc.) ...
    # ... (Keep existing methods register_user, check_login, etc.) ...
    def save_message(self, sender, receiver, msg, msg_type="text", file_path=None):
        """Lưu tin nhắn (Text hoặc File) vào lịch sử"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().strftime("%H:%M") # Just HH:MM for now, or full time? DB usually stores full time.
            # Let's store full timestamp for sorting, client formats to HH:MM
            now_full = str(datetime.datetime.now())

            cursor.execute('''
                INSERT INTO messages (sender, receiver, content, timestamp, msg_type, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sender, receiver, msg, now_full, msg_type, file_path))
            
            message_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return message_id
        except Exception as e:
            print(f"[DB] Lỗi save_message: {e}")
            return None

    def get_history(self, user1, user2, limit=50):
        """Lấy lịch sử chat riêng giữa 2 user"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Query messages where (sender=u1 AND receiver=u2) OR (sender=u2 AND receiver=u1)
            cursor.execute('''
                SELECT id, sender, content, timestamp, msg_type, file_path 
                FROM messages 
                WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
                ORDER BY id DESC LIMIT ?
            ''', (user1, user2, user2, user1, limit))
            
            rows = cursor.fetchall()
            conn.close()
            # Reverse to return oldest first -> Client appends to bottom
            return rows[::-1] 
        except: return []

    def get_group_history(self, group_name, limit=50):
        """Lấy lịch sử chat nhóm"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Query messages where receiver=group_name
            cursor.execute('''
                SELECT id, sender, content, timestamp, msg_type, file_path
                FROM messages
                WHERE receiver=?
                ORDER BY id DESC LIMIT ?
            ''', (group_name, limit))
            
            rows = cursor.fetchall()
            conn.close()
            return rows[::-1]
        except: return []

    def register_user(self, email, password, username):
        """Đăng ký tài khoản mới"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
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
            conn = sqlite3.connect(self.db_path, timeout=30)
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
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            now = str(datetime.datetime.now())
            
            cursor.execute('''
                UPDATE users SET last_login=?, status='online' WHERE email=?
            ''', (now, email))
            
            conn.commit()
            conn.close()
        except: pass

    # --- ADVANCED FEATURES ---
    def update_password(self, email, old_pass, new_pass):
        """Đổi mật khẩu"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Verify old pass
            cursor.execute("SELECT password FROM users WHERE email=?", (email,))
            row = cursor.fetchone()
            if not row: return False, "Tài khoản không tồn tại"
            
            stored_hash = row[0]
            if not bcrypt.checkpw(old_pass.encode('utf-8'), stored_hash.encode('utf-8')):
                return False, "Mật khẩu cũ không đúng"
            
            # Hash new pass
            salt = bcrypt.gensalt()
            new_hashed = bcrypt.hashpw(new_pass.encode('utf-8'), salt).decode('utf-8')
            
            cursor.execute("UPDATE users SET password=? WHERE email=?", (new_hashed, email))
            conn.commit()
            conn.close()
            return True, "Đổi mật khẩu thành công"
        except Exception as e:
            return False, str(e)

    def update_info(self, current_email, new_name, new_email):
        """Cập nhật thông tin (Tên, Email)"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Check duplicate email if changed
            if current_email != new_email:
                cursor.execute("SELECT email FROM users WHERE email=?", (new_email,))
                if cursor.fetchone():
                    return False, "Email mới đã tồn tại"
            
            cursor.execute("UPDATE users SET username=?, email=? WHERE email=?", (new_name, new_email, current_email))
            conn.commit()
            conn.close()
            return True, "Cập nhật thông tin thành công"
        except Exception as e:
            return False, str(e)

    def update_avatar(self, email, avatar_path):
        """Cập nhật đường dẫn Avatar"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET avatar=? WHERE email=?", (avatar_path, email))
            conn.commit()
            conn.close()
            return True, "Cập nhật avatar thành công"
        except Exception as e:
            return False, str(e)

    def get_user_info(self, email):
        """Lấy thông tin profile"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            cursor.execute("SELECT username, email, avatar FROM users WHERE email=?", (email,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"username": row[0], "email": row[1], "avatar": row[2]}
            return None
        except: return None

    # Giữ lại hàm cũ để tránh lỗi gọi từ Server (nếu có)
    def log_user(self, username):
        pass # Đã xử lý trong check_login

    # --- REACTION METHODS ---
    def add_reaction(self, message_id, username, emoji):
        """Thêm reaction cho tin nhắn. Nếu đã react cùng emoji -> toggle off (xóa)"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            # Check nếu đã react emoji này
            cursor.execute('''
                SELECT id FROM reactions 
                WHERE message_id=? AND username=? AND emoji=?
            ''', (message_id, username, emoji))
            
            if cursor.fetchone():
                # Đã react -> Xóa (toggle off)
                cursor.execute('''
                    DELETE FROM reactions 
                    WHERE message_id=? AND username=? AND emoji=?
                ''', (message_id, username, emoji))
                conn.commit()
                conn.close()
                return "removed"
            else:
                # Chưa react -> Thêm mới
                now = str(datetime.datetime.now())
                cursor.execute('''
                    INSERT INTO reactions (message_id, username, emoji, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (message_id, username, emoji, now))
                conn.commit()
                conn.close()
                return "added"
        except Exception as e:
            print(f"[DB] Lỗi add_reaction: {e}")
            return "error"

    def get_message_reactions(self, message_id):
        """Lấy tất cả reactions của một tin nhắn
        Returns: {"❤️": ["Alice", "Bob"], "👍": ["Charlie"]}
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT emoji, username FROM reactions 
                WHERE message_id=?
                ORDER BY timestamp ASC
            ''', (message_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Group by emoji
            reactions = {}
            for emoji, username in rows:
                if emoji not in reactions:
                    reactions[emoji] = []
                reactions[emoji].append(username)
            
            return reactions
        except Exception as e:
            print(f"[DB] Lỗi get_message_reactions: {e}")
            return {}
