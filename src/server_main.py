import asyncio
import sys
import os
import jwt
import ssl
import datetime
import base64
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
        print(f"[SSL] Handshake thành công với {addr}")
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
                        if writer in self.clients:
                             print(f" [AUTH] Ignored duplicate LOGIN from writer={id(writer)} (User: {self.clients[writer]})")
                             return

                        email, password = parts[2], parts[3]
                        print(f" [DEBUG] Processing LOGIN for email={email} writer={id(writer)}")
                        
                        if self.db:
                            loop = asyncio.get_running_loop()
                            success, user_name_db = await loop.run_in_executor(None, self.db.check_login, email, password)
                            
                            if success:
                                # CHECK DUPLICATE LOGIN
                                existing_writer = None
                                for w, u in list(self.clients.items()):
                                    if u == user_name_db:
                                        existing_writer = w
                                        break
                                
                                if existing_writer:
                                    print(f" [AUTH] {user_name_db} login from new device. Kicking old session.")
                                    try:
                                        existing_writer.write(Protocol.pack("FORCE_LOGOUT|Tài khoản nãy đã đăng nhập ở nơi khác."))
                                        await existing_writer.drain()
                                        existing_writer.close()
                                    except: pass
                                    self.remove_client(existing_writer)

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

            # Vòng lặp Chat chính (Refactored)
            while True:
                msg = await Protocol.recv_msg(reader)
                if not msg: break
                
                await self._process_command(msg, writer, username)
        except ConnectionResetError:
            print(f" [INFO] Client {username} disconnected (ConnectionReset).")
        except asyncio.IncompleteReadError:
            print(f" [INFO] Client {username} disconnected (IncompleteRead).")
        except Exception as e:
            print(f" [ERR] Unexpected error with {username}: {e} (Type: {type(e).__name__})")
        finally:
            self.remove_client(writer)

    # --- REFACTORED COMMAND HANDLERS ---
    async def _process_command(self, msg, writer, username):
        """Dispatch lệnh tới các hàm xử lý tương ứng"""
        parts = msg.split("|")
        cmd = parts[0]

        if cmd == "MSG":
            await self._handle_msg(writer, username, parts)
        elif cmd.startswith("GROUP_"):
            await self._handle_group(writer, username, cmd, parts)
        elif cmd == "CMD_HISTORY":
            await self._handle_history(writer, username, parts)
        elif cmd == "PING":
            # Heartbeat
            print(f" [HEARTBEAT] PING from {username}") 
            writer.write(Protocol.pack("PONG"))
            await writer.drain()
        elif cmd.startswith("CMD_"):
             # User mgmt, typing, etc.
             await self._handle_other_cmds(writer, username, cmd, parts)

        elif cmd == "FILE":
             await self._handle_file(writer, username, parts)
        elif cmd == "REACTION":
             await self._handle_reaction(writer, username, parts)

        elif cmd.startswith("FILE_"):
             await self._handle_file_stream(writer, username, cmd, parts)

        else:
             print(f" [WARN] Unknown command from {username}: {msg}")

    async def _handle_msg(self, writer, username, parts):
        # MSG|receiver|content
        if len(parts) == 2:
            content = parts[1]
            receiver = "General"
        else:
             receiver, content = parts[1], parts[2]

        print(f"💬 [{username} -> {receiver}]: {content}")
        
        message_id = None
        if self.db: 
           loop = asyncio.get_running_loop()
           message_id = await loop.run_in_executor(None, self.db.save_message, username, receiver, content, "text", None)
        
        # Ack to sender (Sent) with message_id
        try:
            ack_msg = f"MSG_SENT|{receiver}|{message_id}" if message_id else f"MSG_SENT|{receiver}"
            writer.write(Protocol.pack(ack_msg))
            await writer.drain()
        except: pass

        if receiver == "General":
            response = f"MSG|{username}|{content}|{message_id}" if message_id else f"MSG|{username}|{content}"
            # Broadcast cho TẤT CẢ kể cả người gửi để họ có message_id
            await self.broadcast(response, exclude_writer=None)
        else:
            # Private
            found = False
            for w, u in self.clients.items():
                if u == receiver:
                    private_msg = f"MSG|{username}|{content}|{message_id}" if message_id else f"MSG|{username}|{content}"
                    w.write(Protocol.pack(private_msg))
                    await w.drain()
                    found = True
                    # Notify sender (Delivered)
                    try:
                        writer.write(Protocol.pack(f"MSG_DELIVERED|{receiver}"))
                        await writer.drain()
                    except: pass
                    break

    async def _handle_group(self, writer, username, cmd, parts):
        if cmd == "GROUP_CREATE":
            g_name = parts[1]
            if self.db:
                loop = asyncio.get_running_loop()
                success, res = await loop.run_in_executor(None, self.db.create_group, g_name, username)
                if success:
                    writer.write(Protocol.pack(f"GROUP_OK|{g_name}"))
                    user_groups = await loop.run_in_executor(None, self.db.get_user_groups, username)
                    writer.write(Protocol.pack(f"GROUPS|{','.join(user_groups)}"))
                else:
                    writer.write(Protocol.pack(f"ERR|{res}"))
                await writer.drain()

        elif cmd == "GROUP_MSG":
            if len(parts) >= 3:
                g_name, content = parts[1], parts[2]
                print(f"🛡️ [{username} -> {g_name}]: {content}")
                message_id = None
                if self.db:
                    loop = asyncio.get_running_loop()
                    message_id = await loop.run_in_executor(None, self.db.save_message, username, g_name, content, "text", None)
                # Broadcast với message_id nếu có
                msg_data = f"GROUP_MSG|{g_name}|{username}|{content}"
                if message_id:
                    msg_data += f"|{message_id}"
                # Gửi cho TẤT CẢ members kể cả người gửi để họ có message_id
                await self.broadcast_group(g_name, msg_data, exclude_writer=None)

        elif cmd == "GROUP_JOIN":
            g_name = parts[1]
            if self.db:
                loop = asyncio.get_running_loop()
                success, res = await loop.run_in_executor(None, self.db.add_group_member, g_name, username)
                if success:
                    writer.write(Protocol.pack(f"GROUP_OK|{g_name}"))
                    await self.broadcast_group(g_name, f"GROUP_NOTIFY|{g_name}|{username} đã tham gia.", exclude_writer=writer)
                    user_groups = await loop.run_in_executor(None, self.db.get_user_groups, username)
                    writer.write(Protocol.pack(f"GROUPS|{','.join(user_groups)}"))
                else:
                    writer.write(Protocol.pack(f"ERR|{res}"))
                await writer.drain()

        elif cmd == "GROUP_LEAVE":
            g_name = parts[1]
            if self.db:
                loop = asyncio.get_running_loop()
                success, res = await loop.run_in_executor(None, self.db.remove_group_member, g_name, username)
                if success:
                    writer.write(Protocol.pack(f"GROUP_LEFT|{g_name}"))
                    await self.broadcast_group(g_name, f"GROUP_NOTIFY|{g_name}|{username} đã rời nhóm.", exclude_writer=writer)
                    user_groups = await loop.run_in_executor(None, self.db.get_user_groups, username)
                    writer.write(Protocol.pack(f"GROUPS|{','.join(user_groups)}"))
                else:
                    writer.write(Protocol.pack(f"ERR|{res}"))
                await writer.drain()
        
        elif cmd == "GROUP_DELETE":
            g_name = parts[1]
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
                                groups = await loop.run_in_executor(None, self.db.get_user_groups, u)
                                w.write(Protocol.pack(f"GROUPS|{','.join(groups)}"))
                                await w.drain()
                            except: pass
                else:
                    writer.write(Protocol.pack(f"ERR|{res}"))
                await writer.drain()

    async def _handle_history(self, writer, username, parts):
        target = parts[1]
        mode = "PRIVATE"
        if len(parts) >= 3:
             mode = parts[2]
        
        loop = asyncio.get_running_loop()
        history = []
        if self.db:
            if mode == "GROUP" or target == "General":
                 history = await loop.run_in_executor(None, self.db.get_group_history, target)
            else:
                 history = await loop.run_in_executor(None, self.db.get_history, username, target)
        
        import json
        hist_data = []
        for row in history:
            # row format: (id, sender, content, timestamp, msg_type, file_path)
            hist_data.append({
                "id": row[0], "sender": row[1], "content": row[2], "timestamp": row[3], "type": row[4], "file": row[5]
            })
        json_str = json.dumps(hist_data)
        writer.write(Protocol.pack(f"HISTORY_DATA|{target}|{json_str}"))
        await writer.drain()

    async def _handle_other_cmds(self, writer, username, cmd, parts):
        loop = asyncio.get_running_loop()
        if cmd == "CMD_PASS_CHANGE" and len(parts) >= 3:
             old_p, new_p = parts[1], parts[2]
             if self.db:
                 res, msg_res = await loop.run_in_executor(None, self.db.update_password, self.client_emails[writer], old_p, new_p)
                 writer.write(Protocol.pack(f"CMD_RES|PASS|{str(res)}|{msg_res}"))
                 await writer.drain()

        elif cmd == "CMD_UPDATE_INFO" and len(parts) >= 3:
             new_name, new_email = parts[1], parts[2]
             if self.db:
                 res, msg_res = await loop.run_in_executor(None, self.db.update_info, self.client_emails[writer], new_name, new_email)
                 if res:
                     self.client_emails[writer] = new_email
                     self.clients[writer] = new_name
                 writer.write(Protocol.pack(f"CMD_RES|INFO|{str(res)}|{msg_res}"))
                 await writer.drain()

        elif cmd == "CMD_UPDATE_AVATAR" and len(parts) >= 3:
             filename, b64_data = parts[1], parts[2]
             if self.db:
                 if not os.path.exists("uploads/avatars"): os.makedirs("uploads/avatars")
                 fname_secure = f"{self.client_emails[writer]}_{datetime.datetime.now().strftime('%M%S')}_{filename}"
                 file_path = f"uploads/avatars/{fname_secure}"
                 try:
                     with open(file_path, "wb") as f: f.write(base64.b64decode(b64_data))
                     res, msg_res = await loop.run_in_executor(None, self.db.update_avatar, self.client_emails[writer], file_path)
                     writer.write(Protocol.pack(f"CMD_RES|AVATAR|{str(res)}|{file_path}"))
                 except Exception as e:
                     writer.write(Protocol.pack(f"CMD_RES|AVATAR|False|{str(e)}"))
                 await writer.drain()

        elif cmd == "CMD_TYPING" and len(parts) >= 3:
             target, sender = parts[1], parts[2]
             if target == "General":
                  await self.broadcast(f"TYPING|{target}|{sender}", exclude_writer=writer)
             else:
                  # Private Typing
                  found_user = False
                  for w, u in self.clients.items():
                      if u == target:
                          try:
                              w.write(Protocol.pack(f"TYPING|{sender}|{sender}"))
                              await w.drain()
                              found_user = True
                          except: pass
                          break
                  if not found_user:
                      await self.broadcast_group(target, f"TYPING|{target}|{sender}", exclude_writer=writer)
        
        elif cmd == "CMD_GET_INFO":
            if self.db and writer in self.client_emails:
                loop = asyncio.get_running_loop()
                info = await loop.run_in_executor(None, self.db.get_user_info, self.client_emails[writer])
                if info:
                    avt = info['avatar'] if info['avatar'] else ""
                    writer.write(Protocol.pack(f"CMD_RES|GET_INFO|{info['username']}|{info['email']}|{avt}"))
                else:
                    writer.write(Protocol.pack("CMD_RES|GET_INFO|Error|Error|"))
                await writer.drain()

    async def _handle_file_stream(self, writer, username, cmd, parts):
        """
        Xử lý truyền file theo luồng (Chunked Transfer)
        Format:
          FILE_START | target | filename | file_size | total_chunks
          FILE_CHUNK | target | filename | chunk_index | data_b64
          FILE_END   | target | filename
        """
        target = parts[1]
        
        # Chỉ lưu log/DB khi bắt đầu file
        if cmd == "FILE_START":
            filename = parts[2]
            print(f"📁 [{username} -> {target}] Start sending file: {filename}")
            if self.db:
                 loop = asyncio.get_running_loop()
                 # Lưu lịch sử là "Sent a file" thay vì lưu cả file (để tránh nặng DB)
                 await loop.run_in_executor(None, self.db.save_message, username, target, f"[FILE] {filename}", "file_start", None)
        
        # Forward tin nhắn tới người nhận
        encoded_msg = Protocol.pack(f"{cmd}|{username}|{'|'.join(parts[1:])}")
        
        if target == "General":
            await self.broadcast(f"{cmd}|{username}|{'|'.join(parts[1:])}", exclude_writer=writer)
        else:
             # Private or Group
             # Logic tìm user để forward (giống _handle_msg) nhưng tối ưu hơn
             if target in self.client_emails.values(): # Check if target is a user (simplistic check)
                 pass 
             
             # Broadcast Group (nếu target là group) hoặc Send Private
             # Để đơn giản, ta dùng logic broadcast của Group nếu target không phải user private
             
             # Case 1: Private
             sent = False
             for w, u in self.clients.items():
                 if u == target:
                     w.write(encoded_msg)
                     await w.drain()
                     sent = True
                     break
            
             # Case 2: Group (Nếu không phải private user)
             if not sent:
                await self.broadcast_group(target, f"{cmd}|{username}|{'|'.join(parts[1:])}", exclude_writer=writer)

    async def _handle_reaction(self, writer, username, parts):
        """Xử lý REACTION|ADD|message_id|emoji hoặc REACTION|REMOVE|message_id|emoji"""
        if len(parts) < 4:
            return
        
        action, message_id, emoji = parts[1], int(parts[2]), parts[3]
        
        if not self.db:
            return
        
        loop = asyncio.get_running_loop()
        
        if action == "ADD":
            # add_reaction tự động toggle (thêm hoặc xóa)
            result = await loop.run_in_executor(None, self.db.add_reaction, message_id, username, emoji)
            print(f"👍 [{username}] {result} reaction {emoji} on message {message_id}")
        
        # Lấy tất cả reactions của tin nhắn
        reactions_dict = await loop.run_in_executor(None, self.db.get_message_reactions, message_id)
        
        # Serialize reactions: {"❤️": ["Alice", "Bob"]} -> "❤️:Alice,Bob;👍:Charlie"
        reactions_str = ";".join([f"{emoji}:{','.join(users)}" for emoji, users in reactions_dict.items()])
        
        # Broadcast update cho tất cả clients
        response = f"REACTION|UPDATE|{message_id}|{reactions_str}"
        await self.broadcast(response)

    async def start(self):
        # SSL Context
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(certfile=os.path.join(current_dir, "server.crt"), 
                                keyfile=os.path.join(current_dir, "server.key"))

        server = await asyncio.start_server(self.handle_client, HOST, PORT, ssl=ssl_ctx)
        
        addr = server.sockets[0].getsockname()
        print(f" [SERVER] Đang chạy Secure SSL tại {addr}")
        print(" [INFO] Sẵn sàng chấp nhận kết nối an toàn...")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    try:
        # Check certs
        if not os.path.exists(os.path.join(current_dir, "server.crt")) or not os.path.exists(os.path.join(current_dir, "server.key")):
             print(" [ERROR] Không tìm thấy chứng chỉ SSL (server.crt, server.key). Vui lòng chạy generate_cert_v2.py trước.")
             sys.exit(1)

        server = AsyncChatServer()
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print(" [STOP] Server đã dừng.")