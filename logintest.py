
import cv2
import os
import base64
import threading
import mysql.connector   # type: ignore
from time import time
import numpy as np # type: ignore
from ultralytics.solutions.solutions import BaseSolution # type: ignore
from ultralytics.utils.plotting import Annotator, colors # type: ignore
from datetime import datetime
from shapely.geometry import LineString # type: ignore
from langchain_core.messages import HumanMessage # type: ignore
import google.generativeai as genai # type: ignore
from langchain.schema import HumanMessage as LangchainHumanMessage
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
from tkinter import scrolledtext
from database_utils import fetch_data, create_database_table_ui
from login import login_system
import tkinter as tk
from tkinter import Label
import sys
import atexit

# Add at the top of the file
def cleanup():
    lock_file = "app.lock"
    if os.path.exists(lock_file):
        os.remove(lock_file)

atexit.register(cleanup)

# More robust command line argument handling
def get_camera_number():
    try:
        # Skip the first argument (script name) and look for a valid camera number
        for arg in sys.argv[1:]:
            try:
                return int(arg)
            except ValueError:
                continue
        return 0  # Default camera if no valid number found
    except Exception:
        return 0  # Default to camera 0 if any error occurs

camera_number = get_camera_number()

# Set up Google API Key (Use a secure method to store it)
GOOGLE_API_KEY = "AIzaSyBvJpGAl9vsS-TpeYdsKTtPXopbNJNkDvQ"  # Replace with your actual API key
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# MySQL Database Configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",  # You may need to set your actual MySQL password here
    "database": "vehicle_data1"
}

# Add flag to control database operations
USE_DATABASE = False  # Set to False to skip database operations for testing

def initialize_database():
    """Creates the database and table if they don't exist, handling existing tables"""
    if not USE_DATABASE:
        print("⚠️ Database operations are disabled for testing")
        return
        
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"]
        )
        cursor = conn.cursor()

        # Create database if not exists (modified)
        cursor.execute("CREATE DATABASE IF NOT EXISTS vehicle_data1")
        cursor.execute("USE vehicle_data1")
        # Check if table exists first
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            track_id INT,
            speed INT,
            date_time DATETIME,
            vehicle_model VARCHAR(255),
            vehicle_color VARCHAR(100),
            vehicle_company VARCHAR(255),
            number_plate VARCHAR(50),
            image_data LONGBLOB
        ) ENGINE=InnoDB
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database and table are ready!")

    except mysql.connector.Error as err:
        if err.errno == 1813:
            print("ℹ️ Table already exists - continuing with existing table")
        else:
            print(f"❌ Database Error: {err}")
    except Exception as e:
        print(f"❌ General Error: {e}")

# Call the function to initialize the database & table
initialize_database()

