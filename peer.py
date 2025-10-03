import threading
import socket
import time


class Server:
    BROADCAST_INTERVAL = 10

    def __init__(self, name: str):
        self.name = name

        self.tcp_socket: socket.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        self.udp_socket: socket.socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        )
        self.clients: dict[int, socket.socket] = {}
        self.client_count: int = 0
        self.lock = threading.Lock()

        self.running = True

    def _add_client(self, s: socket.socket, address: tuple[str, int]):
        with self.lock:
            self.clients[hash(address)] = s
            self.client_count += 1

    def _remove_client(self, address: tuple[str, int]):
        with self.lock:
            del self.clients[hash(address)]

    def _get_client(self, address: tuple[str, int]):
        with self.lock:
            return self.clients[hash(address)]

    def listen_client(self, s: socket.socket, address: tuple[str, int]):
        try:
            data = s.recv(1024)
            if not data:
                return
            name = data.decode(errors="ignore")
            if name.startswith("_NAME="):
                name = name[6:].strip()
            else:
                name = f"Anonymous #{self.client_count}"

            while True:
                data = s.recv(1024)
                if not data:
                    break

                str_data = data.decode()
                print(f"[{name}] - {str_data}")
                with self.lock:
                    for sock in self.clients.values():
                        if sock is not s:
                            sock.send(f"[{name}] - {str_data}".encode())
        finally:
            with self.lock:
                self._remove_client(address)
            s.close()

    def start_broadcast(self):
        threading.Thread(target=self.broadcast_loop, daemon=True).start()

    def broadcast_loop(self):
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        msg = f"ROOM_HOST:{self.udp_socket.getsockname()}"

        while self.running:
            self.udp_socket.sendto(msg.encode(), ("<broadcast>", 0))
            time.sleep(Server.BROADCAST_INTERVAL)

    def on_client_join(self, s: socket.socket, address: tuple[str, int]):
        print(f"New connection from address {address}")
        self._add_client(s, address)
        self.listen_client(s, address)

    def client_join(self):
        client_socket, address = self.tcp_socket.accept()
        new_client_thread = threading.Thread(
            target=self.on_client_join, args=(client_socket, address), daemon=True
        )
        new_client_thread.start()

    def start(self):
        self.tcp_socket.bind(("", 0))
        address = self.tcp_socket.getsockname()
        self.tcp_socket.listen()
        print(f"Listening on {address}")

        self.start_broadcast()

        # Continuously accept clients
        try:
            while self.running:
                self.client_join()
        except OSError as e:
            print(f"Error: {e}")

    def stop(self):
        self.running = False
        print("Disconnecting all clients...")
        with self.lock:
            for sock in self.clients.values():
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()
        self.tcp_socket.close()
        self.udp_socket.close()
        print("Room closed.")
