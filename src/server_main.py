import asyncio
import sys
import os
import jwt
import datetime
from dotenv import load_dotenv

# --- 1. Setup Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Load env variables
load_dotenv(os.path.join(os.path.dirname(current_dir), '.env'))

# --- 2. Import Modules ---
try:
    from database.sqlite_db import DBHandler
    has_db = True
    print(" [SERVER] Đã kết nối module SQLite Database.")
except ImportError:
    print(" [SERVER] Cảnh báo: Không tìm thấy DB.")
    has_db = False

from core.protocol import Protocol

HOST = '127.0.0.1'
PORT = 65432
SECRET_KEY = os.getenv("SECRET_KEY", "DEFAULT_SECRET_KEY_IF_MISSING")
print(f" [CONFIG] Loaded SECRET_KEY: {'***' if SECRET_KEY else 'None'}")

class AsyncChatServer:
    def __init__(self):

        self.clients = {} # {writer: username}
        self.client_emails = {} # {writer: email}
        self.db = DBHandler() if has_db else None

    # --- JWT UTILS ---
    def generate_token(self, email, username):
        payload = {
            "email": email,
            "username": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return token

    # --- BROADCAST ---
    async def broadcast(self, message: str, exclude_writer=None):
        encoded_msg = Protocol.pack(message)
        disconnected_clients = []

        # 1. TCP
        for writer in self.clients:
            if writer == exclude_writer:
                continue
            try:
                writer.write(encoded_msg)
                await writer.drain()
            except Exception:
                disconnected_clients.append(writer)

        for w in disconnected_clients:
            self.remove_client(w)

    def remove_client(self, writer):
        if writer in self.clients:
            username = self.clients[writer]
            del self.clients[writer]
            if writer in self.client_emails:
                del self.client_emails[writer]
            print(f" [EXIT] {username} đã ngắt kết nối.")
            try: writer.close()
            except: pass
            asyncio.create_task(self.broadcast_user_list())

    async def broadcast_user_list(self):
        users = list(self.clients.values())
        msg = "LIST|" + ",".join(users)
        await self.broadcast(msg)

    # --- HELPER: FILE SAVING (BLOCKING I/O) ---
    def save_file_to_disk(self, file_path, b64_data):
        import base64
        try:
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            return True, None
        except Exception as e:
            return False, str(e)

    async def broadcast_group(self, group_name, message, exclude_writer=None):
        """Gửi tin nhắn chỉ cho thành viên trong nhóm"""
        if not self.db: return
        loop = asyncio.get_running_loop()
        members = await loop.run_in_executor(None, self.db.get_group_members, group_name)
        print(f" [DEBUG] Group '{group_name}' members: {members}")
        
        encoded_msg = Protocol.pack(message)
        
        # 1. TCP
        for writer, username in self.clients.items():
            if username in members and writer != exclude_writer:
                try:
                    writer.write(encoded_msg)
                    await writer.drain()
                    print(f" [DEBUG] Sent to {username}")
                except Exception as e:
                     print(f" [DEBUG] Failed to send to {username}: {e}")

    # --- HANDLE CLIENT ---
    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f" [CONN] Kết nối mới từ {addr}")
        
        username = "Unknown"
        isAuthenticated = False
        
        try:
            # Vòng lặp Auth: Yêu cầu Login/Register cho đến khi Authenticated
            while not isAuthenticated:
                msg = await Protocol.recv_msg(reader)
                if not msg: return # Ngắt kết nối

                if msg.startswith("AUTH|"):
                    parts = msg.split("|")
                    cmd = parts[1] # REGISTER or LOGIN

                    if cmd == "REGISTER" and len(parts) == 5:
                        # AUTH|REGISTER|email|pass|name
                        email, password, name = parts[2], parts[3], parts[4]
                        
                        # Chạy DB trong executor để không chặn Loop
                        if self.db:
                            loop = asyncio.get_running_loop()
                            success, reason = await loop.run_in_executor(None, self.db.register_user, email, password, name)
                            
                            if success:
                                response = f"AUTH|SUCCESS|RegOK"
                            else:
                                response = f"AUTH|FAIL|{reason}"
                        else:
                            response = "AUTH|FAIL|ServerNoDB"
                        
                        writer.write(Protocol.pack(response))
                        await writer.drain()

                    elif cmd == "LOGIN" and len(parts) == 4:
                        # AUTH|LOGIN|email|pass
                        email, password = parts[2], parts[3]
                        
                        if self.db:
                            loop = asyncio.get_running_loop()
                            success, user_name_db = await loop.run_in_executor(None, self.db.check_login, email, password)
                            
                            if success:
                                token = self.generate_token(email, user_name_db)
                                username = user_name_db
                                isAuthenticated = True
                                self.clients[writer] = username
                                self.client_emails[writer] = email
                                
                                response = f"AUTH|SUCCESS|{token}|{username}"
                                print(f" [LOGIN] {username} đã tham gia.")
                            else:
                                response = "AUTH|FAIL|Sai tài khoản hoặc mật khẩu"
                        else:
                            response = "AUTH|FAIL|ServerNoDB"

                        writer.write(Protocol.pack(response))
                        await writer.drain()
                    else:
                        writer.write(Protocol.pack("AUTH|FAIL|InvalidCommand"))
                        await writer.drain()
                else:
                    # Chưa login mà gửi tin nhắn khác -> Đóng
                    writer.write(Protocol.pack("AUTH|FAIL|PleaseLoginFirst"))
                    await writer.drain()
                    return 

            # --- SAU KHI LOGIN THÀNH CÔNG ---
            self.clients[writer] = username
            print(f" [LOGIN] {username} đã tham gia.")
            await self.broadcast_user_list()

            # Gửi danh sách nhóm đã tham gia
            if self.db:
                loop = asyncio.get_running_loop()
                user_groups = await loop.run_in_executor(None, self.db.get_user_groups, username)
                if user_groups:
                    writer.write(Protocol.pack(f"GROUPS|{','.join(user_groups)}"))
                    await writer.drain()

            # Vòng lặp Chat chính
            while True:
                msg = await Protocol.recv_msg(reader)
                if not msg: break
                
                # --- XỬ LÝ LỆNH ---
                if msg.startswith("MSG|"):
                    content = msg.split("|")[1]
                    print(f"💬 [{username}]: {content}")
                    if self.db: 
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, self.db.save_message, username, content, "text", None)
                    response = f"MSG|{username}|{content}"
                    await self.broadcast(response, exclude_writer=writer)

                elif msg.startswith("GROUP_CREATE|"):
                    # GROUP_CREATE|group_name
                    g_name = msg.split("|")[1]
                    if self.db:
                        loop = asyncio.get_running_loop()
                        success, res = await loop.run_in_executor(None, self.db.create_group, g_name, username)
                        if success:
                            writer.write(Protocol.pack(f"GROUP_OK|{g_name}"))
                            # Gửi lại list group cập nhật
                            user_groups = await loop.run_in_executor(None, self.db.get_user_groups, username)
                            writer.write(Protocol.pack(f"GROUPS|{','.join(user_groups)}"))
                        else:
                            writer.write(Protocol.pack(f"ERR|{res}"))
                        await writer.drain()

                elif msg.startswith("GROUP_MSG|"):
                    # GROUP_MSG|group_name|content
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        g_name = parts[1]
                        content = parts[2]
                        print(f"🛡️ [{username} -> {g_name}]: {content}")
                        # Broadcast group
                        await self.broadcast_group(g_name, f"GROUP_MSG|{g_name}|{username}|{content}", exclude_writer=writer)

                elif msg.startswith("GROUP_JOIN|"):
                     # GROUP_JOIN|group_name
                    g_name = msg.split("|")[1]
                    if self.db:
                        loop = asyncio.get_running_loop()
                        success, res = await loop.run_in_executor(None, self.db.add_group_member, g_name, username)
                        if success:
                            writer.write(Protocol.pack(f"GROUP_OK|{g_name}"))
                            # Update group list
                            user_groups = await loop.run_in_executor(None, self.db.get_user_groups, username)
                            writer.write(Protocol.pack(f"GROUPS|{','.join(user_groups)}"))
                        else:
                            writer.write(Protocol.pack(f"ERR|{res}"))
                        await writer.drain()

                elif msg.startswith("GROUP_LEAVE|"):
                    g_name = msg.split("|")[1]
                    if self.db:
                        loop = asyncio.get_running_loop()
                        success, res = await loop.run_in_executor(None, self.db.remove_group_member, g_name, username)
                        if success:
                            writer.write(Protocol.pack(f"GROUP_LEFT|{g_name}"))
                            await self.broadcast_group(g_name, f"GROUP_MSG|{g_name}|System|{username} đã rời nhóm.", exclude_writer=writer)
                            user_groups = await loop.run_in_executor(None, self.db.get_user_groups, username)
                            writer.write(Protocol.pack(f"GROUPS|{','.join(user_groups)}"))
                        else:
                            writer.write(Protocol.pack(f"ERR|{res}"))
                        await writer.drain()

                elif msg.startswith("GROUP_DELETE|"):
                    g_name = msg.split("|")[1]
                    if self.db:
                        loop = asyncio.get_running_loop()
                        members = await loop.run_in_executor(None, self.db.get_group_members, g_name)
                        success, res = await loop.run_in_executor(None, self.db.delete_group, g_name, username)
                        if success:
                            encoded_del = Protocol.pack(f"GROUP_DELETED|{g_name}")
                            for w, u in self.clients.items():
                                if u in members:
                                    try:
                                        w.write(encoded_del)
                                        # Refresh list
                                        groups = await loop.run_in_executor(None, self.db.get_user_groups, u)
                                        w.write(Protocol.pack(f"GROUPS|{','.join(groups)}"))
                                        await w.drain()
                                    except: pass
                        else:
                            writer.write(Protocol.pack(f"ERR|{res}"))
                        await writer.drain()

                        await writer.drain()

                # --- USER MANAGEMENT ---
                elif msg.startswith("CMD_PASS_CHANGE|"):
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        old_p, new_p = parts[1], parts[2]
                        if self.db and writer in self.client_emails:
                            loop = asyncio.get_running_loop()
                            res, msg_res = await loop.run_in_executor(None, self.db.update_password, self.client_emails[writer], old_p, new_p)
                            writer.write(Protocol.pack(f"CMD_RES|PASS|{str(res)}|{msg_res}"))
                            await writer.drain()

                elif msg.startswith("CMD_UPDATE_INFO|"):
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        new_name, new_email = parts[1], parts[2]
                        if self.db and writer in self.client_emails:
                            current_email = self.client_emails[writer]
                            loop = asyncio.get_running_loop()
                            res, msg_res = await loop.run_in_executor(None, self.db.update_info, current_email, new_name, new_email)
                            if res:
                                # Update in-memory session if email changed
                                self.client_emails[writer] = new_email
                                self.clients[writer] = new_name
                                # TODO: Broadcast name change?
                            writer.write(Protocol.pack(f"CMD_RES|INFO|{str(res)}|{msg_res}"))
                            await writer.drain()

                elif msg.startswith("CMD_UPDATE_AVATAR|"):
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        filename, b64_data = parts[1], parts[2]
                        if self.db and writer in self.client_emails:
                             # Save file
                             if not os.path.exists("uploads/avatars"):
                                 os.makedirs("uploads/avatars")
                             
                             fname_secure = f"{self.client_emails[writer]}_{datetime.datetime.now().strftime('%M%S')}_{filename}"
                             file_path = f"uploads/avatars/{fname_secure}"
                             
                             try:
                                 with open(file_path, "wb") as f:
                                     f.write(base64.b64decode(b64_data))
                                 
                                 loop = asyncio.get_running_loop()
                                 res, msg_res = await loop.run_in_executor(None, self.db.update_avatar, self.client_emails[writer], file_path)
                                 writer.write(Protocol.pack(f"CMD_RES|AVATAR|{str(res)}|{file_path}"))
                             except Exception as e:
                                 writer.write(Protocol.pack(f"CMD_RES|AVATAR|False|{str(e)}"))
                             await writer.drain()
                
                elif msg.startswith("CMD_TYPING|"):
                    # CMD_TYPING|target|sender
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        target, sender = parts[1], parts[2]
                        # Broadcast TYPING|target|sender to appropriate people
                        if target == "General":
                             # Broadcast to all except sender
                             await self.broadcast(f"TYPING|{target}|{sender}", exclude_writer=writer)
                        else:
                             # Broadcast to Group
                             await self.broadcast_group(target, f"TYPING|{target}|{sender}", exclude_writer=writer)
                             
                elif msg.startswith("CMD_GET_INFO"):
                    if self.db and writer in self.client_emails:
                        loop = asyncio.get_running_loop()
                        info = await loop.run_in_executor(None, self.db.get_user_info, self.client_emails[writer])
                        if info:
                            # INFO|name|email|avatar
                            avt = info['avatar'] if info['avatar'] else ""
                            writer.write(Protocol.pack(f"CMD_RES|GET_INFO|{info['username']}|{info['email']}|{avt}"))
                        else:
                            writer.write(Protocol.pack("CMD_RES|GET_INFO|Error|Error|"))
                        await writer.drain()

                elif msg.startswith("FILE|"):
                    # FILE|filename|base64_string
                    parts = msg.split("|")
                    if len(parts) >= 3:
                        filename = parts[1]
                        b64_data = parts[2]
                        
                        # Tạo thư mục uploads nếu chưa có
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        
                        file_path = f"uploads/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                        
                        # Sử dụng run_in_executor để lưu file không chặn main loop
                        loop = asyncio.get_running_loop()
                        success, error = await loop.run_in_executor(None, self.save_file_to_disk, file_path, b64_data)

                        if success:
                            print(f"📁 [{username}] Gửi file: {filename}")
                            if self.db:
                                await loop.run_in_executor(None, self.db.save_message, username, filename, "file", file_path)

                            # Broadcast: FILE|username|filename|b64_data
                            response = f"FILE|{username}|{filename}|{b64_data}"
                            await self.broadcast(response, exclude_writer=writer)
                        else:
                            print(f"[ERR] Save File Failed: {error}")

        except Exception as e:
            print(f" [ERR] Lỗi xử lý client {username}: {e}")
        finally:
            self.remove_client(writer)

    async def start(self):
        server = await asyncio.start_server(self.handle_client, HOST, PORT)
        addr = server.sockets[0].getsockname()
        print(f" [SERVER] Đang chạy Asynchronous tại {addr}")
        print(" [INFO] Sẵn sàng chấp nhận JWT Authentication...")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    try:
        server = AsyncChatServer()
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print(" [STOP] Server đã dừng.")