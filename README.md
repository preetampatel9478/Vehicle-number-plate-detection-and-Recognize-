# AI Vehicle Number Plate Tracking System

## Overview

This project is an *AI-powered vehicle number plate tracking system* with a user-friendly GUI. It detects vehicles, estimates their speed, recognizes number plates, and stores all details (including images) in a searchable database. The system uses YOLOv8 for detection, Google Gemini AI for extracting vehicle details, and MySQL for data storage. It is designed for traffic monitoring, law enforcement, and smart city applications.

---

## Features

- *User Authentication:* Secure login and registration system.
- *Camera Selection:* Choose from multiple cameras or upload video/image files.
- *Live Vehicle Detection:* Real-time vehicle detection and speed estimation using YOLOv8.
- *Number Plate Recognition:* Extracts vehicle details (model, color, company, number plate) using Google Gemini AI.
- *Database Storage:* Stores all records and vehicle images in MySQL.
- *Search & View:* Search records by number plate, date, time, model, color, or company. View vehicle images.
- *Performance Visualization:* Analyze system performance with charts.
- *Modern GUI:* Built with Tkinter for easy use.

---

## Project Structure


major project collage/
│
├── logintest.py           # Main application (GUI, detection, tracking)
├── login.py               # User login and registration logic
├── database_utils.py      # Database operations and search UI
├── profomence.py          # System performance analysis (charts)
├── users.db               # SQLite DB for user authentication
├── vehicle_data1 (MySQL)  # MySQL DB for vehicle records
├── crop/                  # Folder for cropped vehicle images
├── performance_metrics.png# Performance chart output
└── ... (other files)


---

## Requirements

- Python 3.8+
- MySQL Server (for vehicle data)
- Required Python packages:
  - opencv-python
  - numpy
  - pillow
  - mysql-connector-python
  - ultralytics
  - shapely
  - langchain-core
  - langchain-google-genai
  - tkinter (usually included with Python)

---

## Setup Instructions

1. *Clone or Download the Project*

2. *Install Python Dependencies*
   sh
   pip install opencv-python numpy pillow mysql-connector-python ultralytics shapely langchain-core langchain-google-genai
   

3. *Set Up MySQL Database*
   - Make sure MySQL server is running.
   - The app will auto-create the vehicle_data1 database and vehicle_records table on first run.

4. *Run the Application*
   sh
   python logintest.py
   

5. *Login/Register*
   - Register a new user or login with existing credentials.
   - Select a camera or upload a video/image to start tracking.

---

## Usage

- *Start Tracking:* Choose input source (camera, video, image) and click "Start Tracking".
- *View Records:* All detected vehicles are stored in the database. Use the search panel to filter records.
- *View Images:* Double-click a record or use the "View Vehicle Image" button to see the vehicle image.
- *Performance:* Run profomence.py to view system performance charts.

---

## Notes

- *Google Gemini API Key:* Replace the placeholder in logintest.py with your actual API key for Gemini AI.
- *User Data:* User authentication uses a local SQLite database (users.db).
- *Images:* Cropped vehicle images are saved in the crop/ folder and stored as BLOBs in MySQL.

---

## Screenshots

(Add screenshots of the login screen, main dashboard, detection in action, and search results here)

---

## License

This project is for educational and research purposes.

---

## Credits

- YOLOv8 by Ultralytics
- Google Gemini AI
- Python, OpenCV, Tkinter, MySQL

---
