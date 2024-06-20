import tkinter as tk
import socket
import threading
import json
from datetime import datetime

class LoginWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title('Messenger Login')
        self.geometry('300x250')
        tk.Label(self, text="Name:").pack(pady=(10, 0))
        self.name_entry = tk.Entry(self)
        self.name_entry.pack(pady=5)
        tk.Label(self, text="Server IP:").pack(pady=(10, 0))
        self.ip_entry = tk.Entry(self)
        self.ip_entry.pack(pady=5)
        self.ip_entry.insert(0, "192.168.162.152")
        enter_button = tk.Button(self, text="Enter", command=self.enter)
        enter_button.pack(pady=20)

    def enter(self):
        name = self.name_entry.get()
        server_ip = self.ip_entry.get()
        self.master.init_messenger(name, server_ip)
        self.destroy()

class MessengerClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.login_window = LoginWindow(self)
        self.socket = None
        self.name = None
        self.current_chat_user = None

    def init_messenger(self, name, server_ip):
        self.name = name
        self.deiconify()
        self.title('Messenger')
        self.geometry('800x500')

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((server_ip, 12345))
            self.socket.send(name.encode('utf-8'))
        except ConnectionRefusedError:
            print("Unable to connect to server.")
            self.destroy()
            return

        self.user_label = tk.Label(self, text=f"User: {self.name}", font=('Arial', 12, 'bold'))
        self.user_label.pack(side='top', pady=5)

        self.user_frame = tk.Frame(self, bg='lightgray', width=200)
        self.user_frame.pack(side='right', fill='y')

        self.online_label = tk.Label(self.user_frame, text="Online", bg='lightgray', font=('Arial', 10, 'bold'))
        self.online_label.pack(side='top', pady=(5, 0))

        self.online_list = tk.Listbox(self.user_frame, bg='lightgray')
        self.online_list.pack(side='top', fill='y', expand=True)
        self.online_list.bind('<<ListboxSelect>>', self.on_user_select)

        self.offline_label = tk.Label(self.user_frame, text="Offline", bg='lightgray', font=('Arial', 10, 'bold'))
        self.offline_label.pack(side='top', pady=(5, 0))

        self.offline_list = tk.Listbox(self.user_frame, bg='lightgray')
        self.offline_list.pack(side='top', fill='y', expand=True)
        self.offline_list.bind('<<ListboxSelect>>', self.on_user_select)

        self.exit_chat_button = tk.Button(self.user_frame, text="Exit Chat", command=self.exit_chat, width=20)
        self.exit_chat_button.pack(side='bottom', fill='x')

        self.chat_frame = tk.Frame(self, bg='white')
        self.chat_frame.pack(side='left', expand=True, fill='both')

        self.chat_text = tk.Text(self.chat_frame, state='disabled', bg='white')
        self.chat_text.pack(side='top', expand=True, fill='both')

        self.input_frame = tk.Frame(self.chat_frame)
        self.input_frame.pack(side='bottom', fill='x')

        self.message_entry = tk.Entry(self.input_frame)
        self.message_entry.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

        send_button = tk.Button(self.input_frame, text="Send", command=self.send)
        send_button.grid(row=0, column=1, padx=5, pady=5)

        self.input_frame.grid_columnconfigure(0, weight=1)

        self.chat_text.tag_configure('sender', font=('Arial', 10, 'bold'))
        self.chat_text.tag_configure('message', font=('Arial', 10))
        self.chat_text.tag_configure('timestamp', font=('Arial', 8, 'italic'))

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.after(100, self.start_receiving_messages)

    def start_receiving_messages(self):
        threading.Thread(target=self.receive_message).start()

    def receive_message(self):
        while True:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    continue

                if data.startswith('history:'):
                    self.chat_text.config(state='normal')
                    self.chat_text.delete('1.0', 'end')
                    history_json = data[len('history:'):]
                    messages = json.loads(history_json)
                    for msg in messages:
                        self.display_chat_message(msg['sender'], msg['text'], msg['timestamp'])
                    self.chat_text.config(state='disabled')
                elif data.startswith('{'):  # Update for new user list format
                    users_dict = json.loads(data)
                    self.update_user_lists(users_dict)
                else:
                    if ':' in data:
                        sender, message = data.split(':', 1)
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.display_chat_message(sender, message, timestamp)
            except ConnectionAbortedError:
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def display_chat_message(self, sender, message, timestamp):
        self.chat_text.config(state='normal')
        self.chat_text.insert('end', f"{sender}: ", 'sender')
        self.chat_text.insert('end', f"{message}\n", 'message')
        self.chat_text.insert('end', f"{timestamp}\n", 'timestamp')
        self.chat_text.config(state='disabled')

    def update_user_lists(self, users_dict):
        self.online_list.delete(0, tk.END)
        self.offline_list.delete(0, tk.END)
        for user in users_dict['online']:
            if user != self.name:
                self.online_list.insert(tk.END, user)
        for user in users_dict['offline']:
            if user != self.name:
                self.offline_list.insert(tk.END, user)

    def on_user_select(self, event):
        selection = event.widget.curselection()
        if selection:
            index = selection[0]
            selected_user = event.widget.get(index)
            if selected_user != self.current_chat_user:
                self.current_chat_user = selected_user
                self.socket.send(f"history_request:{self.name}:{self.current_chat_user}".encode('utf-8'))
                self.chat_text.delete('1.0', 'end')

    def send(self):
        message = self.message_entry.get().strip()
        if message and self.current_chat_user:
            self.socket.send(f"{self.current_chat_user}:{message}".encode('utf-8'))
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.display_chat_message("You", message, timestamp)
            self.message_entry.delete(0, 'end')

    def exit_chat(self):
        self.current_chat_user = None
        self.chat_text.config(state='normal')
        self.chat_text.delete('1.0', 'end')
        self.chat_text.config(state='disabled')

    def on_closing(self):
        try:
            self.socket.send("save_history".encode('utf-8'))
        except Exception as e:
            print(f"Error closing connection: {e}")
        finally:
            self.socket.close()
            self.destroy()

if __name__ == "__main__":
    app = MessengerClient()
    app.mainloop()
