from src.client import Client


def main():
    name = input("Enter your name: ")
    client = Client(name)
    client.run()


if __name__ == "__main__":
    main()
