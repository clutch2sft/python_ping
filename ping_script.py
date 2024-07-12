import os
import threading
import time
import subprocess
from datetime import datetime
from tkinter import Tk, Text, Scrollbar, END, BOTH, RIGHT, Y, Frame, Label, Button
import queue
import signal
import sys

# Directory setup
CONFIG_DIR = 'config'
OUTPUT_DIR = 'output'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'ips.txt')

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Global flag to control the running state of the threads
running = True

# Function to handle SIGINT (Ctrl+C)
def signal_handler(sig, frame):
    global running
    running = False
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Function to read IP addresses from the config file
def read_ips(config_file):
    with open(config_file, 'r') as file:
        return [line.strip() for line in file.readlines()]

# Function to log ping results
def log_ping(ip, log_queue, start_time):
    log_file = os.path.join(OUTPUT_DIR, f'{ip}_{start_time}.log')
    with open(log_file, 'a') as file:
        while running:
            timestamp_sent = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            process = subprocess.Popen(['ping', '-n', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            timestamp_received = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

            if process.returncode == 0:
                stdout = stdout.decode('utf-8')
                # Extract time from ping response
                ms = None
                for line in stdout.split('\n'):
                    if 'time=' in line:
                        ms = line.split('time=')[1].split('ms')[0].strip()
                        break
                    elif 'time<' in line:
                        ms = line.split('time<')[1].split('ms')[0].strip()
                        ms = f'<{ms}'
                        break
                
                if ms is not None:
                    logmessage = f'{timestamp_sent} - {timestamp_received}: Ping to {ip} successful, Time: {ms}ms\n'
                    termmessage = f'Ping {ip} success, {ms}ms\n'
                else:
                    logmessage = f'{timestamp_sent} - {timestamp_received}: Ping to {ip} successful, Time: Unknown\n'
                    termmessage = f'Ping {ip} success Unknown ms\n'
            else:
                logmessage = f'{timestamp_sent} - {timestamp_received}: Ping to {ip} failed\n'
                termmessage = f'Ping {ip} failed\n'

            file.write(logmessage)
            file.flush()  # Ensure the message is written immediately
            log_queue.put((ip, termmessage))
            time.sleep(1)

# Function to create a GUI window for each IP
def create_gui_window(ip, log_queue):
    root = Tk()
    root.title(f'Ping Log: {ip}')
    
    frame = Frame(root)
    frame.pack(side=RIGHT, fill=BOTH, expand=True)
    
    label = Label(frame, text=f'Ping Log: {ip}')
    label.pack()
    
    text = Text(frame)
    scrollbar = Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    
    text.pack(side=RIGHT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)
    
    text.tag_configure('ping', foreground='blue')
    text.tag_configure('error', foreground='red')
    
    def stop():
        global running
        running = False
        root.destroy()
    
    stop_button = Button(frame, text="Stop", command=stop)
    stop_button.pack()
    
    def process_log_queue():
        while running:
            try:
                _, message = log_queue.get_nowait()
                text.insert(END, message, 'ping')
                text.see(END)
            except queue.Empty:
                break
        if running:
            root.after(100, process_log_queue)
    
    root.after(100, process_log_queue)
    root.mainloop()

# Main function to set up threads for each IP
def main():
    ips = read_ips(CONFIG_FILE)
    start_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for ip in ips:
        log_queue = queue.Queue()
        thread = threading.Thread(target=log_ping, args=(ip, log_queue, start_time))
        thread.daemon = True
        thread.start()
        
        gui_thread = threading.Thread(target=create_gui_window, args=(ip, log_queue))
        gui_thread.daemon = True
        gui_thread.start()
    
    # Keep the main thread alive to keep logging running
    while running:
        time.sleep(1)

if __name__ == '__main__':
    main()
