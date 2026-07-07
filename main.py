import ctypes
import os
import re
import subprocess
import sys

from PyQt6.QtCore import QEasingCurve, QEvent, Qt, QTime, QVariantAnimation
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QFontMetrics, QIcon,
                         QKeySequence, QShortcut, QValidator)
from PyQt6.QtWidgets import (QAbstractSpinBox, QApplication, QButtonGroup,
                             QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                             QLabel, QMainWindow, QMessageBox, QPushButton,
                             QRadioButton, QSizePolicy, QSpinBox, QTimeEdit,
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


def load_bundled_fonts():
    """Register the bundled Fira Mono faces so the design renders everywhere"""
    for font_file in ('FiraMono-Regular.ttf', 'FiraMono-Medium.ttf', 'FiraMono-Bold.ttf'):
        QFontDatabase.addApplicationFont(resource_path('assets', 'fonts', font_file))


def fira_mono(pixel_size, weight=QFont.Weight.Normal, letter_spacing=0.0):
    """Build a Fira Mono font; letter spacing given in pixels (QSS cannot do it)"""
    font = QFont('Fira Mono')
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    if letter_spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
    return font


def make_glow(widget, blur, alpha):
    """Red ember glow behind a widget, standing in for CSS text/box shadows"""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setOffset(0, 0)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(251, 54, 64, alpha))
    widget.setGraphicsEffect(effect)
    return effect


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

        self.set_theme()
        self.init_ui()

        # Lock the window to its natural size
        self.adjustSize()
        self.setFixedSize(self.size())

        # Add Enter key shortcut
        self.shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.shortcut.activated.connect(self.execute_shutdown)

        # Add Enter key shortcut for numpad Enter as well
        self.shortcut_numpad = QShortcut(QKeySequence(Qt.Key.Key_Enter), self)
        self.shortcut_numpad.activated.connect(self.execute_shutdown)

    def set_theme(self):
        self.setWindowTitle("Life Control Button")
        # Frameless, translucent window: only the glowing card is visible
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(40, 40, 40, 40)  # Room for the card's glow

        # The card: near-black panel with a pulsing ember ring
        self.card = QFrame()
        self.card.setObjectName('card')
        self.card.setFixedWidth(460)
        self.card.setStyleSheet(
            "#card {background-color: #160A0E; border: 1px solid rgba(251, 54, 64, 45%); border-radius: 6px;}"
        )
        self.card_glow = make_glow(self.card, 40, 31)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(48, 52, 48, 52)
        card_layout.setSpacing(0)

        # ARMED indicator
        armed_layout = QHBoxLayout()
        armed_layout.setContentsMargins(0, 0, 0, 0)
        armed_layout.setSpacing(9)
        armed_dot = QLabel()
        armed_dot.setFixedSize(8, 8)
        armed_dot.setStyleSheet("background-color: #FB3640; border-radius: 4px;")
        make_glow(armed_dot, 10, 255)
        armed_label = QLabel("ARMED")
        armed_label.setFont(fira_mono(11, QFont.Weight.Medium, 3.1))
        armed_label.setStyleSheet("color: #FB3640;")
        armed_layout.addWidget(armed_dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        armed_layout.addWidget(armed_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        armed_layout.addStretch(1)
        card_layout.addLayout(armed_layout)
        card_layout.addSpacing(26)

        # Title
        title_label = QLabel("Liberation, not limitation")
        title_label.setFont(fira_mono(22, QFont.Weight.Medium, -0.3))
        title_label.setStyleSheet("color: #F8FFE5;")
        card_layout.addWidget(title_label)
        card_layout.addSpacing(30)

        # The big glowing display doubles as the input for the current mode
        time_font = fira_mono(64, QFont.Weight.Medium, 2.6)
        self.time_edit = QTimeEdit()
        self.time_edit.setFont(time_font)
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_edit.setStyleSheet(
            "background: transparent; border: none; color: #FB3640;"
            "selection-background-color: rgba(251, 54, 64, 30%); selection-color: #F8FFE5;"
        )
        self.time_edit.setFixedWidth(QFontMetrics(time_font).horizontalAdvance('23:00') + 28)
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setWrapping(True)  # 23 wraps to 0, 59 to 0
        self.time_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        current_time = QTime.currentTime()
        hours = (current_time.hour() + 2) % 24  # Add 2 hours and wrap around at 24
        self.time_edit.setTime(QTime(hours, 0))
        make_glow(self.time_edit, 30, 128)

        duration_font = fira_mono(36, QFont.Weight.Medium, 1.4)
        self.duration_spinbox = DurationSpinBox()
        self.duration_spinbox.setFont(duration_font)
        self.duration_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_spinbox.setStyleSheet(
            "background: transparent; border: none; color: #FB3640;"
            "selection-background-color: rgba(251, 54, 64, 30%); selection-color: #F8FFE5;"
        )
        self.duration_spinbox.setFixedWidth(QFontMetrics(duration_font).horizontalAdvance('23 h 55 min') + 28)
        self.duration_spinbox.setRange(5, 1440)  # 5 minutes up to 24 hours
        self.duration_spinbox.setValue(60)  # Default one hour
        self.duration_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        make_glow(self.duration_spinbox, 22, 128)

        display_container = QWidget()
        display_layout = QHBoxLayout()
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.addStretch(1)
        display_layout.addWidget(self.time_edit, alignment=Qt.AlignmentFlag.AlignVCenter)
        display_layout.addWidget(self.duration_spinbox, alignment=Qt.AlignmentFlag.AlignVCenter)
        display_layout.addStretch(1)
        display_container.setLayout(display_layout)
        display_container.setFixedHeight(
            max(self.time_edit.sizeHint().height(), self.duration_spinbox.sizeHint().height())
        )
        card_layout.addWidget(display_container)
        card_layout.addSpacing(12)

        self.mode_sub_label = QLabel("SHUTDOWN AT")
        self.mode_sub_label.setFont(fira_mono(11, QFont.Weight.Normal, 2.6))
        self.mode_sub_label.setStyleSheet("color: rgba(248, 255, 229, 40%);")
        self.mode_sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.mode_sub_label)
        card_layout.addSpacing(34)

        # Mode selection rows, terminal style
        self.radio_at_time, at_mark, at_text, at_row_glow, at_mark_glow = self.build_mode_row("at a specific time")
        self.radio_after_time, after_mark, after_text, after_row_glow, after_mark_glow = self.build_mode_row("after a duration")
        self.mode_rows = [
            (self.radio_at_time, at_mark, at_text, at_row_glow, at_mark_glow),
            (self.radio_after_time, after_mark, after_text, after_row_glow, after_mark_glow),
        ]
        self.radio_at_time.setChecked(True)

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_at_time)
        self.mode_group.addButton(self.radio_after_time)

        self.radio_at_time.toggled.connect(self.update_input_visibility)

        card_layout.addWidget(self.radio_at_time)
        card_layout.addSpacing(12)
        card_layout.addWidget(self.radio_after_time)
        card_layout.addSpacing(36)

        # "Get Life Control" button, outlined
        self.control_button = QPushButton("GET LIFE CONTROL")
        self.control_button.setFont(fira_mono(14, QFont.Weight.DemiBold, 1.7))
        self.control_button.setStyleSheet(
            "QPushButton {background-color: transparent; color: #FB3640; border: 2px solid #FB3640; border-radius: 5px; padding: 16px;}"
            "QPushButton:hover {background-color: #FB3640; color: #160A0E;}"
            "QPushButton:focus {background-color: rgba(251, 54, 64, 15%); outline: none;}"
            "QPushButton:pressed {background-color: #FB3640; color: #160A0E;}"
        )
        self.control_button.clicked.connect(self.execute_shutdown)
        self.control_button.setDefault(True)
        card_layout.addWidget(self.control_button)

        self.card.setLayout(card_layout)
        outer_layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)
        central_widget.setLayout(outer_layout)
        self.setCentralWidget(central_widget)

        # Pulse the card glow like the design's emberpulse keyframes
        self.pulse_animation = QVariantAnimation(self)
        self.pulse_animation.setStartValue(0.0)
        self.pulse_animation.setKeyValueAt(0.5, 1.0)
        self.pulse_animation.setEndValue(0.0)
        self.pulse_animation.setDuration(4000)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_animation.setLoopCount(-1)
        self.pulse_animation.valueChanged.connect(self.update_card_glow)
        self.pulse_animation.start()

        self.update_input_visibility()

        # Keyboard navigation: Tab cycles through the controls, hidden inputs are skipped
        self.setTabOrder(self.time_edit, self.duration_spinbox)
        self.setTabOrder(self.duration_spinbox, self.radio_at_time)
        self.setTabOrder(self.radio_at_time, self.radio_after_time)
        self.setTabOrder(self.radio_after_time, self.control_button)

        # Start on the hour section so the arrow keys adjust the time straight away
        self.time_edit.setFocus()
        self.time_edit.setSelectedSection(QTimeEdit.Section.HourSection)

        # Make a single left/right press jump between the hour and minute sections
        self.time_edit.installEventFilter(self)

    def build_mode_row(self, label_text):
        """A radio button dressed as a bordered terminal row with a [x] mark"""
        radio = QRadioButton()
        radio.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        radio.setFixedHeight(48)
        radio.setStyleSheet(
            "QRadioButton {border: 1px solid rgba(248, 255, 229, 10%); border-radius: 5px; background-color: transparent;}"
            "QRadioButton:checked {border: 1px solid rgba(251, 54, 64, 45%); background-color: rgba(251, 54, 64, 8%);}"
            "QRadioButton:focus {border: 1px solid rgba(251, 54, 64, 80%); outline: none;}"
            "QRadioButton::indicator {width: 0px; height: 0px; border: none; background: transparent; image: none;}"
        )
        row_glow = make_glow(radio, 22, 33)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(15, 0, 15, 0)
        row_layout.setSpacing(12)
        mark = QLabel("[ ]")
        mark.setFont(fira_mono(15, QFont.Weight.DemiBold))
        mark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mark_glow = make_glow(mark, 12, 128)
        text = QLabel(label_text)
        text.setFont(fira_mono(14))
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row_layout.addWidget(mark)
        row_layout.addWidget(text)
        row_layout.addStretch(1)
        radio.setLayout(row_layout)
        return radio, mark, text, row_glow, mark_glow

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
        at_time = self.radio_at_time.isChecked()
        self.time_edit.setVisible(at_time)
        self.duration_spinbox.setVisible(not at_time)
        self.mode_sub_label.setText("SHUTDOWN AT" if at_time else "SHUTDOWN IN")
        self.update_mode_visuals()

    def update_mode_visuals(self):
        for radio, mark, text, row_glow, mark_glow in self.mode_rows:
            checked = radio.isChecked()
            mark.setText("[x]" if checked else "[ ]")
            mark.setStyleSheet("color: #FB3640;" if checked else "color: rgba(248, 255, 229, 35%);")
            text.setStyleSheet("color: #F8FFE5;" if checked else "color: rgba(248, 255, 229, 45%);")
            row_glow.setEnabled(checked)
            mark_glow.setEnabled(checked)

    def update_card_glow(self, phase):
        self.card_glow.setBlurRadius(40 + phase * 24)
        self.card_glow.setColor(QColor(251, 54, 64, int(31 + phase * 25)))

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

    load_bundled_fonts()

    main_window = LifeControlButtonApp()
    main_window.center_window_on_primary_monitor()

    main_window.show()
    sys.exit(app.exec())
