"""MASKER server: authenticated encrypted client handling and status UI."""
import socket
import threading
import tkinter as tk
from tkinter import Button, Label, Listbox, Toplevel, scrolledtext

from PIL import Image, ImageTk

from constants import DB_CONFIG, IP, PORT, project_path
from create_tables import create_all_tables, populate_media_menu
from db_manager import DatabaseManager
from decode_png import ImageExtractor
from encrypt import Encryption
from hide_png import DataHider


class Server:
    def __init__(self):
        self.db_manager = DatabaseManager(**DB_CONFIG)
        create_all_tables(self.db_manager)
        populate_media_menu(self.db_manager)
        self.encryptor = Encryption()
        self.root = tk.Tk()
        self.root.withdraw()
        self.log_text = self.client_listbox = None
        self.showing_all_clients = False

    def update_gui_log(self, message):
        if self.log_text:
            self.root.after(0, lambda: self._write_log(message))

    def _write_log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.yview(tk.END)

    def update_client_list(self):

        if not self.client_listbox:
            return
        rows = self.db_manager.get_client_rows(not self.showing_all_clients)
        def redraw():
            self.client_listbox.delete(0, tk.END)
            for client_id, ip, port, _, connected, sent, decoded in rows:
                status = "Connected" if connected else "Disconnected"
                self.client_listbox.insert(tk.END, f"{client_id[:12]}... | {status} | sent: {sent} | decoded: {decoded} | {ip}:{port}")
        self.root.after(0, redraw)

    def toggle_all_clients(self):
        self.showing_all_clients = not self.showing_all_clients
        self.all_clients_button.config(text="Show connected clients" if self.showing_all_clients else "Show all clients")
        self.update_client_list()

    def show_client_details(self, _event=None):
        selection = self.client_listbox.curselection()
        if not selection:
            return
        short_id = self.client_listbox.get(selection[0]).split(" | ", 1)[0].removesuffix("...")
        client = next((row for row in self.db_manager.get_client_rows(False) if row[0].startswith(short_id)), None)
        if not client:
            return
        client_id, ip, port, seen, connected, sent, decoded = client
        window = Toplevel(self.root)
        window.title("Client details")
        for line in (f"Client ID: {client_id}", f"IP: {ip}", f"Port: {port}", f"Last seen: {seen}",
                     f"Connected now: {'yes' if connected else 'no'}", f"Files hidden: {sent}", f"Files decoded: {decoded}"):
            Label(window, text=line, anchor="w").pack(fill="x", padx=12, pady=2)

    def play_audio(self):
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(str(project_path("sea-waves-with-birds-loop.wav")))
            pygame.mixer.music.play()
            pygame.mixer.music.queue(str(project_path("montana skies.mp3")))
        except Exception as exc:
            self.update_gui_log(f"Audio unavailable: {exc}")

    def authenticate_client(self, client_socket):
        while True:
            self.encryptor.send_encrypted_message(client_socket, "AUTH_MENU")
            action = self.encryptor.receive_encrypted_message(client_socket)
            if action not in {"REGISTER", "LOGIN"}:
                self.encryptor.send_encrypted_message(client_socket, "ERROR: Choose Register or Login.")
                continue
            username = self.encryptor.receive_encrypted_message(client_socket)
            password = self.encryptor.receive_encrypted_message(client_socket)
            if action == "REGISTER":
                ok, message = self.db_manager.register_user(username, password)
                self.encryptor.send_encrypted_message(client_socket, ("OK: " if ok else "ERROR: ") + message)
                continue
            ok, client_id, message = self.db_manager.verify_user(username, password)
            self.encryptor.send_encrypted_message(client_socket, ("OK: " if ok else "ERROR: ") + message)
            if ok:
                return client_id

    def handle_client(self, client_socket):
        client_id = None
        try:
            client_id = self.authenticate_client(client_socket)
            ip, port = client_socket.getpeername()
            self.db_manager.connect_client(client_id, ip, port)
            self.update_gui_log(f"Client {client_id[:12]} connected.")
            self.update_client_list()
            while True:
                self.encryptor.send_encrypted_message(client_socket, "MENU\n1: Hide Data\n2: Decode Data\n3: Logout")
                option = self.encryptor.receive_encrypted_message(client_socket)
                if option == "1":
                    result = DataHider(client_socket, self.db_manager, client_id).run()
                    if result:
                        self.db_manager.record_action(client_id, "hide", result[2])
                elif option == "2":
                    result = ImageExtractor(client_socket, self.db_manager, client_id).run()
                    if result:
                        self.db_manager.record_action(client_id, "decode", result[2])
                elif option == "3":
                    break
                else:
                    self.encryptor.send_encrypted_message(client_socket, "Invalid option.")
                self.update_client_list()
        except Exception as exc:
            self.update_gui_log(f"Client error: {exc}")
        finally:
            if client_id:
                self.db_manager.disconnect_client(client_id)
            client_socket.close()
            self.update_client_list()

    def start_server(self):
        with socket.socket() as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((IP, PORT))
            server_socket.listen()
            self.update_gui_log(f"Server started on {IP}:{PORT}.")
            while True:
                client_socket, _ = server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def create_gui(self):
        splash = Toplevel(self.root)
        splash.geometry("400x400")
        splash.overrideredirect(True)
        logo = ImageTk.PhotoImage(Image.open(project_path("sea-backround2.jpg")).resize((400, 400)))
        Label(splash, image=logo).pack()
        Label(splash, text="MASKER - Hila's Web'\nVersion 1.0", fg="white", bg="black", font=("Arial", 16, "bold")).place(relx=.5, rely=.86, anchor="center")
        splash.logo = logo
        self.root.title("MASKER Server")
        self.root.geometry("700x600")
        background = ImageTk.PhotoImage(Image.open(project_path("sea-backround2.jpg")))
        Label(self.root, image=background).place(relwidth=1, relheight=1)
        self.root.background = background
        self.log_text = scrolledtext.ScrolledText(self.root, state=tk.DISABLED, height=12, bg="black", fg="white")
        self.log_text.pack(expand=True, fill="both", padx=10, pady=5)
        Label(self.root, text="MASKER clients", font=("Arial", 14, "bold")).pack(pady=5)
        self.client_listbox = Listbox(self.root, bg="black", fg="white")
        self.client_listbox.pack(expand=True, fill="both", padx=10, pady=5)
        self.client_listbox.bind("<Double-Button-1>", self.show_client_details)
        controls = tk.Frame(self.root)
        controls.pack(pady=8)
        Button(controls, text="Show last encrypted image", command=self.show_last_hidden_image).pack(side="left", padx=5)
        self.all_clients_button = Button(controls, text="Show all clients", command=self.toggle_all_clients)
        self.all_clients_button.pack(side="left", padx=5)
        threading.Thread(target=self.start_server, daemon=True).start()
        self.root.after(4000, lambda: (splash.destroy(), self.root.deiconify(), self.play_audio(), self.update_client_list()))
        self.root.mainloop()


if __name__ == "__main__":
    Server().create_gui()
