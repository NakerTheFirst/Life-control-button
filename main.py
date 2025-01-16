import os
import sys

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QPalette, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


class LifeControlButtonApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set application icon
        self.setWindowIcon(QIcon('icon.png'))
        self.setFixedSize(500, 400) 

        # Set the theme based on Atom One Dark colours
        self.set_theme()

        # Initialize main UI
        self.init_ui()
        
        # Add Enter key shortcut
        self.shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.shortcut.activated.connect(self.execute_shutdown)
        
        # Add Enter key shortcut for numpad Enter as well
        self.shortcut_numpad = QShortcut(QKeySequence(Qt.Key.Key_Enter), self)
        self.shortcut_numpad.activated.connect(self.execute_shutdown)

    def set_theme(self):
        self.setWindowTitle("Life Control Button")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#282c34"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#abb2bf"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#21252b"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#282c34"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#abb2bf"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#abb2bf"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#abb2bf"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#222e4d"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#abb2bf"))
        self.setPalette(palette)

        # Regular Windows title bar
        self.setWindowFlags(Qt.WindowType.Window)

    def init_ui(self):
        self.resize(500, 400) 
        
        
        
        self.center()
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  
        layout.setSpacing(0)

        # Title
        title_label = QLabel("Liberation, not limitation")
        title_label.setStyleSheet("padding: 0; color: #abb2bf; font-family: ubuntu; font-size: 32px; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Shutdown mode selection
        mode_layout = QVBoxLayout()
        self.radio_at_time = QRadioButton("Turn PC off at a specific time")
        self.radio_at_time.setStyleSheet(
            "QRadioButton {padding: 0; margin: 5px 0px 5px 112px; color: #abb2bf; font-family: ubuntu; font-size: 14px; spacing: 10px;} "
            "QRadioButton::indicator {width: 14px; height: 14px; border: 1px solid #abb2bf; background: #21252b; } "
            "QRadioButton::indicator:checked { background-color: #abb2bf; } "
            "QRadioButton:hover {color: #dcdfe4;}"
            "QRadioButton:focus {outline: none;}"
        )
        self.radio_after_time = QRadioButton("Turn PC off after a specific duration")
        self.radio_after_time.setStyleSheet(
            "QRadioButton { padding: 0; margin: 5px 0px 5px 112px; color: #abb2bf; font-family: ubuntu; font-size: 14px; spacing: 10px;} "
            "QRadioButton::indicator {padding: 0; width: 14px; height: 14px; border: 1px solid #abb2bf; background: #21252b; } "
            "QRadioButton::indicator:checked {padding: 0; background-color: #abb2bf; } "
            "QRadioButton:hover {color: #dcdfe4;}"
            "QRadioButton:focus {outline: none;}"
        )
        self.radio_at_time.setChecked(True)

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_at_time)
        self.mode_group.addButton(self.radio_after_time)

        self.radio_at_time.toggled.connect(self.update_input_visibility)

        mode_layout.addWidget(self.radio_at_time)
        mode_layout.addWidget(self.radio_after_time)
        layout.addLayout(mode_layout)

        # Set Time option
        set_time_layout = QHBoxLayout()
        set_time_label = QLabel("Turn PC off at:")
        set_time_label.setStyleSheet("margin: 0px 0px 0px 100px; color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        
        self.time_edit = QTimeEdit()
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center text
        self.time_edit.setStyleSheet(
            "border: none; margin: 0px 157px 0 4px; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; selection-background-color: #6d798f;"
        )
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        current_time = QTime.currentTime()
        hours = (current_time.hour() + 2) % 24  # Add 2 hours and wrap around at 24
        self.time_edit.setTime(QTime(hours, 0))
        set_time_layout.addWidget(set_time_label)
        set_time_layout.addWidget(self.time_edit)

        self.set_time_widget = QWidget()
        self.set_time_widget.setLayout(set_time_layout)
        layout.addWidget(self.set_time_widget)

        # Turn off after n time option
        after_time_layout = QHBoxLayout()
        after_time_label = QLabel("Turn PC off after:")
        after_time_label.setStyleSheet("margin: 0 0 0 100px; color: #abb2bf; font-family: ubuntu; font-size: 14px;")

        self.time_value_spinbox = QDoubleSpinBox()
        self.time_value_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center text
        self.time_value_spinbox.setStyleSheet(
            "border: none; margin: 0 25px 0 25px; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; selection-background-color: #6d798f;"
        )
        self.time_value_spinbox.setRange(0.1, 24)  # Max 24 hours, minimum 0.1
        self.time_value_spinbox.setDecimals(2)
        self.time_value_spinbox.setValue(1)  # Default value 1
        self.time_value_spinbox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        self.time_unit_label = QLabel("hours")

        after_time_layout.addWidget(after_time_label)
        after_time_layout.addWidget(self.time_value_spinbox)
        after_time_layout.addWidget(self.time_unit_label)

        self.after_time_widget = QWidget()
        self.after_time_widget.setLayout(after_time_layout)
        layout.addWidget(self.after_time_widget)

        # Initially hide "after time" option
        self.after_time_widget.hide()

        # "Get Life Control" Button
        self.control_button = QPushButton("Get Life Control")  # Make it an instance variable
        self.control_button.setStyleSheet(
            "QPushButton {margin: auto; width: 100px; height: 30; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 20px; padding: 10px; border: none;}"
            "QPushButton:hover {background-color: #3b4252; color: #ffffff;}"
            "QPushButton:focus {outline: none;}"
        )
        self.control_button.clicked.connect(self.execute_shutdown)
        self.control_button.setDefault(True)  # Make it the default button
        layout.addWidget(self.control_button)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        self.show()

    def center(self):
        # Get the frame/window geometry
        window_frame = self.frameGeometry()
    
        # Get the primary screen's center point
        primary_screen = QApplication.primaryScreen()
        screen_center = primary_screen.availableGeometry().center()
    
        # Move the window's center point to the screen's center point
        window_frame.moveCenter(screen_center)
    
        # Move the window to the top-left point of the frame
        self.move(window_frame.topLeft())

    def update_input_visibility(self):
        if self.radio_at_time.isChecked():
            self.set_time_widget.show()
            self.after_time_widget.hide()
        else:
            self.set_time_widget.hide()
            self.after_time_widget.show()

    def execute_shutdown(self):
        if self.radio_at_time.isChecked():
            self.set_shutdown_time()
        elif self.radio_after_time.isChecked():
            self.set_shutdown_after()

    def set_shutdown_time(self):
        target_time = self.time_edit.time()
        now = QTime.currentTime()
        seconds_until_shutdown = now.secsTo(target_time)

        if seconds_until_shutdown <= 0:
            seconds_until_shutdown += 86400  # Adjust for next day

        os.system(f"powershell.exe shutdown /s /t {seconds_until_shutdown}")

    def set_shutdown_after(self):
        time_value = self.time_value_spinbox.value()
        seconds = int(time_value * 3600)
        os.system(f"powershell.exe shutdown /s /t {seconds}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app.setWindowIcon(QIcon('icon.png'))
    main_window = LifeControlButtonApp()
    sys.exit(app.exec())
