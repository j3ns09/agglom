import socket
import threading
import time


class Server:
    PORT = 5000

    def __init__(self):
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: dict[int, socket.socket] = {}
        self.client_count: int = 0
        self.lock = threading.Lock()

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

    def on_client_join(self, s: socket.socket, address: tuple[str, int]):
        print(f"New connection from address {address}")
        self._add_client(s, address)
        self.listen_client(s, address)

    def client_join(self):
        client_socket, address = self.socket.accept()
        new_client_thread = threading.Thread(
            target=self.on_client_join, args=(client_socket, address), daemon=True
        )
        new_client_thread.start()

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
        except Exception as e:
            print(f"Error with {address}: {e}")
        finally:
            s.close()
            self._remove_client(address)
            print(f"Connection with {address} terminated")

    def run(self):
        self.socket.bind(("", Server.PORT))
        self.socket.listen()
        print(f"Listening on port {Server.PORT}")

        # Continuously accept clients
        try:
            while True:
                self.client_join()
        except OSError as e:
            print(f"Error: {e}")

    def disconnect(self):
        print("Disconnecting all clients...")
        with self.lock:
            for sock in self.clients.values():
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                except Exception as e:
                    print(f"Error closing client socket: {e}")
            self.clients.clear()
        self.socket.close()
        print("Server socket closed.")


def main():
    server = Server()

    try:
        server.run()
    except KeyboardInterrupt:
        server.disconnect()
        print("Shutting down server...")


if __name__ == "__main__":
    main()
