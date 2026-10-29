"""Interactive MASKER client with an animated underwater authentication UI."""
import socket
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from uuid import uuid4

from PIL import Image, ImageDraw, ImageOps, ImageTk

from constants import IP, PORT, PROJECT_DIR
from encrypt import Encryption


class Client:

    #constants for UI.
    WIDTH, HEIGHT = 1120, 700
    NAVY, BLUE, AQUA = "#064d78", "#087fbc", "#15bdd0"

    def __init__(self):

        #initialize client's methods.
        self.client_socket = None
        self.encryptor = Encryption()
        self.authenticated = False
        self.form_widgets = []
        self.home_widgets = []
        self.action_widgets = []
        self.fish = []
        self.button_number = 0
        self.background_item = None
        self.preview_window = None
        self.last_hidden_path = None

    def submit_auth(self, action, username, password):
        #client authentication to server.
        try:
            if self.encryptor.receive_encrypted_message(self.client_socket) != "AUTH_MENU":
                raise ConnectionError("Invalid server authentication protocol.")
            for value in (action, username, password):
                self.encryptor.send_encrypted_message(self.client_socket, value)
            return self.encryptor.receive_encrypted_message(self.client_socket)
        except Exception as exc:
            return f"ERROR: {exc}"

    @staticmethod

    #design of the text boxes.
    def rounded_box(canvas, x1, y1, x2, y2, radius, **kwargs):
        points = (x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
                  x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
                  x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1)
        return canvas.create_polygon(points, smooth=True, **kwargs)

    @staticmethod
    def _transparent_fish(path, size):

        #function removes the backround of the picture, and leaves the fish only.

        source = Image.open(path).convert("RGB")

        #the supplied art has a light page background. Flood filling starts at
        #the corners, so disconnected white stripes/highlights stay visible.
        for point in ((0, 0), (source.width - 1, 0), (0, source.height - 1), (source.width - 1, source.height - 1)):
            ImageDraw.floodfill(source, point, (255, 0, 255), thresh=60)
        rgba = source.convert("RGBA")
        alpha = rgba.getchannel("A")
        for y in range(rgba.height):
            for x in range(rgba.width):
                if rgba.getpixel((x, y))[:3] == (255, 0, 255):
                    alpha.putpixel((x, y), 0)
        rgba.putalpha(alpha)

        #return the fishonly pic.
        return ImageOps.contain(rgba, size, Image.Resampling.LANCZOS)

    def add_fish(self, canvas):

        #function adds the fish to their starting place on screen.
        blue = ImageTk.PhotoImage(ImageOps.mirror(self._transparent_fish(PROJECT_DIR / "Bluefish.jpg", (132, 132))))
        orange = ImageTk.PhotoImage(ImageOps.mirror(self._transparent_fish(PROJECT_DIR / "OrangeFish.jpg", (142, 142))))
        crub = ImageTk.PhotoImage(ImageOps.mirror(self._transparent_fish(PROJECT_DIR / "crub.jpg", (142, 142))))
        jellyfish = ImageTk.PhotoImage(ImageOps.mirror(self._transparent_fish(PROJECT_DIR / "jellyFish.jpg", (90, 90))))
        # Fish travel in opposite directions and wrap around the screen.
        self.fish = [
            {"item": canvas.create_image(120, 445, image=blue), "image": blue, "speed": 5.0, "width": 132},
            {"item": canvas.create_image(970, 285, image=orange), "image": orange, "speed": -5.0, "width": 142},
            {"item": canvas.create_image(80, 300, image=blue), "image": blue, "speed": 3.0, "width": 132},
            {"item": canvas.create_image(1100, 100, image=orange), "image": orange, "speed": -2.0, "width": 100},
            {"item": canvas.create_image(1100, 400, image=jellyfish), "image": jellyfish, "speed": -2.5, "width": 132},
            {"item": canvas.create_image(20, 200, image=jellyfish), "image": jellyfish, "speed": 2.5, "width": 132},
            {"item": canvas.create_image(30, 600, image=crub), "image": crub, "speed": 2.0, "width": 100},
                    ]

        def swim():

            #moving the fish pics.
            for fish in self.fish:
                canvas.move(fish["item"], fish["speed"], 0)
                x, _ = canvas.coords(fish["item"])
                if fish["speed"] > 0 and x > self.WIDTH + fish["width"]:
                    canvas.coords(fish["item"], -fish["width"], 280)
                elif fish["speed"] < 0 and x < -fish["width"]:
                    canvas.coords(fish["item"], self.WIDTH + fish["width"], 455)
            canvas.after(35, swim)
        swim()

    def set_background(self, filename):

        #open backround based on the current screen.
        path = PROJECT_DIR / filename
        if not path.is_file():
            # The login flow must remain usable if an optional visual asset was
            # not copied with the project.
            messagebox.showwarning("Missing background", f"Could not find {filename}. Using the default background.", parent=self.window)
            return
        source = Image.open(path)
        fitted = ImageOps.fit(source, (self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS)
        self.background_image = ImageTk.PhotoImage(fitted)
        if self.background_item is None:
            self.background_item = self.canvas.create_image(0, 0, image=self.background_image, anchor="nw")
        else:
            self.canvas.itemconfig(self.background_item, image=self.background_image)

    def show_image_preview(self, title, image_path):

        #displays a single image preview in a pop-up window.

        #if not blocking preview
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        try:
            #open image.
            image = Image.open(image_path).convert("RGB")

        except OSError:
            return
        window = tk.Toplevel(self.window)
        window.title(title)
        window.configure(bg="#fff3fa")
        preview = ImageTk.PhotoImage(ImageOps.contain(image, (460, 350), Image.Resampling.LANCZOS))
        tk.Label(window, text=title, bg="#fff3fa", fg=self.NAVY, font=("Segoe UI", 15, "bold")).pack(padx=16, pady=(14, 6))
        label = tk.Label(window, image=preview, bg="#fff3fa")
        label.image = preview
        label.pack(padx=16, pady=6)
        tk.Label(window, text=Path(image_path).name, bg="#fff3fa", fg="#7e4a72", font=("Segoe UI", 9)).pack(pady=(0, 14))
        self.preview_window = window

    def show_decoded_images(self, image_paths):

        #Present every decoded image in a gallery after the operation completes.
        if not image_paths:
            return
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        window = tk.Toplevel(self.window)
        window.title("Decoded images")
        window.configure(bg="#fff3fa")
        tk.Label(window, text="Decoded images", bg="#fff3fa", fg=self.NAVY, font=("Segoe UI", 16, "bold")).pack(padx=16, pady=(14, 8))
        gallery = tk.Frame(window, bg="#fff3fa")
        gallery.pack(padx=12, pady=(0, 14))
        for index, path in enumerate(image_paths):
            image = Image.open(path).convert("RGB")
            preview = ImageTk.PhotoImage(ImageOps.contain(image, (210, 180), Image.Resampling.LANCZOS))
            card = tk.Frame(gallery, bg="#fff3fa")
            card.grid(row=index // 3, column=index % 3, padx=8, pady=8)
            label = tk.Label(card, image=preview, bg="#fff3fa")
            label.image = preview
            label.pack()
            tk.Label(card, text=Path(path).name, bg="#fff3fa", fg="#7e4a72", font=("Segoe UI", 8)).pack(pady=(3, 0))
        self.preview_window = window

    def button(self, _parent, text, command, x, y, width, height, widgets):

        #function creates a pill shaped button.

        self.button_number += 1
        tag = f"button_{self.button_number}"
        shape = self.rounded_box(self.canvas, x, y, x + width, y + height, height // 2,
                                 fill="#f4fcff", outline="#5dc9df", width=2, tags=tag)
        label = self.canvas.create_text(x + width / 2, y + height / 2, text=text,
                                        font=("Segoe UI", 16, "bold"), fill="#064d78", tags=tag)

        def enter(_event):
            self.canvas.itemconfig(shape, fill="#d9f7ff")
            self.canvas.itemconfig(label, fill="#0b94be")

        def leave(_event):
            self.canvas.itemconfig(shape, fill="#f4fcff")
            self.canvas.itemconfig(label, fill="#064d78")

        self.canvas.tag_bind(tag, "<Button-1>", lambda _event: command())
        self.canvas.tag_bind(tag, "<Enter>", enter)
        self.canvas.tag_bind(tag, "<Leave>", leave)
        control = {"canvas": self.canvas, "canvas_items": (shape, label)}
        widgets.append(control)
        return control

    def entry(self, window, x, y, width, placeholder, widgets, secret=False):

       #Function created the entry buttons.

        self.rounded_box(self.canvas, x, y, x + width, y + 40, 20, fill="#f4fcff", outline="#5dc9df", width=2, tags="form")
        field = tk.Entry(window, font=("Segoe UI", 11), fg="#155373", bg="#f4fcff", relief="flat",
                         highlightthickness=0, insertbackground=self.NAVY)
        field.place(x=x + 15, y=y + 3, width=width - 30, height=34)
        field.insert(0, placeholder)
        field.placeholder, field.is_secret = placeholder, secret
        def focus_in(_):
            if field.get() == field.placeholder:
                field.delete(0, tk.END)
                field.configure(show="•" if field.is_secret else "")
        def focus_out(_):
            if not field.get():
                field.configure(show="")
                field.insert(0, field.placeholder)
        field.bind("<FocusIn>", focus_in)
        field.bind("<FocusOut>", focus_out)
        widgets.append(field)
        return field

    @staticmethod
    def value(field):
        return "" if field.get() == field.placeholder else field.get().strip()

    @staticmethod
    def hide(widgets):
        for widget in widgets:
            if isinstance(widget, dict):
                for item in widget["canvas_items"]:
                    widget["canvas"].itemconfig(item, state="hidden")
            else:
                widget.place_forget()

    #shows home only in the right screen.
    def show_home(self):
        self.hide(self.form_widgets)
        self.hide(self.action_widgets)
        self.form_widgets = []
        self.action_widgets = []
        self.canvas.delete("form")
        self.canvas.delete("actions")
        self.canvas.itemconfig("home", state="normal")
        for widget in self.home_widgets:
            if isinstance(widget, dict):
                for item in widget["canvas_items"]:
                    self.canvas.itemconfig(item, state="normal")
            else:
                widget.place(**widget.home_position)

    def show_form(self, action):

        #home screen.

        self.hide(self.home_widgets)
        self.hide(self.form_widgets)
        self.form_widgets = []
        canvas = self.canvas
        self.canvas.delete("form")
        self.rounded_box(canvas, 355, 165, 765, 665, 32, fill="#efffff", outline="#75d9e9", width=3, tags="form")
        title = "Sign In" if action == "LOGIN" else "Sign Up"
        canvas.create_text(560, 230, text=title, font=("Comfortaa", 27, "bold"), fill=self.NAVY, tags="form")
        canvas.create_text(560, 263, text="Dive into your private MASKER space", font=("Comfortaa", 10), fill="#5260cb", tags="form")

        def form_label(text, y):
            label = tk.Label(self.window, text=text, bg="#efffff", fg=self.NAVY, font=("Segoe UI", 10, "bold"), anchor="w")
            label.place(x=425, y=y, width=270)
            self.form_widgets.append(label)

        if action == "LOGIN":
            form_label("Username", 292)
            username = self.entry(self.window, 425, 314, 270, "Enter username", self.form_widgets)
            form_label("Password", 372)
            password = self.entry(self.window, 425, 394, 270, "Enter password", self.form_widgets, secret=True)
        else:
            form_label("Full name", 272)
            full_name = self.entry(self.window, 425, 292, 270, "Enter full name", self.form_widgets)
            form_label("Username", 342)
            username = self.entry(self.window, 425, 362, 270, "Choose username", self.form_widgets)
            form_label("Email address", 412)
            email = self.entry(self.window, 425, 432, 270, "name@example.com", self.form_widgets)
            form_label("Password", 482)
            password = self.entry(self.window, 425, 502, 130, "Password", self.form_widgets, secret=True)
            confirmation = self.entry(self.window, 565, 502, 130, "Repeat", self.form_widgets, secret=True)

        status = tk.StringVar(value="")
        status_label = tk.Label(self.window, textvariable=status, bg="#efffff", fg="#bd315b", font=("Segoe UI", 9, "bold"))
        status_label.place(x=475, y=620, width=270)
        self.form_widgets.append(status_label)

        def display(message, success=False):
            status.set(message.removeprefix("OK: ").removeprefix("ERROR: "))
            status_label.config(fg="#167452" if success else "#bd315b")

        def submit():

            #function creates loginpage only after the user logins successfully.
            entered_username, entered_password = self.value(username), self.value(password)
            if action == "LOGIN":
                if not entered_username or not entered_password:
                    display("Please enter your username and password.")
                    return
            else:
                if not all((self.value(full_name), entered_username, self.value(email), entered_password, self.value(confirmation))):
                    display("Please complete every Sign Up field.")
                    return
                if "@" not in self.value(email):
                    display("Please enter a valid email address.")
                    return
                if entered_password != self.value(confirmation):
                    display("The password confirmation does not match.")
                    return
            response = self.submit_auth(action, entered_username, entered_password)
            display(response, response.startswith("OK:"))
            if action == "LOGIN" and response.startswith("OK:"):
                self.authenticated = True
                self.set_background("backround-afterlogin.jpg")
                self.window.after(500, self.show_action_menu)
                self.canvas.create_text(562, 96, text="Masker - Hila's Web", font=("Segoe UI", 36, "bold"), fill="#b82679", tags="heading")
                self.canvas.create_text(560, 92, text="Masker - Hila's Web", font=("Segoe UI", 36, "bold"), fill="#440320", tags="heading")

        self.button(self.window, "LOGIN" if action == "LOGIN" else "REGISTER", submit, 475, 468 if action == "LOGIN" else 555, 170, 48, self.form_widgets)
        self.button(self.window, "← Back", self.show_home, 375, 535 if action == "LOGIN" else 610, 92, 38, self.form_widgets)

    def show_action_menu(self, result_message=""):
        #function shows the post-login action menu instead of returning to the console.
        
        self.hide(self.home_widgets)
        self.hide(self.form_widgets)
        self.hide(self.action_widgets)
        self.action_widgets = []
        self.canvas.delete("home")
        self.canvas.delete("form")
        self.canvas.delete("actions")
        try:
            self.encryptor.receive_encrypted_message(self.client_socket)  # Server's textual menu; buttons present it visually.
        except Exception as exc:
            self.canvas.create_text(560, 350, text=f"Connection error: {exc}", fill="#8b2043", font=("Segoe UI", 13, "bold"), tags="actions")
            return

        self.rounded_box(self.canvas, 370, 190, 750, 570, 34, fill="#f6c9ee", outline="#ebafe7", width=3, tags="actions")

        self.canvas.create_text(560, 246, text="What would you like to do?", font=("Segoe UI", 20, "bold"), fill="#563040", tags="actions")
        self.canvas.create_text(560, 282, text="Choose an encrypted MASKER action", font=("Segoe UI", 11), fill="#a03168", tags="actions")
        self.button(self.window, "HIDE AN IMAGE", lambda: self.run_action("1"), 415, 326, 290, 54, self.action_widgets)
        self.button(self.window, "DECODE AN IMAGE", lambda: self.run_action("2"), 415, 400, 290, 54, self.action_widgets)
        self.button(self.window, "LOG OUT", lambda: self.run_action("3"), 465, 492, 190, 44, self.action_widgets)
        if result_message:
            self.canvas.create_text(560, 555, text=result_message, font=("Segoe UI", 10, "bold"), fill="#167452", tags="actions")

    def run_action(self, option):
        self.encryptor.send_encrypted_message(self.client_socket, option)
        if option == "3":
            self.authenticated = False
            self.window.destroy()
            return
        if option == "1":
            media_menu = self.encryptor.receive_encrypted_message(self.client_socket)
            if "No media options available." in media_menu:
                self.show_action_menu("No base media is available on the server.")
                return
            media_id = simpledialog.askstring("Choose media", f"Available media:\n{media_menu}\n\nEnter a media ID:", parent=self.window)
            self.encryptor.send_encrypted_message(self.client_socket, media_id or "")
            image_path = filedialog.askopenfilename(parent=self.window, title="Choose an image to hide", filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")])
            self.encryptor.send_encrypted_bytes(self.client_socket, Path(image_path).read_bytes() if image_path else b"")
            result = self.encryptor.receive_encrypted_message(self.client_socket)
            if result.startswith("Data successfully hidden"):
                hidden_data = self.encryptor.receive_encrypted_bytes(self.client_socket)
                output = PROJECT_DIR / f"hidden_image_{uuid4().hex[:8]}.jpg"
                output.write_bytes(hidden_data)
                self.last_hidden_path = output
                result = f"Image hidden successfully. Saved as {output.name}"
        else:
            use_last_hidden = (
                self.last_hidden_path
                and self.last_hidden_path.is_file()
                and messagebox.askyesno("Decode", "Decode the image you just hid?", parent=self.window)
            )
            image_path = str(self.last_hidden_path) if use_last_hidden else filedialog.askopenfilename(
                parent=self.window,
                title="Choose media to decode",
                filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")],
            )
            self.encryptor.send_encrypted_bytes(self.client_socket, Path(image_path).read_bytes() if image_path else b"")
            count = int(self.encryptor.receive_encrypted_message(self.client_socket))
            decoded_paths = []
            for number in range(1, count + 1):
                decoded_data = self.encryptor.receive_encrypted_bytes(self.client_socket)
                extension = ".png" if decoded_data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg"
                output = PROJECT_DIR / f"decoded_image_{number}{extension}"
                output.write_bytes(decoded_data)
                decoded_paths.append(output)
            result = f"Decoded {count} image(s)."
        self.show_action_menu(result)
        if option == "2":
            # A hide operation appends its secret image after the carrier.  If
            # the chosen file was itself hidden before, the final JPEG is the
            # deepest (actual) secret rather than an intermediate cover image.
            self.show_decoded_images(decoded_paths[-1:])

    def authenticate(self):
        self.window = tk.Tk()
        self.window.title("Masker - Hila's Web")
        self.window.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.window.resizable(False, False)
        self.canvas = tk.Canvas(self.window, width=self.WIDTH, height=self.HEIGHT, highlightthickness=0)
        self.canvas.place(x=0, y=0)

        background = ImageOps.fit(Image.open(PROJECT_DIR / "sea-backround2.jpg"), (self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS)
        self.background_image = ImageTk.PhotoImage(background)

        self.background_item = self.canvas.create_image(0, 0, image=self.background_image, anchor="nw")
        self.add_fish(self.canvas)

        self.canvas.create_text(562, 96, text="Masker - Hila's Web", font=("Segoe UI", 36, "bold"), fill="#eaffff", tags="heading")
        self.canvas.create_text(560, 92, text="Masker - Hila's Web", font=("Segoe UI", 36, "bold"), fill="#087fbc", tags="heading")
        self.canvas.create_text(560, 137, text="Choose how you would like to continue", font=("Segoe UI", 13, "bold"), fill="#075a82", tags="home")
        self.rounded_box(self.canvas, 365, 210, 755, 550, 32, fill="#efffff", outline="#75d9e9", width=3, tags="home")
        self.canvas.create_text(560, 270, text="Welcome", font=("Segoe UI", 25, "bold"), fill=self.NAVY, tags="home")
        self.canvas.create_text(560, 303, text="to the hidden ocean!", font=("Segoe UI", 23, "bold"), fill=self.NAVY, tags="home")
        self.canvas.create_text(560, 343, text="Sign in to return to your hidden memories\nor create a new account to begin.", font=("Segoe UI", 12), fill="#3d196c", justify="center", tags="home")
        sign_in = self.button(self.window, "SIGN IN", lambda: self.show_form("LOGIN"), 440, 405, 240, 55, self.home_widgets)
        sign_up = self.button(self.window, "SIGN UP", lambda: self.show_form("REGISTER"), 440, 475, 240, 55, self.home_widgets)
        self.window.mainloop()

    def handle_hide_option(self):
        print(self.encryptor.receive_encrypted_message(self.client_socket))
        self.encryptor.send_encrypted_message(self.client_socket, input("Choose base-media ID: ").strip())
        path = Path(input("Path of image to hide: ").strip())
        self.encryptor.send_encrypted_bytes(self.client_socket, path.read_bytes() if path.is_file() else b"")
        print(self.encryptor.receive_encrypted_message(self.client_socket))

    def handle_decode_option(self):
        path = Path(input("Path of media to decode: ").strip())
        self.encryptor.send_encrypted_bytes(self.client_socket, path.read_bytes() if path.is_file() else b"")
        count = int(self.encryptor.receive_encrypted_message(self.client_socket))
        for number in range(1, count + 1):
            output = PROJECT_DIR / f"decoded_image_{number}.jpg"
            output.write_bytes(self.encryptor.receive_encrypted_bytes(self.client_socket))
            print(f"Saved {output}")

    def run(self):
        try:
            self.client_socket = socket.socket()
            self.client_socket.connect((IP, PORT))
            self.authenticate()
        finally:
            if self.client_socket:
                self.client_socket.close()


if __name__ == "__main__":
    Client().run()
