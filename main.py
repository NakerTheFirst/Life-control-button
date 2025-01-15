import os
import sys

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QColor, QPalette, QKeySequence, QShortcut, QIcon
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QComboBox,
                             QDoubleSpinBox, QHBoxLayout, QLabel, QMainWindow,
                             QPushButton, QRadioButton, QTimeEdit, QVBoxLayout,
                             QWidget)


class LifeControlButtonApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set application icon
        self.setWindowIcon(QIcon('icon.png'))

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
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#222e4d"))  # Dark navy for highlighted text
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#abb2bf"))
        self.setPalette(palette)

        # Regular Windows title bar
        self.setWindowFlags(Qt.WindowType.Window)

    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()
        root_layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 40)  # Adjust margins to move content up
        root_layout.setContentsMargins(0, 0, 0, 0)  # Adjust margins to move content up

        # Title
        title_label = QLabel("Liberation, not limitation")
        title_label.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 32px; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Shutdown mode selection
        mode_layout = QVBoxLayout()
        self.radio_at_time = QRadioButton("Turn PC off at a specific time")
        self.radio_at_time.setStyleSheet(
            "QRadioButton {color: #abb2bf; font-family: ubuntu; font-size: 14px; spacing: 10px;} "
            "QRadioButton::indicator { width: 14px; height: 14px; border: 1px solid #abb2bf; background: #21252b; } "
            "QRadioButton::indicator:checked { background-color: #abb2bf; } "
            "QRadioButton:hover {color: #dcdfe4;}"
            "QRadioButton:focus {outline: none;}"
        )
        self.radio_after_time = QRadioButton("Turn PC off after a specific duration")
        self.radio_after_time.setStyleSheet(
            "QRadioButton {color: #abb2bf; font-family: ubuntu; font-size: 14px; spacing: 10px;} "
            "QRadioButton::indicator { width: 14px; height: 14px; border: 1px solid #abb2bf; background: #21252b; } "
            "QRadioButton::indicator:checked { background-color: #abb2bf; } "
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
        set_time_label.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        self.time_edit = QTimeEdit()
        self.time_edit.setStyleSheet(
            "position: absolute; margin: 0; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; border-radius: 0; text-align: center; selection-background-color: #6d798f;"
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
        after_time_label.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 14px; ")

        self.time_value_spinbox = QDoubleSpinBox()
        self.time_value_spinbox.setStyleSheet(
            "background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; border-radius: 0; selection-background-color: #6d798f;"
        )
        self.time_value_spinbox.setRange(0.1, 1440)  # Max 24 hours, minimum 0.1
        self.time_value_spinbox.setDecimals(2)
        self.time_value_spinbox.setValue(1)  # Default value 1
        self.time_value_spinbox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        self.time_unit_combobox = QComboBox()
        self.time_unit_combobox.setFrame(False)
        self.time_unit_combobox.setStyleSheet(
            "QWidget {width: 15px; height: 21px; border: none; background-color: #21252b;} "
            "QComboBox {width: 15px; height: 21px; background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; border: none; selection-background-color: #6d798f} "
            "QComboBox::drop-down {border: none;} "
            "QComboBox:hover {color: #dcdfe4;}"
        )
        self.time_unit_combobox.addItems(["Minutes", "Hours"])
        self.time_unit_combobox.setCurrentText("Hours")  # Default to Hours

        after_time_layout.addWidget(after_time_label)
        after_time_layout.addWidget(self.time_value_spinbox)
        after_time_layout.addWidget(self.time_unit_combobox)

        self.after_time_widget = QWidget()
        self.after_time_widget.setLayout(after_time_layout)
        layout.addWidget(self.after_time_widget)

        # Initially hide "after time" option
        self.after_time_widget.hide()

        # "Get Life Control" Button
        self.control_button = QPushButton("Get Life Control")  # Make it an instance variable
        self.control_button.setStyleSheet(
            "QPushButton {background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 20px; padding: 10px; border-radius: 0;}"
            "QPushButton:hover {background-color: #3b4252; color: #ffffff;}"
            "QPushButton:focus {outline: none;}"
        )
        self.control_button.clicked.connect(self.execute_shutdown)
        self.control_button.setDefault(True)  # Make it the default button
        layout.addWidget(self.control_button)
        
        root_layout.addLayout(layout)

        central_widget.setLayout(root_layout)
        self.setCentralWidget(central_widget)

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
        time_unit = self.time_unit_combobox.currentText()
        seconds = int(time_value * 3600) if time_unit == "Hours" else int(time_value * 60)
        os.system(f"powershell.exe shutdown /s /t {seconds}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app.setWindowIcon(QIcon('icon.png'))
    
    main_window = LifeControlButtonApp()
    main_window.resize(500, 400)
    main_window.show()
    sys.exit(app.exec())