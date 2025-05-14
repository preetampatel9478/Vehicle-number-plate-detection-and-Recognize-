import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import io
import sqlite3


# Database Configuration (Ensure it matches your main file)
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",
    "database": "vehicle_data1"
}

def fetch_data(tree):
    """Fetch vehicle records from the database and display them in Tkinter Treeview."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicle_records")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        tree.delete(*tree.get_children())  # Clear existing data
        for row in rows:
            tree.insert("", tk.END, values=row)

    except Exception as e:
        messagebox.showerror("Database Error", f"Error fetching data: {e}")

def show_vehicle_image(image_data):
    """Display vehicle image in a popup window."""
    if image_data:
        try:
            # Convert binary data to image
            image = Image.open(io.BytesIO(image_data))
            # Resize image while maintaining aspect ratio
            image.thumbnail((400, 300))
            
            # Create popup window
            popup = tk.Toplevel()
            popup.title("Vehicle Image")
            popup.geometry("450x400")  # Fixed size for better appearance
            
            # Add vehicle image
            photo = ImageTk.PhotoImage(image)
            image_label = ttk.Label(popup, image=photo)
            image_label.image = photo  # Keep a reference!
            image_label.pack(padx=10, pady=10)
            
            # Add close button with better styling
            close_btn = ttk.Button(
                popup, 
                text="Close", 
                command=popup.destroy,
                style="Accent.TButton"
            )
            close_btn.pack(pady=10)
            
            # Center the popup on screen
            popup.update_idletasks()
            width = popup.winfo_width()
            height = popup.winfo_height()
            x = (popup.winfo_screenwidth() // 2) - (width // 2)
            y = (popup.winfo_screenheight() // 2) - (height // 2)
            popup.geometry(f'+{x}+{y}')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display image: {e}")

def create_quick_search(parent_frame, tree):
    """Create an enhanced multi-search interface with better UI."""
    # Create main search frame with better styling
    search_frame = ttk.LabelFrame(parent_frame, text="Advanced Search", padding="10")
    search_frame.pack(fill=tk.X, pady=10, padx=5)

    # Create two rows of search controls
    row1 = ttk.Frame(search_frame)
    row1.pack(fill=tk.X, pady=5)
    
    row2 = ttk.Frame(search_frame)
    row2.pack(fill=tk.X, pady=5)

    # Add view image button (initially hidden)
    view_image_btn = ttk.Button(
        row1,
        text="View Vehicle Image",
        command=lambda: None,  # Will be updated during search
        style="Accent.TButton",
        width=15
    )

    # Search type dropdown with more options
    search_type = ttk.Combobox(
        row1,
        values=["Number Plate", "Date", "Time", "Model", "Color", "Company"],
        width=15,
        state="readonly"
    )
    search_type.set("Number Plate")
    search_type.pack(side=tk.LEFT, padx=5)

    # Search entry
    search_var = tk.StringVar()
    search_entry = ttk.Entry(row1, textvariable=search_var, width=30)
    search_entry.insert(0, "Enter search term...")
    search_entry.pack(side=tk.LEFT, padx=5)

    # Add date range widgets (initially hidden)
    date_frame = ttk.Frame(row2)
    from_date = ttk.Entry(date_frame, width=15)
    to_date = ttk.Entry(date_frame, width=15)
    
    ttk.Label(date_frame, text="From:").pack(side=tk.LEFT, padx=2)
    from_date.pack(side=tk.LEFT, padx=2)
    ttk.Label(date_frame, text="To:").pack(side=tk.LEFT, padx=2)
    to_date.pack(side=tk.LEFT, padx=2)

    def on_search_type_change(*args):
        if search_type.get() == "Date":
            date_frame.pack(fill=tk.X, pady=5)
            search_entry.pack_forget()
        else:
            date_frame.pack_forget()
            search_entry.pack(side=tk.LEFT, padx=5)

    search_type.bind('<<ComboboxSelected>>', on_search_type_change)

    def quick_search():
        search_text = search_var.get()
        if (search_text and search_text != "Enter search term...") or search_type.get() == "Date":
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                # Store the last image data for number plate searches
                last_image_data = None
                
                # Enhanced search queries
                if search_type.get() == "Number Plate":
                    query = "SELECT * FROM vehicle_records WHERE UPPER(number_plate) LIKE UPPER(%s)"
                    cursor.execute(query, (f"%{search_text}%",))
                    # Show view image button for number plate searches
                    view_image_btn.pack(side=tk.RIGHT, padx=5)
                else:
                    # Hide view image button for other searches
                    view_image_btn.pack_forget()
                    if search_type.get() == "Date":
                        query = """
                        SELECT * FROM vehicle_records 
                        WHERE DATE(date_time) BETWEEN %s AND %s
                        """
                        cursor.execute(query, (from_date.get(), to_date.get()))
                    elif search_type.get() == "Time":
                        query = "SELECT * FROM vehicle_records WHERE TIME(date_time) LIKE %s"
                        cursor.execute(query, (f"%{search_text}%",))
                    elif search_type.get() == "Color":
                        query = "SELECT * FROM vehicle_records WHERE UPPER(vehicle_color) LIKE UPPER(%s)"
                        cursor.execute(query, (f"%{search_text}%",))
                    elif search_type.get() == "Company":
                        query = "SELECT * FROM vehicle_records WHERE UPPER(vehicle_company) LIKE UPPER(%s)"
                        cursor.execute(query, (f"%{search_text}%",))
                    else:  # Model search
                        query = "SELECT * FROM vehicle_records WHERE UPPER(vehicle_model) LIKE UPPER(%s)"
                        cursor.execute(query, (f"%{search_text}%",))
                
                rows = cursor.fetchall()
                tree.delete(*tree.get_children())
                
                for row in rows:
                    row_list = list(row)
                    if row[3]:  # date_time column
                        row_list[3] = row[3].strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Store image data from last number plate match
                    if search_type.get() == "Number Plate" and row[-1]:
                        last_image_data = row[-1]
                    
                    tree.insert("", tk.END, values=row_list[:-1])  # Exclude image data from display

                # Update view image button command
                if search_type.get() == "Number Plate" and last_image_data:
                    view_image_btn.configure(
                        command=lambda: show_vehicle_image(last_image_data)
                    )

                cursor.close()
                conn.close()

            except Exception as e:
                messagebox.showerror("Search Error", str(e))
                view_image_btn.pack_forget()

    # Button styles
    style = ttk.Style()
    style.configure("Search.TButton", foreground="white", background="#0078D7", padding=5)
    style.configure("Clear.TButton", foreground="white", background="#666666", padding=5)

    # Search buttons with better styling
    button_frame = ttk.Frame(row1)
    button_frame.pack(side=tk.LEFT, padx=5)

    ttk.Button(
        button_frame,
        text="Search",
        command=quick_search,
        style="Search.TButton",
        width=12
    ).pack(side=tk.LEFT, padx=2)

    ttk.Button(
        button_frame,
        text="Clear",
        command=lambda: [
            search_var.set(""), 
            from_date.delete(0, tk.END),
            to_date.delete(0, tk.END),
            view_image_btn.pack_forget(),
            fetch_data(tree)
        ],
        style="Clear.TButton",
        width=12
    ).pack(side=tk.LEFT, padx=2)

    def on_entry_click(event):
        if search_var.get() == "Enter search term...":
            search_entry.delete(0, tk.END)

    def on_focus_out(event):
        if search_var.get() == '':
            search_entry.insert(0, "Enter search term...")

    search_entry.bind('<FocusIn>', on_entry_click)
    search_entry.bind('<FocusOut>', on_focus_out)

    return search_entry, tree

def create_database_table_ui(parent_frame):
    """Creates a UI frame with a treeview and search controls."""
    display_frame = ttk.LabelFrame(parent_frame, text="Vehicle Records", padding=10)
    display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Add quick search at the top
    columns = ("ID", "Track ID", "Speed", "Date Time", "Model", "Color", "Company", "Number Plate")
    tree = ttk.Treeview(display_frame, columns=columns, show='headings')

    def on_tree_select(event):
        selected = tree.selection()
        if selected:
            item = tree.item(selected[0])
            values = item['values']
            if values and len(values) > 7:  # Make sure we have image data
                try:
                    conn = mysql.connector.connect(**DB_CONFIG)
                    cursor = conn.cursor()
                    cursor.execute("SELECT image_data FROM vehicle_records WHERE id = %s", (values[0],))
                    result = cursor.fetchone()
                    cursor.close()
                    conn.close()

                    if result and result[0]:
                        show_vehicle_image(result[0])
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to fetch image: {e}")

    # Add quick search
    search_entry, tree = create_quick_search(display_frame, tree)

    # Configure tree columns
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)

    # Add scrollbar
    scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Pack the scrollbar and tree
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(fill=tk.BOTH, expand=True)

    # Bind double-click to show image
    tree.bind('<Double-1>', on_tree_select)

    return tree

