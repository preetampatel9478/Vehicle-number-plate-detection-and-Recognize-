import sqlite3
import hashlib
import tkinter as tk
from tkinter import messagebox
import subprocess  # Import subprocess to run another script
import os
import sys
import psutil
import cv2
from PIL import Image, ImageTk

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

class VideoPreview:
    def __init__(self, parent, video_path):
        self.frame = tk.Frame(parent, bg='#2D2D2D', width=400, height=250)
        self.frame.pack_propagate(False)
        self.frame.pack(pady=(0, 10))
        
        self.label = tk.Label(self.frame, bg='#2D2D2D')
        self.label.pack(expand=True)
        
        # Try to open video file, create default preview if fails
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            # Create a default preview image
            default_img = Image.new('RGB', (380, 220), color='#2D2D2D')
            # Add text to the image
            from PIL import ImageDraw
            draw = ImageDraw.Draw(default_img)
            draw.text((190, 110), f"Camera Preview", fill='white', anchor='mm')
            
            # Convert to PhotoImage and display
            self.imgtk = ImageTk.PhotoImage(default_img)
            self.label.configure(image=self.imgtk)
        else:
            self.running = True
            self.update_preview()
    
    def update_preview(self):
        if not hasattr(self, 'running') or not self.running:
            return
            
        if self.label.winfo_exists():
            ret, frame = self.cap.read()
            if ret:
                # Reset video to start when it ends
                if self.cap.get(cv2.CAP_PROP_POS_FRAMES) == self.cap.get(cv2.CAP_PROP_FRAME_COUNT):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
                # Resize frame to fit preview
                frame = cv2.resize(frame, (380, 220))
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2image)
                imgtk = ImageTk.PhotoImage(image=img)
                self.label.imgtk = imgtk
                self.label.configure(image=imgtk)
                self.label.after(30, self.update_preview)
    
    def stop(self):
        self.running = False
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()

def open_camera(camera_num, camera_window):
    lock_file = "app.lock"
    try:
        # Clean up any existing lock file
        if os.path.exists(lock_file):
            os.remove(lock_file)
            
        # Create new lock file
        with open(lock_file, "w") as f:
            f.write(f"App is running with camera {camera_num}")
        
        # Close the camera selection window
        camera_window.destroy()
        
        # Instead of starting a new process, set a global variable for the camera number
        global selected_camera
        selected_camera = camera_num
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start application: {str(e)}")
        if os.path.exists(lock_file):
            os.remove(lock_file)

def show_camera_selection():
    global selected_camera
    selected_camera = None
    
    camera_window = tk.Tk()
    camera_window.title("Select Camera")
    camera_window.geometry("900x800")
    camera_window.configure(bg='#1E1E1E')
    
    # Center window
    window_width = 900
    window_height = 800
    screen_width = camera_window.winfo_screenwidth()
    screen_height = camera_window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    camera_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Title with better styling
    title_label = tk.Label(
        camera_window,
        text="Select Camera for Vehicle Tracking",
        font=('Arial', 24, 'bold'),
        bg='#1E1E1E',
        fg='#FFFFFF'
    )
    title_label.pack(pady=(20, 30))

    # Create grid frame for camera options
    grid_frame = tk.Frame(camera_window, bg='#1E1E1E')
    grid_frame.pack(expand=True, padx=20)

    # Store video previews
    previews = []
    
    # Create 2x2 grid of camera options
    video_path = r"C:\Users\Saumy Saurav\Desktop\saumyproject\major project collage\hello.mp4"  # Updated path
    for i in range(4):
        row = i // 2
        col = i % 2
        
        # Container for each camera option
        camera_frame = tk.Frame(grid_frame, bg='#1E1E1E')
        camera_frame.grid(row=row, column=col, padx=20, pady=20)
        
        # Add video preview with correct path
        preview = VideoPreview(camera_frame, video_path)
        previews.append(preview)
        
        # Camera button with improved styling
        btn = tk.Button(
            camera_frame,
            text=f"Select Camera {i}",
            command=lambda x=i: [p.stop() for p in previews] + [open_camera(x, camera_window)],
            font=('Arial', 14, 'bold'),
            bg='#0078D7',
            fg='white',
            relief=tk.FLAT,
            cursor='hand2',
            width=20,
            height=2
        )
        btn.pack(pady=(0, 10))
        
        # Hover effects
        btn.bind('<Enter>', lambda e, b=btn: b.config(bg='#1982D8'))
        btn.bind('<Leave>', lambda e, b=btn: b.config(bg='#0078D7'))

    # Configure grid
    grid_frame.grid_columnconfigure(0, weight=1)
    grid_frame.grid_columnconfigure(1, weight=1)
    
    # Clean up on window close
    def on_closing():
        for preview in previews:
            preview.stop()
        camera_window.destroy()
    
    camera_window.protocol("WM_DELETE_WINDOW", on_closing)
    camera_window.mainloop()
    
    return selected_camera

