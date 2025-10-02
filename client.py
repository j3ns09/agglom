import socket
import threading
import time

# Constants
PORT = 5000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("127.0.0.1", PORT))

try:
    name = input("Quel est ton nom ? : ")

    client_socket.send(f"_NAME={name}".encode())

    while True:
        message = input("[Vous] >>> ")
        client_socket.send(message.encode())
except KeyboardInterrupt:
    client_socket.close()
