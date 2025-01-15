import os
import sys

from PyQt6.QtCore import QTime
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QComboBox,
                             QDoubleSpinBox, QHBoxLayout, QLabel, QMainWindow,
                             QPushButton, QRadioButton, QTimeEdit, QVBoxLayout,
                             QWidget)


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

        mode_layout.addWidget(self.radio_at_time)
        mode_layout.addWidget(self.radio_after_time)

        layout.addLayout(mode_layout)

        # Set Time option
        set_time_layout = QVBoxLayout()
        set_time_label = QLabel("Turn PC off at:")
        set_time_label.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        self.time_edit = QTimeEdit()
        self.time_edit.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
        set_time_layout.addWidget(set_time_label)
        set_time_layout.addWidget(self.time_edit)

        layout.addLayout(set_time_layout)

        # Turn off after n time option
        after_time_layout = QVBoxLayout()
        after_time_label = QLabel("Turn PC off after:")
        after_time_label.setStyleSheet("color: #abb2bf; font-family: ubuntu; font-size: 14px;")

        time_choice_layout = QHBoxLayout()
        self.time_value_spinbox = QDoubleSpinBox()
        self.time_value_spinbox.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        self.time_value_spinbox.setRange(0.1, 1440)  # Max 24 hours, minimum 0.1
        self.time_value_spinbox.setDecimals(2)
        self.time_value_spinbox.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
        

        self.time_unit_combobox = QComboBox()
        self.time_unit_combobox.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 14px;")
        self.time_unit_combobox.addItems(["Minutes", "Hours"])

        time_choice_layout.addWidget(self.time_value_spinbox)
        time_choice_layout.addWidget(self.time_unit_combobox)

        after_time_layout.addWidget(after_time_label)
        after_time_layout.addLayout(time_choice_layout)

        layout.addLayout(after_time_layout)

        # "Get Life Control" Button
        control_button = QPushButton("Get Life Control")
        control_button.setStyleSheet("background-color: #21252b; color: #abb2bf; font-family: ubuntu; font-size: 20px; padding: 10px;")
        control_button.clicked.connect(self.execute_shutdown)
        layout.addWidget(control_button)

        layout.addStretch()  # Add space to breathe

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

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
    main_window.resize(450, 550)
    main_window.show()
    sys.exit(app.exec())
