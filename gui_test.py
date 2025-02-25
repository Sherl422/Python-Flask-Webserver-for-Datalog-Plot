import os
import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import tkinter
from tkinter import *
from tkinter import filedialog
import base64
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime
import matplotlib.dates as mdates
from waitress import serve
import threading
import logging
import webbrowser
import socket  # Import socket module to get the local machine's IP address

def open_link(url):
    try:
        webbrowser.open(url, new=1)
    except Exception as e:
        print(f"Failed to open link: {e}")

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_file.csv')
        file.save(file_path)
        return render_template('uploaded_successfully.html', file_uploaded=True, plots=None)
    return 'Invalid file format, only CSV files are allowed.', 400

@app.route('/dropdown')
def dropdown():
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_file.csv')
    data = pd.read_csv(file_path)
    data['Time'] = pd.to_datetime(data['Time'], format='mixed', dayfirst=True, errors="coerce")
    data = data.dropna(subset=['Time'])
    data.reset_index(drop=True, inplace=True)
    print("The date object file:\n", data['Time'])
    data['Time'] = data['Time'].dt.strftime("%Y-%m-%dT%H:%M")
    mint = data['Time'].min()
    maxt = data['Time'].max()
    return render_template('dropdown.html', mint=mint, maxt=maxt)

@app.route('/plot', methods=['POST'])
def plot():
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_file.csv')
    if not os.path.exists(file_path):
        return 'No file uploaded yet', 400
    plots, trimmed_data_html = generate_plots(file_path)
    return render_template('generate_plots.html', file_uploaded=True, plots=plots, table=trimmed_data_html)

def generate_plots(file_path):
    plots = []
    parameter1 = request.form.get('parameters1')
    parameter2 = request.form.get('parameters2')
    parameter3 = request.form.get('parameters3')
    from_time_str = request.form.get('fromtime')
    to_time_str = request.form.get('totime')
    if not (parameter1 and parameter2 and parameter3):
        return 'Please select all parameters and provide valid time range.', 400

    try:
        from_time = datetime.strptime(from_time_str, "%Y-%m-%dT%H:%M")
        to_time = datetime.strptime(to_time_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        return 'Invalid date/time format. Please use DD-MM-YY H:MM', 400    

    attributes = [parameter1, parameter2, parameter3]
    colors = ['red', 'blue', 'green']

    data = pd.read_csv(file_path)
    data['Time'] = pd.to_datetime(data['Time'], dayfirst=True, errors="coerce")
    data = data.dropna(subset=['Time'])
    data.reset_index(drop=True, inplace=True)
    filtered_data = data[(data['Time'] >= from_time) & (data['Time'] <= to_time)]
    if filtered_data.empty:
        return "No data available for the selected time range.", 400

    filtered_data = filtered_data[['Time'] + attributes]
    
    fig, ax = plt.subplots(figsize=(16, 4))
    for attribute, color in zip(attributes, colors):
        if attribute in filtered_data.columns:
            ax.plot(filtered_data['Time'], filtered_data[attribute], label=attribute, color=color)

    ax.set_xlim([filtered_data['Time'].min(), filtered_data['Time'].max()])
    
    num_xticks = 10  
    xticks = pd.date_range(start=filtered_data['Time'].min(), end=filtered_data['Time'].max(), periods=num_xticks)
    ax.set_xticks(xticks)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%y %H:%M")) 
    plt.title("Line Graph")
    plt.legend()
    plt.grid(True)
    img = BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    plots.append(base64.b64encode(img.getvalue()).decode('utf-8'))

    return plots, filtered_data.to_html(classes='dataframe', index=False)

def close():
    window.destroy()
    sys.exit()

def get_local_ip():
    """
    This function gets the local IP address of the machine running the application.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # Try to connect to a remote server to determine the local IP address
        s.connect(('10.254.254.254', 1))  # No need to actually connect, just to determine the local IP
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'  # Fallback to localhost if the network is unreachable
    finally:
        s.close()
    return local_ip

def appdebug():
    try:
        logging.debug("Starting Flask server...")
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        local_ip = get_local_ip()  # Get the local IP address dynamically
        print(f"Server running on IP: {local_ip}")
        serve(app, host=local_ip, port=5000)
    except Exception as e:
        logging.error("Failed to start the Flask server: %s", e)

# Main GUI setup
if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=appdebug)
    flask_thread.daemon = True
    flask_thread.start()

    # Tkinter GUI setup
    window = Tk()
    window.title('Graphical Representation of the Data Logs')
    name = Label(window, text="Application is running", font=("Times New Roman", 12))
    name.grid(row=1, column=1, columnspan=3)
    local_ip = get_local_ip()  # Get the local IP dynamically
    link = Button(window, text="Click here to redirect to the server", font=("Times New Roman", 12))
    link.grid(row=2, column=1, columnspan=3, pady=10)
    link.bind("<Button-1>", lambda e: open_link(f"http://{local_ip}:5000"))  # Use the dynamic local IP
    cls = Button(window, text='Close', font=("Times New Roman", 10), command=close)
    cls.grid(row=3, column=2)

    window.mainloop()
