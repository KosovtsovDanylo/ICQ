import socket
import threading
import json
import os
from datetime import datetime

def start_server(host='192.168.162.152', port=12345):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print("Server started and waiting for connections...")

    clients = {}
    messages = {}
    all_users = set()  # Set to store all users

    def load_history():
        if os.path.exists('chat_history.json'):
            try:
                with open('chat_history.json', 'r') as file:
                    data = json.load(file)
                    return {tuple(key.split(',')): value for key, value in data.items()}
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error loading chat history: {e}")
                return {}
        return {}

    def save_history():
        with open('chat_history.json', 'w') as file:
            json.dump({','.join(key): value for key, value in messages.items()}, file)

    def load_users():
        if os.path.exists('users.json'):
            try:
                with open('users.json', 'r') as file:
                    return set(json.load(file))
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error loading user list: {e}")
                return set()
        return set()

    def save_users():
        with open('users.json', 'w') as file:
            json.dump(list(all_users), file)

    def update_clients_users():
        online_users = list(clients.keys())
        offline_users = list(all_users - set(online_users))
        users_dict = {"online": online_users, "offline": offline_users}
        users_list = json.dumps(users_dict).encode('utf-8')
        print("Sending user list:", users_list)
        for conn in clients.values():
            conn.send(users_list)

    def client_thread(conn, addr):
        name = conn.recv(1024).decode('utf-8')
        clients[name] = conn
        all_users.add(name)
        save_users()  # Save all users
        update_clients_users()

        try:
            while True:
                data = conn.recv(1024).decode('utf-8')
                if not data:
                    break

                if data.startswith('history_request'):
                    _, requester, partner = data.split(':')
                    chat_key = tuple(sorted([requester, partner]))
                    history = messages.get(chat_key, [])
                    history_json = json.dumps([{'sender': sender, 'text': msg, 'timestamp': timestamp} for sender, msg, timestamp in history])
                    conn.send(f"history:{history_json}".encode('utf-8'))
                else:
                    if ':' in data:
                        recipient, message = data.split(':', 1)
                        chat_key = tuple(sorted([name, recipient]))
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if chat_key not in messages:
                            messages[chat_key] = []
                        messages[chat_key].append((name, message, timestamp))
                        save_history()  # Save history with each new message

                        if recipient in clients:
                            clients[recipient].send(f"{name}: {message}".encode('utf-8'))
        except ConnectionResetError:
            print(f"Client {name} disconnected.")
        finally:
            if name in clients:
                del clients[name]
                update_clients_users()
            conn.close()

    all_users.update(load_users())
    messages.update(load_history())

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=client_thread, args=(client_socket, addr)).start()

if __name__ == "__main__":
    start_server()
