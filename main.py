import ctypes
import os
import re
import subprocess
import sys

from PyQt6.QtCore import QEvent, Qt, QTime
from PyQt6.QtGui import (QColor, QIcon, QKeySequence, QPalette, QShortcut,
                         QValidator)
from PyQt6.QtWidgets import (QAbstractSpinBox, QApplication, QButtonGroup,
                             QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                             QPushButton, QRadioButton, QSpinBox, QTimeEdit,
                             QVBoxLayout, QWidget)

if sys.platform == 'win32':
    # Hide console window
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    SW_HIDE = 0
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, SW_HIDE)


def resource_path(*relative_parts):
    """Resolve a resource path relative to the script or the PyInstaller bundle"""
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *relative_parts)


class DurationSpinBox(QSpinBox):
    """Duration input holding minutes: shows plain minutes under an hour,
    hours and minutes above. Below an hour the arrows step five minutes;
    above it they act on the hour or minute section, picked with left/right.
    Wraps past either end of the range."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.minutes_section_active = False
        self.setWrapping(True)  # Keep stepping enabled at both range ends

    def textFromValue(self, minutes):
        hours, mins = divmod(minutes, 60)
        if hours == 0:
            return f"{mins} min"
        return f"{hours} h {mins} min"

    def valueFromText(self, text):
        numbers = [int(n) for n in re.findall(r'\d+', text)]
        if not numbers:
            return self.value()
        if 'h' in text.replace('min', ''):
            hours = numbers[0]
            mins = numbers[1] if len(numbers) > 1 else 0
            return hours * 60 + mins
        return numbers[0]

    def validate(self, text, pos):
        if re.fullmatch(r'[\dhmin ]*', text):
            return QValidator.State.Acceptable, text, pos
        return QValidator.State.Invalid, text, pos

    def stepBy(self, steps):
        self.interpretText()
        minutes = self.value()
        if minutes >= 60 and not self.minutes_section_active:
            # Hour section: step whole hours
            target = minutes + steps * 60
            if target > self.maximum():
                target = self.minimum()  # Past 24 h wraps to the shortest duration
            elif target < self.minimum():
                target = 55  # Stepping down from the last hour re-enters the minute range
        elif minutes >= 60:
            # Minute section: wrap within the current hour
            hours, mins = divmod(minutes, 60)
            target = hours * 60 + (mins + steps * 5) % 60
        else:
            target = minutes + steps * 5
            if target < self.minimum():
                target = self.maximum()  # Below 5 min wraps to 24 h
        self.setValue(target)
        self.select_active_section()

    def keyPressEvent(self, event):
        # A single left/right press jumps between the hour and minute sections
        if self.value() >= 60 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if event.key() == Qt.Key.Key_Right:
                self.minutes_section_active = True
                self.select_active_section()
                return
            if event.key() == Qt.Key.Key_Left:
                self.minutes_section_active = False
                self.select_active_section()
                return
        super().keyPressEvent(event)

    def select_active_section(self):
        if self.value() < 60:
            self.minutes_section_active = False
        numbers = list(re.finditer(r'\d+', self.text()))
        if not numbers:
            return
        section = numbers[1] if self.minutes_section_active and len(numbers) > 1 else numbers[0]
        self.lineEdit().setSelection(section.start(), section.end() - section.start())


class LifeControlButtonApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set application icon
        self.setWindowIcon(QIcon(resource_path('assets', 'icon.png')))
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

        # Frameless window: no native title bar, closing stays deliberately inconvenient
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)

    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  
        layout.setSpacing(0)

        # Title
        title_label = QLabel("Liberation, not limitation")
        title_label.setStyleSheet("padding: 0; color: #abb2bf; font-family: ubuntu; font-size: 32px; margin: 30px 0 20px 0;")
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
            "QRadioButton:focus {color: #dcdfe4; outline: none;}"
        )
        self.radio_after_time = QRadioButton("Turn PC off after a specific duration")
        self.radio_after_time.setStyleSheet(
            "QRadioButton { padding: 0; margin: 5px 0px 5px 112px; color: #abb2bf; font-family: ubuntu; font-size: 14px; spacing: 10px;} "
            "QRadioButton::indicator {padding: 0; width: 14px; height: 14px; border: 1px solid #abb2bf; background: #21252b; } "
            "QRadioButton::indicator:checked {padding: 0; background-color: #abb2bf; } "
            "QRadioButton:hover {color: #dcdfe4;}"
            "QRadioButton:focus {color: #dcdfe4; outline: none;}"
        )
        self.radio_at_time.setChecked(True)

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_at_time)
        self.mode_group.addButton(self.radio_after_time)

        self.radio_at_time.toggled.connect(self.update_input_visibility)

        mode_layout.addWidget(self.radio_at_time)
        mode_layout.addWidget(self.radio_after_time)
        layout.addLayout(mode_layout)

        # Both input rows share these widths so the boxes line up across modes
        row_label_width = 240
        input_width = 90

        # Set Time option
        set_time_layout = QHBoxLayout()
        set_time_label = QLabel("Turn PC off at:")
        set_time_label.setStyleSheet("margin: 0px 0px 0px 100px; color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        set_time_label.setFixedWidth(row_label_width)

        self.time_edit = QTimeEdit()
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centre the text
        self.time_edit.setStyleSheet(
            "border: none; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; selection-background-color: #6d798f;"
        )
        self.time_edit.setFixedWidth(input_width)
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setWrapping(True)  # 23 wraps to 0, 59 to 0
        self.time_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        current_time = QTime.currentTime()
        hours = (current_time.hour() + 2) % 24  # Add 2 hours and wrap around at 24
        self.time_edit.setTime(QTime(hours, 0))
        set_time_layout.addWidget(set_time_label)
        set_time_layout.addWidget(self.time_edit)
        set_time_layout.addStretch(1)

        self.set_time_widget = QWidget()
        self.set_time_widget.setLayout(set_time_layout)
        layout.addWidget(self.set_time_widget)

        # Turn off after n time option
        after_time_layout = QHBoxLayout()
        after_time_label = QLabel("Turn PC off after:")
        after_time_label.setStyleSheet("margin: 0 0 0 100px; color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        after_time_label.setFixedWidth(row_label_width)

        self.duration_spinbox = DurationSpinBox()
        self.duration_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centre the text
        self.duration_spinbox.setStyleSheet(
            "border: none; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; selection-background-color: #6d798f;"
        )
        self.duration_spinbox.setFixedWidth(input_width)
        self.duration_spinbox.setRange(5, 1440)  # 5 minutes up to 24 hours
        self.duration_spinbox.setValue(60)  # Default one hour
        self.duration_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        after_time_layout.addWidget(after_time_label)
        after_time_layout.addWidget(self.duration_spinbox)
        after_time_layout.addStretch(1)

        self.after_time_widget = QWidget()
        self.after_time_widget.setLayout(after_time_layout)
        layout.addWidget(self.after_time_widget)

        # Initially hide "after time" option
        self.after_time_widget.hide()

        # "Get Life Control" Button
        self.control_button = QPushButton("Get Life Control")  # Make it an instance variable
        self.control_button.setStyleSheet(
            "QPushButton {margin: auto; width: 100px; height: 30px; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 20px; padding: 10px; border: none;}"
            "QPushButton:hover {background-color: #3b4252; color: #ffffff;}"
            "QPushButton:focus {background-color: #333946; color: #ffffff; outline: none;}"
        )
        self.control_button.clicked.connect(self.execute_shutdown)
        self.control_button.setDefault(True)  # Make it the default button
        layout.addWidget(self.control_button)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Keyboard navigation: Tab cycles through the controls, hidden inputs are skipped
        self.setTabOrder(self.radio_at_time, self.radio_after_time)
        self.setTabOrder(self.radio_after_time, self.time_edit)
        self.setTabOrder(self.time_edit, self.duration_spinbox)
        self.setTabOrder(self.duration_spinbox, self.control_button)

        # Start on the hour section so the arrow keys adjust the time straight away
        self.time_edit.setFocus()
        self.time_edit.setSelectedSection(QTimeEdit.Section.HourSection)

        # Make a single left/right press jump between the hour and minute sections
        self.time_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.time_edit and event.type() == QEvent.Type.KeyPress \
                and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if event.key() == Qt.Key.Key_Right:
                self.time_edit.setSelectedSection(QTimeEdit.Section.MinuteSection)
                return True
            if event.key() == Qt.Key.Key_Left:
                self.time_edit.setSelectedSection(QTimeEdit.Section.HourSection)
                return True
        return super().eventFilter(obj, event)

    def update_input_visibility(self):
        if self.radio_at_time.isChecked():
            self.set_time_widget.show()
            self.after_time_widget.hide()
        else:
            self.set_time_widget.hide()
            self.after_time_widget.show()

    def execute_shutdown_command(self, seconds):
        """Schedule a shutdown, return True if successful and show any error otherwise"""
        try:
            result = subprocess.run(['shutdown', '/s', '/t', str(seconds)],
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    capture_output=True,
                                    text=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to schedule shutdown: {str(e)}")
            return False

        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip() or f"shutdown exited with code {result.returncode}"
            QMessageBox.critical(self, "Error", f"Failed to schedule shutdown:\n{details}")
            return False
        return True

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

        if self.execute_shutdown_command(seconds_until_shutdown):
            self.close()

    def set_shutdown_after(self):
        seconds = self.duration_spinbox.value() * 60

        if self.execute_shutdown_command(seconds):
            self.close()

    def center_window_on_primary_monitor(self):
        # Get the primary screen (focused monitor)
        screen = QApplication.primaryScreen()
        if not screen:
            return  # Safety check in case no primary screen is available

        # Get the available geometry of the primary screen
        screen_geometry = screen.availableGeometry()

        # Calculate the center of the screen
        screen_center = screen_geometry.center()

        # Adjust position relative to the window's frame geometry
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(screen_center)

        # Move the window to the calculated position
        self.move(frame_geometry.topLeft())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app.setWindowIcon(QIcon(resource_path('assets', 'icon.png')))

    main_window = LifeControlButtonApp()
    main_window.center_window_on_primary_monitor()

    main_window.show()
    sys.exit(app.exec())
