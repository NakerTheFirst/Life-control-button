import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import os
import sys

class LifeControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Life Control Button")
        self.root.geometry("400x500")
        
        # Set dark theme colours
        self.bg_color = "#282c34"
        self.accent_color = "#86bf63"
        self.text_color = "#abb2bf"
        
        # Configure the root window
        self.root.configure(bg=self.bg_color)
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TLabelframe", background=self.bg_color, foreground=self.text_color)
        self.style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.text_color)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        self.style.configure("TRadiobutton", 
                           background=self.bg_color, 
                           foreground=self.text_color,
                           indicatorrelief="flat",
                           indicatorbackground=self.bg_color,
                           indicatorforeground=self.accent_color)
        self.style.configure("Big.TButton", 
                           padding=20, 
                           font=("Arial", 12, "bold"),
                           background=self.accent_color)
        
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
        
        # Custom Entry widgets instead of Spinbox
        vcmd = (self.root.register(self.validate_number), '%P')
        
        self.hours = tk.Entry(timer_input_frame, 
                            width=5, 
                            validate='key', 
                            validatecommand=vcmd,
                            bg=self.bg_color,
                            fg=self.text_color,
                            insertbackground=self.text_color,  # cursor color
                            relief="flat",
                            highlightthickness=1,
                            highlightcolor=self.accent_color,
                            highlightbackground=self.text_color)
        self.hours.pack(side=tk.LEFT, padx=5)
        self.hours.insert(0, "0")
        
        ttk.Label(timer_input_frame, text="hours").pack(side=tk.LEFT, padx=2)
        
        self.minutes = tk.Entry(timer_input_frame, 
                              width=5, 
                              validate='key', 
                              validatecommand=vcmd,
                              bg=self.bg_color,
                              fg=self.text_color,
                              insertbackground=self.text_color,
                              relief="flat",
                              highlightthickness=1,
                              highlightcolor=self.accent_color,
                              highlightbackground=self.text_color)
        self.minutes.pack(side=tk.LEFT, padx=5)
        self.minutes.insert(0, "0")
        
        ttk.Label(timer_input_frame, text="minutes").pack(side=tk.LEFT, padx=2)
        
        # Specific time option
        time_frame = ttk.LabelFrame(main_frame, text="Shutdown at Time", padding="10")
        time_frame.pack(fill=tk.X, pady=10)
        
        ttk.Radiobutton(time_frame, text="Shutdown at:", 
                       variable=self.shutdown_type, value="specific_time").pack(anchor=tk.W)
        
        time_input_frame = ttk.Frame(time_frame)
        time_input_frame.pack(fill=tk.X, pady=5)
        
        self.hour = tk.Entry(time_input_frame, 
                           width=5, 
                           validate='key', 
                           validatecommand=vcmd,
                           bg=self.bg_color,
                           fg=self.text_color,
                           insertbackground=self.text_color,
                           relief="flat",
                           highlightthickness=1,
                           highlightcolor=self.accent_color,
                           highlightbackground=self.text_color)
        self.hour.pack(side=tk.LEFT, padx=5)
        self.hour.insert(0, "0")
        
        ttk.Label(time_input_frame, text=":").pack(side=tk.LEFT)
        
        self.minute = tk.Entry(time_input_frame, 
                             width=5, 
                             validate='key', 
                             validatecommand=vcmd,
                             bg=self.bg_color,
                             fg=self.text_color,
                             insertbackground=self.text_color,
                             relief="flat",
                             highlightthickness=1,
                             highlightcolor=self.accent_color,
                             highlightbackground=self.text_color)
        self.minute.pack(side=tk.LEFT, padx=5)
        self.minute.insert(0, "0")
        
        # Custom styled button
        self.control_button = tk.Button(main_frame, 
                                      text="GET LIFE CONTROL",
                                      font=("Arial", 12, "bold"),
                                      bg=self.accent_color,
                                      fg="#ffffff",
                                      activebackground="#729e57",  # darker shade for hover
                                      activeforeground="#ffffff",
                                      relief="flat",
                                      command=self.initiate_shutdown)
        self.control_button.pack(pady=30, ipadx=20, ipady=10)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack(pady=10)
    
    def validate_number(self, value):
        if value == "":
            return True
        try:
            num = int(value)
            return len(value) <= 2 and num >= 0
        except ValueError:
            return False
        
    def initiate_shutdown(self):
        try:
            if self.shutdown_type.get() == "timer":
                hours = int(self.hours.get() or 0)
                minutes = int(self.minutes.get() or 0)
                
                if hours == 0 and minutes == 0:
                    self.status_label.config(text="Please set a valid time")
                    return
                    
                seconds = (hours * 3600) + (minutes * 60)
                
            else:  # specific_time
                target_hour = int(self.hour.get() or 0)
                target_minute = int(self.minute.get() or 0)
                
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