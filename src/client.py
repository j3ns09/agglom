import threading
import socket
import time

from prompt_toolkit import PromptSession, prompt, print_formatted_text
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from .server import Server, DEFAULT_UDP_PORT


class Client:
    PROMPT_STYLE = Style.from_dict(
        {
            "prompt-name": "#808080 bold",
            "good": "#00ff00 bold",
            "new": "#0000ff bold",
            "bad": "#ff0000",
            "others": "#ff0000 bold",
        }
    )

    DISCOVERY_INTERVAL = 8

    def __init__(self, name: str):
        self.name: str = name
        self.prompt_session: PromptSession = PromptSession()
        self.socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running: bool = True

    def discover_rooms(self, timeout=DISCOVERY_INTERVAL):
        """Listen for UDP broadcasts for `timeout` seconds, return list of (ip, port)"""
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind(("", DEFAULT_UDP_PORT))
        udp.settimeout(timeout)
        rooms = {}
        start = time.time()
        while time.time() - start < timeout:
            try:
                data, addr = udp.recvfrom(1024)
                msg = data.decode()
                if msg.startswith("ROOM_HOST:"):
                    _, ip, port_str, name = msg.split(":")
                    port = int(port_str)
                    rooms[name] = (ip, port)
            except socket.timeout:
                break
            except Exception:
                continue
        return rooms

    def join_room(self, ip: str, port: int):
        self.socket.connect((ip, port))
        with patch_stdout():
            print_formatted_text(
                HTML(f"<good>Connected to room at {(ip, port)}</good>"),
                style=Client.PROMPT_STYLE,
            )
        self.socket.send(f"_NAME={self.name}".encode())

        threading.Thread(target=self.receive_loop, daemon=True).start()

    def send_loop(self):
        with patch_stdout():
            while self.running:
                try:
                    message: str = self.prompt_session.prompt(
                        HTML(f"[<prompt-name>Vous ({self.name})</prompt-name>] >>> "),
                        style=Client.PROMPT_STYLE,
                    )
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
                sender, message = data.decode(errors="ignore").split(":")
                print_formatted_text(
                    HTML(f"[<others>{sender}</others> - {message}"),
                    style=Client.PROMPT_STYLE,
                )
            except Exception as e:
                print(f"\nErreur: {e}")
                break

    def run(self):
        result: str = choice(
            message="Voulez-vous créer ou rejoindre une salle ? :",
            options=[("host", "Créer une salle"), ("client", "Rejoindre une salle")],
            default="host",
        )

        if result == "host":
            name = prompt("Quel nom donner à la salle ? : ")
            host = Server(name)
            threading.Thread(target=host.start, daemon=True).start()

            time.sleep(0.5)
            with host.lock:
                self.join_room("127.0.0.1", host.tcp_address[1])

        else:
            rooms: dict = self.discover_rooms()
            if not rooms:
                print("No rooms found.")
                return
            print("Rooms discovered:")

            result: tuple[str, int] = choice(
                message="Veuillez choisir la salle :",
                options=[(addr, name) for name, addr in rooms.items()],
            )

            self.join_room(*result)

        self.send_loop()

    def disconnect(self):
        self.socket.close()
