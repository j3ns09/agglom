import socket
import threading
import time


class Server:
    PORT = 5000

    def __init__(self):
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: dict[str, socket.socket] = {}

    def on_client_join(self, s, address):
        print(f"New connection from address {address}")
        client_hash = hash(address)

    def run(self):
        self.socket.bind(("", Server.PORT))
        self.socket.listen()
        print(f"Listening on port {Server.PORT}")

    def client_join(self):
        client_socket, address = self.socket.accept()
        pass


def listening():
    while True:
        client_socket, address = server_socket.accept()
        client_thread = threading.Thread(target=on_join, args=(client_socket, address))
        client_thread.start()


def on_join(s, address):
    print(f"New connection from address {address}")
    client_hash = hash(address)
    clients[client_hash] = s

    l = len(clients)

    try:
        data = s.recv(1024)
        if not data:
            return
        name = data.decode(errors="ignore")
        if name.startswith("_NAME="):
            name = name[6:].strip()
        else:
            name = "Unknown " + str(l)

        while True:
            data = s.recv(1024)
            if not data:
                break

            str_data = data.decode()
            print(f"[{name}] - {str_data}")
            for c in clients:
                if c != client_hash:
                    clients[c].send(f"[{name}] - {str_data}".encode())
    except Exception as e:
        print(f"Error with {address}: {e}")
    finally:
        s.close()
        print(f"Connection with {address} terminated")


def main():
    init()

    listening()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down server...")
        server_socket.close()
