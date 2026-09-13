# picoware/apps/ftp-server.py

_ftp = None
_ui_drawn = False

class NonBlockingFTP:
    def __init__(self, ip, board_name, port=2121, data_port=2122):
        import socket
        import select
        
        self.socket = socket
        self.select = select
        self.ip = ip
        self.port = port
        self.data_port = data_port
        self.cwd = "/"
        
        # Hardware Detection & Memory Strategy using Picoware's board_name
        machine = board_name.lower()
        if "rp2350" in machine or "pico 2" in machine:
            # Pico 2 / RP2350
            self.max_buffer_size = 65536  
            self.loops_per_frame = 8      
        else:
            # Pico 1 / RP2040
            self.max_buffer_size = 4096   
            self.loops_per_frame = 4      
        
        # Sockets
        self.srv_sock = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_STREAM)
        self.srv_sock.setsockopt(self.socket.SOL_SOCKET, self.socket.SO_REUSEADDR, 1)
        self.srv_sock.bind((self.ip, self.port))
        self.srv_sock.listen(1)
        
        self.poller = self.select.poll()
        self.poller.register(self.srv_sock, self.select.POLLIN)
        
        self.client_sock = None
        self.pasv_sock = None
        self.data_sock = None
        
        # State machine for transfers
        self.transfer_file = None
        self.transfer_mode = None 
        self.chunk_buffer = b""
        self.chunk_offset = 0     # Tracks our place without copying memory
        self.write_buffer = bytearray()

    def _send(self, msg):
        if self.client_sock:
            try:
                self.client_sock.sendall((msg + "\r\n").encode())
            except OSError:
                self._disconnect()

    def _disconnect(self):
        if self.client_sock:
            self.poller.unregister(self.client_sock)
            self.client_sock.close()
            self.client_sock = None
        if self.pasv_sock:
            self.pasv_sock.close()
            self.pasv_sock = None
        if self.data_sock:
            self.data_sock.close()
            self.data_sock = None
        if self.transfer_file:
            self.transfer_file.close()
            self.transfer_file = None
            self.transfer_mode = None
        
        # Free memory immediately
        self.chunk_buffer = b""
        self.chunk_offset = 0
        self.write_buffer = bytearray()
        import gc
        gc.collect()

    def _resolve_path(self, path):
        if not path.startswith("/"):
            path = self.cwd + "/" + path
        parts = [p for p in path.split("/") if p and p != "."]
        final = []
        for p in parts:
            if p == "..":
                if final: final.pop()
            else:
                final.append(p)
        return "/" + "/".join(final)

    def tick(self):
        import os
        import gc
        
        # 1. Handle active file transfers smoothly
        if self.transfer_mode and self.data_sock and self.transfer_file:
            
            for _ in range(self.loops_per_frame):
                if self.transfer_mode == 'RETR': # Download to PC
                    r, w, e = self.select.select([], [self.data_sock], [], 0)
                    if w:
                        try:
                            # Read massive chunk from SD card at once
                            if not self.chunk_buffer:
                                try:
                                    b = self.transfer_file.read(self.max_buffer_size)
                                except MemoryError:
                                    # Fallback if heap is fragmented
                                    gc.collect()
                                    self.max_buffer_size = 4096 
                                    b = self.transfer_file.read(self.max_buffer_size)

                                if not b:
                                    self.transfer_file.close()
                                    self.transfer_file = None
                                    self.transfer_mode = None
                                    self.data_sock.close()
                                    self.data_sock = None
                                    self._send("226 Transfer complete.")
                                    return
                                self.chunk_buffer = b
                                self.chunk_offset = 0
                            
                            # Bleed buffer to Wi-Fi using memoryview (zero-copy)
                            if self.chunk_buffer:
                                view = memoryview(self.chunk_buffer)[self.chunk_offset:]
                                sent = self.data_sock.send(view)
                                self.chunk_offset += sent
                                
                                # Clear the buffer only when fully sent
                                if self.chunk_offset >= len(self.chunk_buffer):
                                    self.chunk_buffer = b""
                                    self.chunk_offset = 0
                                    
                        except OSError as err:
                            if err.args[0] == 11: # EAGAIN
                                break 
                            else:
                                self._disconnect()
                                return
                    else:
                        break 

                elif self.transfer_mode == 'STOR': # Upload to Pico
                    r, w, e = self.select.select([self.data_sock], [], [], 0)
                    if r:
                        try:
                            # Read from Wi-Fi socket
                            chunk = self.data_sock.recv(4096)
                            if chunk:
                                self.write_buffer.extend(chunk)
                                # Dump to SD card only when buffer is full
                                if len(self.write_buffer) >= self.max_buffer_size:
                                    self.transfer_file.write(self.write_buffer)
                                    self.write_buffer = bytearray()
                                    gc.collect() # Help prevent upload fragmentation
                            else:
                                # End of stream, flush remaining data
                                if self.write_buffer:
                                    self.transfer_file.write(self.write_buffer)
                                    self.write_buffer = bytearray()
                                self.transfer_file.close()
                                self.transfer_file = None
                                self.transfer_mode = None
                                self.data_sock.close()
                                self.data_sock = None
                                self._send("226 Transfer complete.")
                                return
                        except OSError as err:
                            if err.args[0] == 11: 
                                break 
                            else:
                                self._disconnect()
                                return
                        except MemoryError:
                            # Force a flush if RAM chokes mid-upload
                            if self.write_buffer:
                                self.transfer_file.write(self.write_buffer)
                                self.write_buffer = bytearray()
                                gc.collect()
                    else:
                        break 
            return 

        # 2. Check for incoming connections or commands
        events = self.poller.poll(0)
        for sock, ev in events:
            if sock == self.srv_sock:
                self._disconnect()
                self.client_sock, addr = self.srv_sock.accept()
                self.client_sock.setblocking(False)
                self.poller.register(self.client_sock, self.select.POLLIN)
                self._send("220 Picoware Dynamic FTP Server Ready.")
                
            elif sock == self.client_sock:
                try:
                    data = self.client_sock.recv(512)
                    if not data:
                        self._disconnect()
                        continue
                    
                    cmd_line = data.decode().strip()
                    parts = cmd_line.split(" ", 1)
                    cmd = parts[0].upper()
                    arg = parts[1] if len(parts) > 1 else ""
                    
                    self._process_command(cmd, arg, os)
                except OSError:
                    self._disconnect()

    def _process_command(self, cmd, arg, os):
        if cmd == "USER":
            self._send("331 User okay, need password.")
        elif cmd == "PASS":
            self._send("230 Logged in.")
        elif cmd == "SYST":
            self._send("215 UNIX Type: L8")
        elif cmd == "PWD":
            self._send(f'257 "{self.cwd}" is current directory.')
        elif cmd == "TYPE":
            self._send("200 Type set to I.") 
        elif cmd == "SIZE": 
            try:
                stat = os.stat(self._resolve_path(arg))
                self._send(f"213 {stat[6]}")
            except OSError:
                self._send("550 File not found.")
        elif cmd == "CWD":
            new_path = self._resolve_path(arg)
            try:
                os.stat(new_path)
                self.cwd = new_path
                self._send("250 Directory successfully changed.")
            except OSError:
                self._send("550 Failed to change directory.")
        elif cmd == "CDUP":
            self.cwd = self._resolve_path(self.cwd + "/..")
            self._send("250 Directory successfully changed.")
        elif cmd == "PASV":
            if self.pasv_sock:
                self.pasv_sock.close()
            self.pasv_sock = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_STREAM)
            self.pasv_sock.setsockopt(self.socket.SOL_SOCKET, self.socket.SO_REUSEADDR, 1)
            self.pasv_sock.bind((self.ip, self.data_port))
            self.pasv_sock.listen(1)
            
            ip_parts = self.ip.split('.')
            p1 = self.data_port >> 8
            p2 = self.data_port & 0xFF
            self._send(f"227 Entering Passive Mode ({ip_parts[0]},{ip_parts[1]},{ip_parts[2]},{ip_parts[3]},{p1},{p2}).")
        elif cmd == "LIST":
            try:
                self.data_sock, _ = self.pasv_sock.accept()
                self._send("150 Here comes the directory listing.")
                
                for f in os.ilistdir(self.cwd):
                    name = f[0]
                    type_num = f[1]
                    size = f[3] if len(f) > 3 else 0
                    if type_num == 0x4000:
                        self.data_sock.sendall(f"drwxr-xr-x 1 owner group 0 Jan 1 2026 {name}\r\n".encode())
                    else:
                        self.data_sock.sendall(f"-rw-r--r-- 1 owner group {size} Jan 1 2026 {name}\r\n".encode())
                
                self.data_sock.close()
                self.data_sock = None
                self._send("226 Directory send OK.")
            except OSError:
                self._send("425 Can't open data connection.")
        elif cmd == "RETR":
            try:
                path = self._resolve_path(arg)
                self.transfer_file = open(path, 'rb')
                self.data_sock, _ = self.pasv_sock.accept()
                self.data_sock.setblocking(False)
                self.chunk_buffer = b""
                self.chunk_offset = 0
                self.transfer_mode = 'RETR'
                self._send("150 Opening binary mode data connection.")
            except OSError:
                self._send("550 Failed to open file.")
        elif cmd == "STOR":
            try:
                path = self._resolve_path(arg)
                self.transfer_file = open(path, 'wb')
                self.data_sock, _ = self.pasv_sock.accept()
                self.data_sock.setblocking(False)
                self.write_buffer = bytearray()
                self.transfer_mode = 'STOR'
                self._send("150 Ok to send data.")
            except OSError:
                self._send("550 Failed to open file.")
        elif cmd == "DELE":
            try:
                os.remove(self._resolve_path(arg))
                self._send("250 File deleted.")
            except OSError:
                self._send("550 Delete failed.")
        elif cmd == "MKD":
            try:
                os.mkdir(self._resolve_path(arg))
                self._send("257 Directory created.")
            except OSError:
                self._send("550 Create directory failed.")
        elif cmd == "RMD":
            try:
                os.rmdir(self._resolve_path(arg))
                self._send("250 Directory removed.")
            except OSError:
                self._send("550 Remove directory failed.")
        elif cmd == "QUIT":
            self._send("221 Goodbye.")
            self._disconnect()
        else:
            self._send("500 Unknown command.")

    def close(self):
        self._disconnect()
        if self.srv_sock:
            self.poller.unregister(self.srv_sock)
            self.srv_sock.close()


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.vector import Vector
    
    global _ftp, _ui_drawn

    wifi = view_manager.wifi

    if not wifi or not wifi.is_connected():
        view_manager.alert("WiFi not connected...", False)
        return False
    
    # 1. Safely handle the IP address (checks if it needs parentheses)
    try:
        ip = wifi.ip_address() if callable(wifi.ip_address) else wifi.ip_address
    except AttributeError:
        # Fallback if the property doesn't exist on this Picoware version
        import network
        ip = network.WLAN(network.STA_IF).ifconfig()[0]

    # 2. Safely handle the board name
    try:
        b_name = view_manager.board_name
        b_name = b_name() if callable(b_name) else b_name
        b_name = str(b_name) if b_name else "Unknown"
    except AttributeError:
        b_name = "Unknown"
    
    try:
        _ftp = NonBlockingFTP(
            ip=ip, 
            board_name=b_name
        )
    except Exception as e:
        # This will now display the ACTUAL Python error on your screen
        error_msg = str(e)[:25] # Limit length so it fits on screen
        view_manager.alert(f"Err: {error_msg}", False)
        print("FTP Crash:", e) # Prints to your Thonny/serial console if connected
        return False

    _ui_drawn = False
    return True

def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK
    from picoware.system.vector import Vector
    
    global _ftp, _ui_drawn

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    if _ftp:
        _ftp.tick()

    if not _ui_drawn:
        draw = view_manager.draw
        fg = view_manager.foreground_color
        
        draw.text(Vector(0, 0), "FTP SERVER", fg)
        draw.text(Vector(0, 20), f"IP: {_ftp.ip}", fg)
        draw.text(Vector(0, 40), f"PORT: {_ftp.port}", fg)
        draw.text(Vector(0, 70), f"HW: {view_manager.board_name}", fg)
        draw.text(Vector(0, 100), "BACK = STOP", fg)
        draw.swap()
        _ui_drawn = True


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect
    global _ftp, _ui_drawn

    if _ftp:
        _ftp.close()
        del _ftp
        _ftp = None

    _ui_drawn = False
    collect()