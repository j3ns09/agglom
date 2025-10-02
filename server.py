import socket
import threading
import time

# Constants
PORT = 5000


server_socket: socket.socket | None = None

clients = []


def init():
    global server_socket

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("", PORT))
    server_socket.listen()
    print(f"Listening on port {PORT}")


def listening():
    while True:
        client_socket, address = server_socket.accept()
        client_thread = threading.Thread(target=on_join, args=(client_socket, address))
        client_thread.start()


def on_join(s, address):
    print(f"New connection from address {address}")
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
            print(f"Received from {name}: {data.decode(errors='ignore')}")
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