def create_table():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

def register_user():
    username = entry_username.get()
    password = entry_password.get()
    
    if not username or not password:
        show_status("All fields are required", True)
        return
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            show_status("Username already exists", True)
            return
            
        # If username doesn't exist, create new user
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)", 
            (username, hash_password(password))
        )
        conn.commit()
        show_status("Registration successful!")
        
    except sqlite3.Error as e:
        show_status(f"Database error: {str(e)}", True)
    finally:
        conn.close()

def login_user():
    username = entry_username.get()
    password = entry_password.get()
    
    if not username or not password:
        show_status("Please enter username and password", True)
        return
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        # Get user from database
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        record = cursor.fetchone()
        
        if record and record[0] == hash_password(password):
            show_status("Login successful!")
            root.logged_in = True
            root.after(1000, root.destroy)  # Close after 1 second
        else:
            show_status("Invalid username or password", True)
            
    except sqlite3.Error as e:
        show_status(f"Database error: {str(e)}", True)
    finally:
        conn.close()

def create_styled_button(parent, text, command, width=20):
    """Create a styled button with hover effect"""
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        bg='#0078D7',
        fg='white',
        font=('Arial', 10, 'bold'),
        relief=tk.FLAT,
        cursor='hand2'
    )
    btn.bind('<Enter>', lambda e: btn.config(bg='#1982D8'))
    btn.bind('<Leave>', lambda e: btn.config(bg='#0078D7'))
    return btn

def create_entry(parent, show=None):
    """Create a styled entry widget"""
    entry = tk.Entry(
        parent,
        font=('Arial', 11),
        bg='#F0F0F0',
        relief=tk.FLAT,
        show=show
    )
    entry.config(insertbackground='#0078D7')  # Cursor color
    return entry

def show_status(message, is_error=False):
    """Show status message with color coding"""
    status_label.config(
        text=message,
        fg='#D32F2F' if is_error else '#2E7D32'
    )
    root.after(3000, lambda: status_label.config(text=""))

def login_system():
    global root, entry_username, entry_password, status_label
    create_table()
    
    root = tk.Tk()
    root.title("AI Vehicle Number Plate Tracking - Login")
    root.geometry("400x500")
    root.configure(bg='white')
    
    # Center window
    window_width = 400
    window_height = 500
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Main frame
    main_frame = tk.Frame(root, bg='white')
    main_frame.place(relx=0.5, rely=0.5, anchor='center')  # Fixed: changed second relx to rely
    
    # Logo/Title
    title_label = tk.Label(
        main_frame,
        text="Number Plate Tracking",
        font=('Arial', 20, 'bold'),
        bg='white',
        fg='#0078D7'
    )
    title_label.pack(pady=(0, 30))
    
    # Login text
    login_label = tk.Label(
        main_frame,
        text="Login to continue",
        font=('Arial', 12),
        bg='white',
        fg='#666666'
    )
    login_label.pack(pady=(0, 20))
    
    # Username
    username_frame = tk.Frame(main_frame, bg='white')
    username_frame.pack(fill='x', pady=(0, 15))
    
    username_label = tk.Label(
        username_frame,
        text="Username",
        font=('Arial', 10),
        bg='white',
        fg='#666666'
    )
    username_label.pack(anchor='w')
    
    entry_username = create_entry(username_frame)
    entry_username.pack(fill='x', pady=(5, 0))
    
    # Password
    password_frame = tk.Frame(main_frame, bg='white')
    password_frame.pack(fill='x', pady=(0, 25))
    
    password_label = tk.Label(
        password_frame,
        text="Password",
        font=('Arial', 10),
        bg='white',
        fg='#666666'
    )
    password_label.pack(anchor='w')
    
    entry_password = create_entry(password_frame, show='•')
    entry_password.pack(fill='x', pady=(5, 0))
    
    # Buttons
    create_styled_button(main_frame, "Login", login_user).pack(pady=(0, 10))
    create_styled_button(main_frame, "Register", register_user).pack(pady=(0, 20))
    
    # Status message label
    status_label = tk.Label(
        main_frame,
        text="",
        font=('Arial', 10),
        bg='white',
        fg='#666666'
    )
    status_label.pack()
    
    root.mainloop()
    
    if hasattr(root, 'logged_in') and root.logged_in:
        camera_num = show_camera_selection()
        return camera_num
    return None
