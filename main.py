import os
import sys
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk


class LifeControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Life Control Button")
        self.root.geometry("400x500")
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("Big.TButton", padding=20, font=("Arial", 12, "bold"))
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Shutdown options
        self.shutdown_type = tk.StringVar(value="timer")
        
        # Timer option
        timer_frame = ttk.LabelFrame(main_frame, text="Shutdown Timer", padding="10")
        timer_frame.pack(fill=tk.X, pady=10)
        
        ttk.Radiobutton(timer_frame, text="Shutdown after:", 
                       variable=self.shutdown_type, value="timer").pack(anchor=tk.W)
        
        timer_input_frame = ttk.Frame(timer_frame)
        timer_input_frame.pack(fill=tk.X, pady=5)
        
        self.hours = ttk.Spinbox(timer_input_frame, from_=0, to=23, width=5)
        self.hours.pack(side=tk.LEFT, padx=5)
        ttk.Label(timer_input_frame, text="hours").pack(side=tk.LEFT, padx=2)
        
        self.minutes = ttk.Spinbox(timer_input_frame, from_=0, to=59, width=5)
        self.minutes.pack(side=tk.LEFT, padx=5)
        ttk.Label(timer_input_frame, text="minutes").pack(side=tk.LEFT, padx=2)
        
        # Specific time option
        time_frame = ttk.LabelFrame(main_frame, text="Shutdown at Time", padding="10")
        time_frame.pack(fill=tk.X, pady=10)
        
        ttk.Radiobutton(time_frame, text="Shutdown at:", 
                       variable=self.shutdown_type, value="specific_time").pack(anchor=tk.W)
        
        time_input_frame = ttk.Frame(time_frame)
        time_input_frame.pack(fill=tk.X, pady=5)
        
        self.hour = ttk.Spinbox(time_input_frame, from_=0, to=23, width=5)
        self.hour.pack(side=tk.LEFT, padx=5)
        ttk.Label(time_input_frame, text=":").pack(side=tk.LEFT)
        
        self.minute = ttk.Spinbox(time_input_frame, from_=0, to=59, width=5)
        self.minute.pack(side=tk.LEFT, padx=5)
        
        # Life Control Button
        self.control_button = ttk.Button(main_frame, text="GET LIFE CONTROL", 
                                       style="Big.TButton", command=self.initiate_shutdown)
        self.control_button.pack(pady=30)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack(pady=10)
        
    def initiate_shutdown(self):
        try:
            if self.shutdown_type.get() == "timer":
                hours = int(self.hours.get())
                minutes = int(self.minutes.get())
                
                if hours == 0 and minutes == 0:
                    self.status_label.config(text="Please set a valid time")
                    return
                    
                seconds = (hours * 3600) + (minutes * 60)
                
            else:  # specific_time
                target_hour = int(self.hour.get())
                target_minute = int(self.minute.get())
                
                now = datetime.now()
                target_time = now.replace(hour=target_hour, minute=target_minute, second=0)
                
                if target_time <= now:
                    target_time += timedelta(days=1)
                
                seconds = int((target_time - now).total_seconds())
            
            # Execute shutdown command
            if sys.platform == "win32":
                os.system(f"shutdown /s /t {seconds}")
                status = f"PC will shutdown in {seconds//3600} hours and {(seconds%3600)//60} minutes"
            else:
                os.system(f"shutdown -h +{seconds//60}")
                status = f"PC will shutdown in {seconds//3600} hours and {(seconds%3600)//60} minutes"
            
            self.status_label.config(text=status)
            
        except ValueError:
            self.status_label.config(text="Please enter valid numbers")

def main():
    root = tk.Tk()
    app = LifeControlApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()