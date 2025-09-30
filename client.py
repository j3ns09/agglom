import socket
import threading
import time

# Constants
PORT = 5000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("127.0.0.1", PORT))

try:
    while True:
        message = input(">>")
        client_socket.send(message.encode())
except KeyboardInterrupt:
    client_socket.close()
