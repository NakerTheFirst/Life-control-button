import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTimeEdit, QDoubleSpinBox, QComboBox, QRadioButton, QButtonGroup
from PyQt6.QtCore import QTime, Qt
from PyQt6.QtGui import QPalette, QColor
import os

class LifeControlButtonApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set the theme based on Atom One Dark colors
        self.set_theme()

        # Initialize main UI
        self.init_ui()

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
        self.setPalette(palette)

    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 70, 40, 40)  # Move content up by reducing top margin

        # Title
        title_label = QLabel("Liberation, not limitation")
        title_label.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 32px; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Shutdown mode selection
        mode_layout = QVBoxLayout()
        self.radio_at_time = QRadioButton("Turn PC off at a specific time")
        self.radio_at_time.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        self.radio_after_time = QRadioButton("Turn PC off after a specific duration")
        self.radio_after_time.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 14px;")
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
        self.time_edit.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; border-radius: 0;")
        self.time_edit.setDisplayFormat("HH:mm")
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
        after_time_label.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 14px;")

        self.time_value_spinbox = QDoubleSpinBox()
        self.time_value_spinbox.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; border-radius: 0;")
        self.time_value_spinbox.setRange(0.1, 1440)  # Max 24 hours, minimum 0.1
        self.time_value_spinbox.setDecimals(2)
        self.time_value_spinbox.setValue(1)  # Default value 1
        self.time_value_spinbox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        self.time_unit_combobox = QComboBox()
        self.time_unit_combobox.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px; border-radius: 0;")
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
        control_button = QPushButton("Get Life Control")
        control_button.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 20px; padding: 10px; border-radius: 0;")
        control_button.clicked.connect(self.execute_shutdown)
        layout.addWidget(control_button)

        central_widget.setLayout(layout)
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
    main_window = LifeControlButtonApp()
    main_window.resize(500, 400)
    main_window.show()
    sys.exit(app.exec())
