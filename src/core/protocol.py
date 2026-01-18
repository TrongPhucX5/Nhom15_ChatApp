import struct

class Protocol:
    """
    Giao thức gửi/nhận tin nhắn (Framing Protocol).
    Cấu trúc gói tin: [HEADER (4 bytes)][PAYLOAD (N bytes)]
    - HEADER: Số nguyên 4 byte (big-endian) biểu diễn độ dài của PAYLOAD.
    - PAYLOAD: Dữ liệu (UTF-8 string hoặc bytes).
    """

    HEADER_SIZE = 4

    @staticmethod
    def pack(content: str) -> bytes:
        """Đóng gói tin nhắn thành bytes để gửi đi."""
        if isinstance(content, str):
            payload = content.encode('utf-8')
        else:
            payload = content
        
        length = len(payload)
        # Pack length thành 4 bytes, big-endian
        header = struct.pack('!I', length) 
        return header + payload

    @staticmethod
    async def recv_msg(reader):
        """
        Nhận tin nhắn đầy đủ từ asyncio StreamReader.
        Trả về chuỗi String decoded hoặc None nếu mất kết nối.
        """
        try:
            # 1. Đọc Header (4 bytes)
            header = await reader.read(Protocol.HEADER_SIZE)
            if not header or len(header) < Protocol.HEADER_SIZE:
                return None # Mất kết nối hoặc dữ liệu lỗi
            
            # 2. Giải mã độ dài
            (length,) = struct.unpack('!I', header)
            
            # 3. Đọc dữ liệu (Payload) theo độ dài chính xác
            payload = await reader.readexactly(length)
            return payload.decode('utf-8')
        
        except Exception:
            return None

    @staticmethod
    def recv_msg_sync(sock):
        """
        Nhận tin nhắn (Synchronous) dành cho Client dùng Thread/Blocking Socket.
        """
        try:
            # 1. Đọc Header
            header = b''
            while len(header) < Protocol.HEADER_SIZE:
                chunk = sock.recv(Protocol.HEADER_SIZE - len(header))
                if not chunk: return None
                header += chunk
            
            # 2. Giải mã độ dài
            (length,) = struct.unpack('!I', header)
            
            # 3. Đọc Payload
            payload = b''
            while len(payload) < length:
                chunk = sock.recv(length - len(payload))
                if not chunk: return None
                payload += chunk
                
            return payload.decode('utf-8')
        except Exception:
            return None