def insert_into_database(track_id, speed, timestamp, model, color, company, number_plate, image_path):
    """Insert detected vehicle details along with the cropped image into MySQL."""
    try:
        print(f"📌 DEBUG: insert_into_database called with:")
        print(f"Track ID: {track_id}, Speed: {speed}, Timestamp: {timestamp}")
        print(f"Model: {model}, Color: {color}, Company: {company}, Number Plate: {number_plate}")
        print(f"Image Path: {image_path}")
        
        if not USE_DATABASE:
            print("⚠️ Database insert skipped (database operations disabled)")
            return
            
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return

        with open(image_path, "rb") as img_file:
            image_binary = img_file.read()  # Convert image to binary

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # ✅ Ensure consistent formatting (trim spaces, uppercase)
        number_plate = number_plate.strip().upper()
        if not number_plate:
            print("❌ Error: Extracted number plate is empty!")
            return

        query = """
        INSERT INTO vehicle_records (track_id, speed, date_time, vehicle_model, vehicle_color, vehicle_company, number_plate, image_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (track_id, speed, timestamp, model, color, company, number_plate, image_binary)

        print(f"📌 Storing Image in Database - Number Plate: {number_plate}")

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Data inserted successfully for Number Plate: {number_plate}")

    except mysql.connector.Error as err:
        print(f"❌ Database Insert Error: {err}")
    except Exception as e:
        print(f"❌ General Error: {e}")    

class SpeedEstimator(BaseSolution):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialize_region()
        self.spd = {}  
        self.trkd_ids = []  
        self.trk_pt = {}  
        self.trk_pp = {}  
        self.saved_ids = set()  
        # Initialize Google Generative AI directly
        genai.configure(api_key=GOOGLE_API_KEY)
        self.gemini_model = genai.GenerativeModel('gemini-pro-vision')
        
        # Adjusted calibration factors for better speed estimation
        self.pixels_per_meter = 15.0    # Reduced from 30.0 to increase speedorkload on traffic management personnel, allowing them to focus on more critical tasks. Additionally, the system's capability to maintain detailed digital records of vehicle movements and speed violations could serve as a deterrent to traffic rule violations, promoting safer driving behavior. The privacy-conscious design, which includes secure data handling and controlled access through user authentication, addresses public concerns about surveillance while maintaining transparency in traffic monitoring. Furthermore, the system's adaptability to various scenarios, from traffic intersections to parking facilities, makes it a valuable tool for both public authorities and private institutions looking to enhance their traffic management capabilities while promoting road safety awareness in the community.
        self.fps_adjustment = 2.5       # Increased from 1.2 for better frame rate compensation
        self.speed_correction = 3.2     # Increased from 1.8 to scale up final speed
        self.min_speed = 15            # Minimum speed threshold
        self.max_speed = 120           # Maximum speed threshold
        
        # Enhanced vehicle classes with common names
        self.vehicle_classes = {
            2: {'name': 'CAR', 'display': 'CAR'},
            3: {'name': 'MOTORCYCLE', 'display': ['BIKE', 'SCOOTY']},  # Alternates between these
            5: {'name': 'BUS', 'display': 'BUS'},
            6: {'name': 'AUTO', 'display': 'AUTO-RICKSHAW'},  # Added auto-rickshaw
            7: {'name': 'TRUCK', 'display': 'TRUCK'},
            8: {'name': 'AUTO', 'display': 'E-RICKSHAW'}  # Added e-rickshaw
        }
          # Counter for alternating two-wheeler labels
        self.two_wheeler_counter = 0
        os.makedirs("crop", exist_ok=True)
        
    def draw_detection_line(self, im0):
        """Draw detection line on the image"""
        if len(self.region) >= 2:
            pt1 = tuple(map(int, self.region[0]))
            pt2 = tuple(map(int, self.region[1]))
            cv2.line(im0, pt1, pt2, color=(104, 0, 123), thickness=self.line_width * 2)
            
    def analyze_and_save_response(self, image_path, track_id, speed, timestamp):
        """Analyzes the image with AI and saves response + image to MySQL."""
        try:
            if not os.path.exists(image_path):  # ✅ Check if image exists
                print(f"❌ Image not found: {image_path}")
                return

            # Load image for Gemini
            img = Image.open(image_path)
            
            # Create prompt for the model
            prompt = "Extract ONLY these details:\n| Vehicle Model | Color | Company | Number Plate |\n|--------------|--------|---------|------------|"
            
            # Generate content with the image
            response = self.gemini_model.generate_content([prompt, img])
            response_text = response.text.strip()

            print(f"📌 DEBUG: Gemini AI Response:\n{response_text}")

            valid_rows = [
                row.split("|")[1:-1]
                for row in response_text.split("\n")
                if "|" in row and "Vehicle Model" not in row and "---" not in row
            ]

            vehicle_info = valid_rows[0] if valid_rows else ["Unknown", "Unknown", "Unknown", "Unknown"]
            number_plate = vehicle_info[3]  # Extracted number plate

            print(f"📌 Extracted Number Plate: {number_plate}")

            # ✅ Insert into database with image path
            insert_into_database(track_id, speed, timestamp, vehicle_info[0], vehicle_info[1], vehicle_info[2], number_plate, image_path)

        except Exception as e:
            print(f"❌ Error invoking Gemini AI: {e}")


          # Remove duplicate database insertion - we already do this in insert_into_database
        # This section was causing duplicate inserts and variable undefined errors
        if False:  # Disabled code block - keeping for reference but never executing
            try:
                with open(image_path, "rb") as img_file:
                    image_binary = img_file.read()
    
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
    
                query = """
                INSERT INTO vehicle_records (track_id, speed, date_time, vehicle_model, vehicle_color, vehicle_company, number_plate, image_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (track_id, speed, timestamp, model, color, company, number_plate, image_binary)
    
                cursor.execute(query, values)
                conn.commit()
                cursor.close()
                conn.close()
    
                print(f"✅ Image and data stored for Number Plate: {number_plate}")
    
            except Exception as e:
                print(f"❌ Database Insert Error: {e}")

    def estimate_speed(self, im0):
        """Estimate speed of detected vehicles in the video."""
        self.annotator = Annotator(im0, line_width=self.line_width)
        self.extract_tracks(im0)
        
        # Filter for vehicle detections only
        vehicle_indices = [i for i, cls in enumerate(self.clss) if int(cls) in self.vehicle_classes]
        
        if not vehicle_indices:
            return im0
            
        self.draw_detection_line(im0)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for idx in vehicle_indices:
            box = self.boxes[idx]
            track_id = self.track_ids[idx]
            cls = int(self.clss[idx])
            
            # Get vehicle type with special handling for two-wheelers
            vehicle_info = self.vehicle_classes[cls]
            if cls == 3:  # Motorcycle/Scooty
                # Alternate between bike and scooty based on track_id
                display_name = vehicle_info['display'][track_id % 2]
            else:
                display_name = vehicle_info['display']

            # Rest of tracking logic...
            self.store_tracking_history(track_id, box)

            if track_id not in self.trk_pt:
                self.trk_pt[track_id] = time()
            if track_id not in self.trk_pp:
                self.trk_pp[track_id] = box

            prev_pos = self.trk_pp[track_id]
            curr_pos = box

            if LineString([prev_pos[:2], curr_pos[:2]]).intersects(LineString(self.region)):
                direction = "known"
            else:
                direction = "unknown"

            if direction == "known" and track_id not in self.trkd_ids:
                self.trkd_ids.append(track_id)
                time_difference = time() - self.trk_pt[track_id]
                if time_difference > 0:
                    # Calculate distance in pixels with scaling factor
                    pixel_distance = np.linalg.norm(np.array(curr_pos[:2]) - np.array(prev_pos[:2]))
                    
                    # Apply improved distance calculation
                    distance_meters = pixel_distance / self.pixels_per_meter
                    
                    # Calculate base speed with fps adjustment
                    base_speed = (distance_meters * self.fps_adjustment) / time_difference
                    
                    # Convert to km/h with correction factor
                    speed_kmh = (base_speed * 3.6) * self.speed_correction
                    
                    # Apply speed thresholds and smoothing
                    if speed_kmh < self.min_speed:
                        speed_kmh = self.min_speed + (speed_kmh * 0.5)
                    elif speed_kmh > self.max_speed:
                        speed_kmh = self.max_speed
                    
                    # Store rounded speed
                    self.spd[track_id] = round(speed_kmh)

            self.trk_pt[track_id] = time()
            self.trk_pp[track_id] = curr_pos

            speed_value = self.spd.get(track_id, 0)
            # Update label with enhanced vehicle type
            label = f"{display_name} ID:{track_id} {speed_value}km/h"
            self.annotator.box_label(box, label=label, color=colors(track_id, True))

            # ✅ Ensure Image is Saved and Passed to Analysis
            if track_id in self.spd and track_id not in self.saved_ids:
                x1, y1, x2, y2 = map(int, box)
                cropped_image = im0[y1:y2, x1:x2]

                if cropped_image.size != 0:
                    image_filename = f"crop/{track_id}_{speed_value}kmh.jpg"
                    cv2.imwrite(image_filename, cropped_image)
                    print(f"📷 Saved image: {image_filename}")  # Debugging print

                    # ✅ Pass the Image Path to `analyze_and_save_response`
                    threading.Thread(
                        target=self.analyze_and_save_response,
                        args=(image_filename, track_id, speed_value, current_time),
                        daemon=True
                    ).start()

                    self.saved_ids.add(track_id)

        self.display_output(im0)
        return im0


def mouse_callback(event, x, y, flags, param):
    """Prints x, y coordinates when the mouse moves over the OpenCV window."""
    if event == cv2.EVENT_MOUSEMOVE:
        print(f"Mouse Position: x={x}, y={y}")

class VehicleTrackingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Vehicle Speed Tracker")
        self.root.geometry("1000x800")  # Adjusted main window size
        self.root.configure(bg="#f0f0f0")
        
        # Add thread safety
        self._running = False
        self._lock = threading.Lock()
        
        # Add cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Variables
        self.input_source = tk.StringVar(value="camera")
        self.video_path = ""
        self.image_path = ""
        self.is_running = False
        self.cap = None
        self.speed_estimator = None
        self.region_points = [(0, 250), (1018, 250)]  # Default middle position
        
        # Setup UI
        self.setup_ui()
        self.auto_refresh_data()
        
    def on_closing(self):
        """Handle cleanup when closing the application"""
        with self._lock:
            self._running = False
            if self.cap is not None:
                self.cap.release()
        cleanup()  # Call the global cleanup function
        self.root.destroy()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel (controls) - made wider
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5, ipadx=10)
        
        # Input source selection
        ttk.Label(control_frame, text="Input Source:").pack(anchor=tk.W, pady=(0, 5))
        
        self.camera_radio = ttk.Radiobutton(
            control_frame, text="Live Camera", 
            variable=self.input_source, value="camera"
        )
        self.camera_radio.pack(anchor=tk.W)
        
        self.video_radio = ttk.Radiobutton(
            control_frame, text="Video File", 
            variable=self.input_source, value="video"
        )
        self.video_radio.pack(anchor=tk.W)
        
        self.image_radio = ttk.Radiobutton(
            control_frame, text="Single Image", 
            variable=self.input_source, value="image"
        )
        self.image_radio.pack(anchor=tk.W)
        
        # File selection button
        self.file_button = ttk.Button(
            control_frame, 
            text="Select File", 
            command=self.select_file,
            state=tk.DISABLED
        )
        self.file_button.pack(pady=5, fill=tk.X)
        
        # Detection Line Controls
        line_control_frame = ttk.LabelFrame(control_frame, text="Detection Line Control", padding=5)
        line_control_frame.pack(fill=tk.X, pady=5)
        
        # Y-position slider
        ttk.Label(line_control_frame, text="Line Height:").pack(anchor=tk.W)
        self.y_slider = ttk.Scale(
            line_control_frame,
            from_=0,
            to=500,
            orient=tk.HORIZONTAL
        )
        self.y_slider.set(250)
        self.y_slider.pack(fill=tk.X, pady=(0, 5))
        
        # Angle slider
        ttk.Label(line_control_frame, text="Line Angle:").pack(anchor=tk.W)
        self.angle_slider = ttk.Scale(
            line_control_frame,
            from_=-45,
            to=45,
            orient=tk.HORIZONTAL
        )
        self.angle_slider.set(0)
        self.angle_slider.pack(fill=tk.X, pady=(0, 5))

        # Bind sliders to update method
        self.y_slider.configure(command=self.update_detection_line)
        self.angle_slider.configure(command=self.update_detection_line)

        # Reset button
        ttk.Button(
            line_control_frame,
            text="Reset Line Position",
            command=self.reset_detection_line
        ).pack(fill=tk.X, pady=5)

        # Control buttons
        self.start_button = ttk.Button(
            control_frame, 
            text="Start Tracking", 
            command=self.start_tracking,
            style="Accent.TButton"
        )
        self.start_button.pack(pady=(15, 5), fill=tk.X)
        
        self.stop_button = ttk.Button(
            control_frame, 
            text="Stop", 
            command=self.stop_tracking,
            state=tk.DISABLED
        )
        self.stop_button.pack(pady=5, fill=tk.X)
        
        # Right panel (display) - made smaller
        display_frame = ttk.LabelFrame(main_frame, text="Live View", padding=10)
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a container frame to limit video size
        video_container = ttk.Frame(display_frame, width=740, height=360)  # 16:9 aspect ratio
        video_container.pack(padx=5, pady=5)
        video_container.pack_propagate(False)  # Prevent resizing
        
        self.video_label = ttk.Label(video_container)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Bottom panel (logs)
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding=10)
        log_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for colored text
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("info", foreground="blue")
        
        # Bind radio buttons to update file button state
        self.input_source.trace_add("write", self.update_file_button_state)
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)


        # Create Table for Database Records
        self.tree = create_database_table_ui(main_frame) 
    
    def auto_refresh_data(self):
        """Automatically fetch data every 5 seconds."""
        fetch_data(self.tree)  # Fetch latest data
        self.root.after(5000, self.auto_refresh_data)     
    def update_file_button_state(self, *args):
        if self.input_source.get() in ["video", "image"]:
            self.file_button.config(state=tk.NORMAL)
        else:
            self.file_button.config(state=tk.DISABLED)
    
    def select_file(self):
        file_types = []
        if self.input_source.get() == "video":
            file_types = [("Video Files", "*.mp4 *.avi *.mov")]
        elif self.input_source.get() == "image":
            file_types = [("Image Files", "*.jpg *.jpeg *.png")]
            
        path = filedialog.askopenfilename(filetypes=file_types)
        if path:
            if self.input_source.get() == "video":
                self.video_path = path
                self.log_message(f"Selected video file: {path}", "info")
            else:
                self.image_path = path
                self.log_message(f"Selected image file: {path}", "info")
    
    def log_message(self, message, tag="info"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n", tag)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
    
    def update_detection_line(self, _=None):
        """Update detection line based on slider values"""
        y_pos = self.y_slider.get()
        angle = self.angle_slider.get()
        
        # Calculate line endpoints based on angle
        center_x = 1020 // 2
        length = 1020  # Line length
        
        # Convert angle to radians and calculate offset
        import math
        rad_angle = math.radians(angle)
        dx = (length / 2) * math.cos(rad_angle)
        dy = (length / 2) * math.sin(rad_angle)
        
        # Calculate new points
        x1 = int(center_x - dx)
        x2 = int(center_x + dx)
        y1 = int(y_pos - dy)
        y2 = int(y_pos + dy)
        
        # Update region points
        self.region_points = [(x1, y1), (x2, y2)]
        
        # Update speed estimator if running
        if self.speed_estimator:
            self.speed_estimator.region = self.region_points

    def reset_detection_line(self):
        """Reset detection line to default position"""
        self.y_slider.set(250)
        self.angle_slider.set(0)
        self.update_detection_line()

    def process_single_image(self):
        try:
            # Clean up any existing video resources
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            if self.speed_estimator is not None:
                self.speed_estimator = None
            
            image = cv2.imread(self.image_path)
            if image is None:
                raise ValueError("Could not read the image file")
            image = cv2.resize(image, (740, 360))  # Match container size
            
            # Initialize speed estimator
            speed_estimator = SpeedEstimator(region=self.region_points, model="yolov8n.pt", line_width=2)
            
            # Get current timestamp
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Process the image
            speed_estimator.analyze_and_save_response(
                self.image_path,
                track_id=1,
                speed=0,
                timestamp=current_time
            )
            
            # Display the image
            rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            self.log_message(f"Processed image: {self.image_path}", "success")
            
            # Reset state for next operation
            with self._lock:
                self._running = False
            
            # Re-enable controls
            self.start_button.config(state=tk.NORMAL)
            self.camera_radio.config(state=tk.NORMAL)
            self.video_radio.config(state=tk.NORMAL)
            self.image_radio.config(state=tk.NORMAL)
            self.update_file_button_state()
            
        except Exception as e:
            self.log_message(f"Image processing error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to process image:\n{str(e)}")

    def start_tracking(self):
        with self._lock:
            if self._running:
                return
            
            # Clean up existing resources
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            if self.speed_estimator is not None:
                self.speed_estimator = None
            
            self._running = True
            
        try:
            self.update_detection_line()
            source = self.input_source.get()
            
            if source == "camera":
                self.cap = cv2.VideoCapture(0)
                self.log_message("Starting live camera feed...", "info")
            elif source == "video":
                if not self.video_path:
                    messagebox.showerror("Error", "Please select a video file first")
                    return
                self.cap = cv2.VideoCapture(self.video_path)
                self.log_message(f"Processing video: {self.video_path}", "info")
            elif source == "image":
                if not self.image_path:
                    messagebox.showerror("Error", "Please select an image file first")
                    return
                self.process_single_image()
                return
            
            # Initialize speed estimator
            self.speed_estimator = SpeedEstimator(region=self.region_points, model="yolov8n.pt", line_width=2)
            
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.camera_radio.config(state=tk.DISABLED)
            self.video_radio.config(state=tk.DISABLED)
            self.image_radio.config(state=tk.DISABLED)
            self.file_button.config(state=tk.DISABLED)
            
            # Start video processing in a separate thread
            threading.Thread(target=self.process_video, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"Error starting tracking: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to start tracking:\n{str(e)}")
            with self._lock:
                self._running = False

    def stop_tracking(self):
        with self._lock:
            self._running = False
            if self.cap is not None:
                self.cap.release()
                self.cap = None
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.camera_radio.config(state=tk.NORMAL)
        self.video_radio.config(state=tk.NORMAL)
        self.image_radio.config(state=tk.NORMAL)
        self.update_file_button_state()
        self.log_message("Tracking stopped", "info")
    
    def process_video(self):
        try:
            with self._lock:
                if not self._running:
                    return
                if not self.cap or not self.cap.isOpened():
                    return
                ret, frame = self.cap.read()
            
            if not ret:
                self.stop_tracking()
                return

            # Update frame size to match container (740x360)
            frame = cv2.resize(frame, (740, 360))
            result = self.speed_estimator.estimate_speed(frame)
            
            # Convert to RGB and display
            rgb_frame = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
            # Schedule next frame update only if still running
            with self._lock:
                if self._running:
                    self.root.after(10, self.process_video)

        except Exception as e:
            self.log_message(f"Video processing error: {str(e)}", "error")
            self.stop_tracking()

def main():
    # Get camera number from login system
    camera_num = login_system()
    if camera_num is None:  # Login failed or cancelled
        return
    
    # Store camera number for later use
    global camera_number
    camera_number = camera_num
    
    # Create main application window
    root = tk.Tk()
    app = VehicleTrackingApp(root)
    
    # Style configuration
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Accent.TButton', foreground='white', background='#0078d7')

    try:
        root.mainloop()
    finally:
        cleanup()
        sys.exit()

if __name__ == "__main__":
    main()