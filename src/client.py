import tkinter as tk
from tkinter import simpledialog, scrolledtext
import socket
import threading

def receive_messages(client_socket, text_area):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            text_area.insert(tk.END, message + '\n')
        except:
            break

def send_message(client_socket, message_entry, username):
    message = f"{username}: {message_entry.get()}"
    client_socket.send(message.encode('utf-8'))
    message_entry.delete(0, tk.END)

def main():
    # Login window
    login_window = tk.Tk()
    login_window.withdraw() # Hide the main window
    username = simpledialog.askstring("Username", "Please enter your username", parent=login_window)
    login_window.destroy()

    # Main chat window
    window = tk.Tk()
    window.title("Chat Application")

    text_area = scrolledtext.ScrolledText(window)
    text_area.pack(padx=20, pady=5)

    message_entry = tk.Entry(window, width=100)
    message_entry.pack(padx=20, pady=5)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5555))

    send_button = tk.Button(window, text="Send", command=lambda: send_message(client_socket, message_entry, username))
    send_button.pack(padx=20, pady=5)

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket, text_area))
    receive_thread.start()

    window.mainloop()

if __name__ == "__main__":
    main()
