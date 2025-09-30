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
    try:
        while True:
            data = s.recv(1024)
            if not data:
                break
            print(f"Received from {address}: {data.decode(errors='ignore')}")
    except Exception as e:
        print(f"Error with {address}: {e}")
    finally:
        s.close()
        print(f"Connection with {address} terminated")


def client_join():
    time.sleep(5)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("127.0.0.1", PORT))

    time.sleep(5)

    client_socket.close()


def main():
    init()

    listening_thread = threading.Thread(target=listening, daemon=True)
    listening_thread.start()

    client_thread = threading.Thread(target=client_join, args=())
    client_thread.start()

    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Shutting down server...")
        server_socket.close()


if __name__ == "__main__":
    main()
