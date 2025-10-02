import socket
import threading

from prompt_toolkit import PromptSession

# Constants
PORT = 5000


class Client:
    def __init__(self, name: str, server_address: tuple[str, int]):
        self.name: str = name
        self.server_address: tuple[str, int] = server_address
        self.prompt_session: PromptSession = PromptSession()
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running: bool = True

    def connect(self):
        self.socket.connect(self.server_address)
        self.socket.send(f"_NAME={self.name}".encode())

    def send_loop(self):
        while self.running:
            try:
                message = self.prompt_session.prompt("[Vous] >>> ")
                if message.lower() in ("exit", "quit"):
                    self.running = False
                    break
                self.socket.send(message.encode())
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break

    def receive_loop(self):
        while self.running:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                print("\n" + data.decode())
            except Exception as e:
                print(f"\n Erreur: {e}")
                break

    def run(self):
        try:
            self.connect()
            recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
            recv_thread.start()
            self.send_loop()
        finally:
            self.disconnect()
            print("Disconnected.")

    def disconnect(self):
        self.socket.close()


def init_client() -> Client:
    SERVER_ADDRESS = ("127.0.0.1", PORT)

    name = input("Quel est ton nom ?: ")
    client = Client(name, SERVER_ADDRESS)

    return client


# Main thread handling input messages
# # Second thread handling other clients and server messages
def main():
    client = init_client()

    try:
        client.run()
    except KeyboardInterrupt:
        client.disconnect()
        print("\nFermeture du client")


if __name__ == "__main__":
    main()
