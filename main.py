import ctypes
import os
import re
import subprocess
import sys
import time
import winreg

from PyQt6.QtCore import (QEasingCurve, QEvent, QPoint, QPointF, QRectF, Qt,
                          QTime, QTimer, QVariantAnimation, pyqtSignal)
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QFontMetrics, QIcon,
                         QPainter, QPainterPath, QPixmap, QValidator)
from PyQt6.QtWidgets import (QAbstractSpinBox, QApplication, QButtonGroup,
                             QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                             QLabel, QMainWindow, QMessageBox,
                             QPushButton, QRadioButton, QSizePolicy, QSpinBox,
                             QTimeEdit, QVBoxLayout, QWidget)

if sys.platform == 'win32':
    # Hide console window
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    SW_HIDE = 0
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, SW_HIDE)

# Glow states as (blur radius, alpha): resting, selected section (always on),
# focused section, keypress flare
TIME_GLOW_BASE, TIME_GLOW_SELECTED, TIME_GLOW_HOT, TIME_GLOW_FLARE = \
    (30, 137), (35, 170), (46, 255), (90, 255)
DURATION_GLOW_BASE, DURATION_GLOW_SELECTED, DURATION_GLOW_HOT, DURATION_GLOW_FLARE = \
    (22, 137), (26, 190), (30, 255), (56, 255)
BUTTON_GLOW_BASE, BUTTON_GLOW_FLASH, BUTTON_GLOW_HELD = (18, 70), (90, 255), (40, 200)
CARD_GLOW_FLASH, CARD_GLOW_HELD = (70, 255), (55, 220)

# The card's idle pulse animates glow intensity only, never blurRadius. The
# card's drop shadow composites the whole card through a pixmap padded by the
# blur radius, and at fractional display scales (125%/150%/...) an animated
# radius re-rounds that padding to device pixels differently frame to frame,
# visibly jiggling the entire card by a pixel or two (Qt 6.10, Win11 at 150%)
CARD_PULSE_BLUR = 52
CARD_PULSE_ALPHA_MIN, CARD_PULSE_ALPHA_MAX = 26, 62

# Text colour heats up with the glow tier — brighter text reads better than
# any halo, especially on the smaller duration digits
GLOW_TEXT_BASE = "#FB3640"
GLOW_TEXT_SELECTED = "#FC575E"
GLOW_TEXT_HOT = "#FF7B81"
GLOW_TEXT_FLARE = "#FFB9BC"
FOCUS_TRANSITION_MS = 800
FLARE_TRANSITION_MS = 80
SECTION_FADE_MS = 100  # The just-left section lets go of its glow almost instantly
EXIT_DELAY_MS = 2250  # Time to soak in the button's flash before the app closes

# Dotted scanline texture: dot grid pitch (px), dot size, opacity, drift speed (ms per pitch)
SCANLINE_PITCH = 2
SCANLINE_DOT_SIZE = 1
SCANLINE_DOT_ALPHA = 80
SCANLINE_DRIFT_MS = 700

# Faint press-feedback flicker, fired the instant the button is hit — quicker
# and dimmer than the success surge so it reads as an acknowledgement, not a payoff
BLIP_DOT_ALPHA = 100
BLIP_DURATION_MS = 180

BUTTON_STYLE_NORMAL = (
    "QPushButton {background-color: transparent; color: #FB3640; border: 2px solid #FB3640; border-radius: 5px; padding: 16px;}"
    "QPushButton:hover {background-color: #FB3640; color: #160A0E;}"
    "QPushButton:focus {background-color: rgba(251, 54, 64, 15%); outline: none;}"
    "QPushButton:pressed {background-color: rgba(251, 54, 64, 35%); color: #FB3640;}"
)
# Pure display while a shutdown is already pending: the ring dims to the card's
# ring alpha so the button reads as information, not as something to press
BUTTON_STYLE_COUNTDOWN = (
    "QPushButton:disabled {background-color: transparent; color: #FB3640;"
    " border: 2px solid rgba(251, 54, 64, 45%); border-radius: 5px; padding: 16px;}"
)


def resource_path(*relative_parts):
    """Resolve a resource path relative to the script or the PyInstaller bundle"""
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *relative_parts)


def schedule_state_path():
    """File remembering when the scheduled shutdown will fire. Windows offers no
    way to query a pending `shutdown /s /t`, so the app keeps its own note"""
    base_dir = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    return os.path.join(base_dir, 'LifeControlButton', 'scheduled_shutdown.txt')


def save_scheduled_epoch(epoch):
    """Best effort only: a failed write must never get in the way of the shutdown"""
    try:
        os.makedirs(os.path.dirname(schedule_state_path()), exist_ok=True)
        with open(schedule_state_path(), 'w', encoding='ascii') as state_file:
            state_file.write(str(int(epoch)))
    except OSError:
        pass


def clear_scheduled_epoch():
    try:
        os.remove(schedule_state_path())
    except OSError:
        pass


def load_pending_epoch():
    """The remembered shutdown moment, if it is still ahead of us; stale or
    unreadable state is cleared and reported as no pending shutdown"""
    try:
        with open(schedule_state_path(), encoding='ascii') as state_file:
            epoch = int(state_file.read().strip())
    except (OSError, ValueError):
        return None
    if epoch <= time.time():
        clear_scheduled_epoch()
        return None
    return epoch


STARTUP_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
STARTUP_VALUE_NAME = 'LifeControlButton'


def startup_command():
    """The command the Run key launches: the frozen exe, or pythonw + this script in development"""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    interpreter = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    return f'"{interpreter}" "{os.path.abspath(__file__)}"'


def install_startup():
    """Register the app to launch at logon via the per-user Run key — no elevation needed"""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as run_key:
        winreg.SetValueEx(run_key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())


def uninstall_startup():
    """Remove the logon registration; an absent value simply means nothing to do"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as run_key:
            winreg.DeleteValue(run_key, STARTUP_VALUE_NAME)
    except FileNotFoundError:
        pass


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


def ember_curve():
    """cubic-bezier(0.97, -0.1, 0.16, 1.01) from the requested CSS transition"""
    curve = QEasingCurve(QEasingCurve.Type.BezierSpline)
    curve.addCubicBezierSegment(QPointF(0.97, -0.1), QPointF(0.16, 1.01), QPointF(1.0, 1.0))
    return curve


def punch_curve():
    """A bouncier settle for one-off payoff moments, distinct from the
    continuous ember_curve used for ordinary section glow states"""
    curve = QEasingCurve(QEasingCurve.Type.OutBack)
    curve.setOvershoot(1.7)
    return curve


class ScanlineOverlay(QWidget):
    """Dotted CRT-style texture drifting slowly down the card"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.drift_offset = 0
        self.tile = self.build_tile(QColor(0, 0, 0, SCANLINE_DOT_ALPHA))

        self.drift_animation = QVariantAnimation(self)
        self.drift_animation.setStartValue(0.0)
        self.drift_animation.setEndValue(float(SCANLINE_PITCH))
        self.drift_animation.setDuration(SCANLINE_DRIFT_MS)
        self.drift_animation.setLoopCount(-1)
        self.drift_animation.valueChanged.connect(self.on_drift)
        self.drift_animation.start()

    def on_drift(self, value):
        # Repaint only on whole-pixel steps so the drift stays cheap
        offset = int(value) % SCANLINE_PITCH
        if offset != self.drift_offset:
            self.drift_offset = offset
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 6, 6)  # Match the card's corner radius
        painter.setClipPath(clip)
        painter.drawTiledPixmap(QRectF(self.rect()), self.tile,
                                QPointF(0, (SCANLINE_PITCH - self.drift_offset) % SCANLINE_PITCH))

    def build_tile(self, color):
        """A single-dot pixmap tiled across the card to make the scanline texture"""
        tile = QPixmap(SCANLINE_PITCH, SCANLINE_PITCH)
        tile.fill(Qt.GlobalColor.transparent)
        painter = QPainter(tile)
        painter.fillRect(0, 0, SCANLINE_DOT_SIZE, SCANLINE_DOT_SIZE, color)
        painter.end()
        return tile

    def surge(self, duration_ms):
        """Flare the dots ember-red and race the drift, like a power surge"""
        self.drift_animation.stop()
        if hasattr(self, 'blip_animation'):
            self.blip_animation.stop()  # A press-blip in flight must not clobber the surge tile
        self.tile = self.build_tile(QColor(251, 54, 64, 200))

        self.surge_animation = QVariantAnimation(self)
        self.surge_animation.setStartValue(0.0)
        self.surge_animation.setEndValue(float(SCANLINE_PITCH) * 8)
        self.surge_animation.setDuration(duration_ms)
        self.surge_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.surge_animation.valueChanged.connect(self.on_drift)
        self.surge_animation.start()

    def blip(self):
        """Flare the dots red the instant the button is pressed. Races briefly, then
        holds at the flared tile — it sustains for as long as the button stays down
        and only settles back once end_blip() is called on release"""
        self.drift_animation.stop()
        if hasattr(self, 'blip_animation'):
            self.blip_animation.stop()
        self.tile = self.build_tile(QColor(251, 54, 64, BLIP_DOT_ALPHA))

        self.blip_animation = QVariantAnimation(self)
        self.blip_animation.setStartValue(0.0)
        self.blip_animation.setEndValue(float(SCANLINE_PITCH) * 3)
        self.blip_animation.setDuration(BLIP_DURATION_MS)
        self.blip_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.blip_animation.valueChanged.connect(self.on_drift)
        self.blip_animation.start()

    def end_blip(self):
        """Restore the idle dim tile and resume the ordinary drift once the button
        is released — a no-op if the surge has already taken over the tile"""
        if hasattr(self, 'blip_animation'):
            self.blip_animation.stop()
        self.tile = self.build_tile(QColor(0, 0, 0, SCANLINE_DOT_ALPHA))
        self.update()
        self.drift_animation.start()


class GlowAnimator:
    """Eases a glow effect between states along the ember bezier curve"""

    def __init__(self, effect, curve=None):
        self.effect = effect
        self.curve = curve or ember_curve()
        self.start_state = (effect.blurRadius(), effect.color().alpha())
        self.target_state = self.start_state
        self.animation = QVariantAnimation(effect)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.valueChanged.connect(self.apply_progress)

    def snapped_blur(self, blur: float) -> float:
        """Quantise an animated blur radius so the drop shadow's padding stays
        on whole device pixels. The shadow pads its pixmap by the blur radius;
        at fractional display scales (125%/150%/...) an off-grid padding
        re-rounds to device pixels differently as it animates, visibly
        jittering the widget by a pixel or two per frame (Qt 6.10)"""
        widget = self.effect.parent()
        dpr = widget.devicePixelRatioF() if isinstance(widget, QWidget) else 1.0
        quantum = next((q for q in (1, 2, 4, 8) if dpr * q == round(dpr * q)), 4)
        return round(blur / quantum) * quantum

    def transition_to(self, blur: float, alpha: int, duration_ms: int, force: bool = False):
        target = (float(blur), int(alpha))
        current = (self.effect.blurRadius(), self.effect.color().alpha())
        if not force and target == self.target_state:
            if self.animation.state() == QVariantAnimation.State.Running or current == target:
                return
        self.animation.stop()
        self.start_state = current
        self.target_state = target
        self.animation.setDuration(duration_ms)
        self.animation.setEasingCurve(self.curve)
        self.animation.start()

    def flare_to(self, flare_state: tuple[float, int], settle_state: tuple[float, int], duration_ms: int):
        """Jump to the flare state, then settle back along the curve"""
        self.effect.setBlurRadius(self.snapped_blur(flare_state[0]))
        self.effect.setColor(QColor(251, 54, 64, flare_state[1]))
        self.transition_to(*settle_state, duration_ms, force=True)

    def apply_progress(self, t):
        # The bezier dips below zero, so clamp what reaches the effect
        blur = self.start_state[0] + (self.target_state[0] - self.start_state[0]) * t
        alpha = self.start_state[1] + (self.target_state[1] - self.start_state[1]) * t
        self.effect.setBlurRadius(self.snapped_blur(max(0.0, blur)))
        self.effect.setColor(QColor(251, 54, 64, max(0, min(255, round(alpha)))))


def typed_digit(event):
    """The digit of a plain (or numpad) number keypress, else None"""
    if event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
        return None
    return int(event.text()) if event.text().isdigit() else None


class DurationSpinBox(QSpinBox):
    """Duration input holding minutes: shows plain minutes under an hour,
    hours and minutes above. Below an hour the arrows step five minutes;
    above it they act on the hour or minute section, picked with left/right.
    Wraps past either end of the range."""

    sectionSwitched = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.minutes_section_active = False
        self.typed_value = None  # Pending typed digits for the active section
        self.setWrapping(True)  # Keep stepping enabled at both range ends

    def textFromValue(self, minutes):
        hours, mins = divmod(minutes, 60)
        if hours == 0:
            return f"{mins} min"
        return f"{hours} h {mins} min"

    def valueFromText(self, text: str) -> int:
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
        self.typed_value = None
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
        # The line edit is read-only (caret suppression), so digit entry is
        # handled here instead of by the native editor
        digit = typed_digit(event)
        if digit is not None:
            self.apply_typed_digit(digit)
            return
        self.typed_value = None  # Any other key restarts typed entry
        # A single left/right press jumps between the hour and minute sections
        if self.value() >= 60 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if event.key() == Qt.Key.Key_Right:
                self.minutes_section_active = True
                self.select_active_section()
                self.sectionSwitched.emit()
                return
            if event.key() == Qt.Key.Key_Left:
                self.minutes_section_active = False
                self.select_active_section()
                self.sectionSwitched.emit()
                return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self.typed_value = None
        super().focusOutEvent(event)

    def apply_typed_digit(self, digit):
        """Successive digits build up the active section's value, moving on to
        the minutes once the typed hours can take no further digit"""
        hours, mins = divmod(self.value(), 60)
        hour_section = self.value() >= 60 and not self.minutes_section_active
        maximum = self.maximum() // 60 if hour_section else 59
        candidate = self.typed_value * 10 + digit if self.typed_value is not None else digit
        if candidate > maximum:
            candidate = digit  # Overflowing digits start a fresh entry
        target = candidate * 60 + mins if hour_section else hours * 60 + candidate
        # setValue wraps out-of-range values when wrapping is on (so a typed
        # "2 min" would jump to 24 h); clamp into range by hand instead
        self.setValue(max(self.minimum(), min(self.maximum(), target)))
        self.select_active_section()
        if candidate * 10 > maximum:
            self.typed_value = None
            if hour_section:
                self.minutes_section_active = True
                self.select_active_section()
                self.sectionSwitched.emit()
        else:
            self.typed_value = candidate

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

        self.overlays_ready = False
        self.set_theme()
        self.init_ui()

        # Lock the window to its natural size
        self.adjustSize()
        self.setFixedSize(self.size())

        # Catch Return/numpad-Enter application-wide (regardless of which widget has
        # focus) via eventFilter rather than QShortcut, so press and release map onto
        # the button's real down state instead of animateClick()'s fixed-timer release
        QApplication.instance().installEventFilter(self)

        # Reopened while a shutdown is already pending: show the countdown instead
        # of letting a doomed second schedule end in the error popup
        pending_epoch = load_pending_epoch()
        if pending_epoch:
            self.enter_countdown_mode(pending_epoch)

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
        self.card_glow = make_glow(self.card, CARD_PULSE_BLUR, CARD_PULSE_ALPHA_MIN)
        self.card_glow_animator = GlowAnimator(self.card_glow)

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

        # Title, sized to span the full content width so it reads as centred
        title_label = QLabel("Liberation, not limitation")
        content_width = 460 - 48 - 48
        title_size = 14
        while title_size < 40:
            candidate = QFontMetrics(fira_mono(title_size + 1, QFont.Weight.Medium, -0.3))
            if candidate.horizontalAdvance(title_label.text()) > content_width:
                break
            title_size += 1
        title_label.setFont(fira_mono(title_size, QFont.Weight.Medium, -0.3))
        title_label.setStyleSheet("color: #F8FFE5;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)
        card_layout.addSpacing(30)

        # The big glowing display doubles as the input for the current mode.
        # The real widgets stay invisible (transparent text, no caret, no
        # selection); glowing overlay labels mirror them per section.
        display_input_style = (
            "background: transparent; border: none; color: transparent;"
            "selection-background-color: transparent; selection-color: transparent;"
        )

        time_font = fira_mono(64, QFont.Weight.Medium, 2.6)
        self.time_edit = QTimeEdit()
        self.time_edit.setFont(time_font)
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_edit.setStyleSheet(display_input_style)
        self.time_edit.setFixedWidth(QFontMetrics(time_font).horizontalAdvance('23:00') + 28)
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setWrapping(True)  # 23 wraps to 0, 59 to 0
        self.time_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        current_time = QTime.currentTime()
        hours = (current_time.hour() + 2) % 24  # Add 2 hours and wrap around at 24
        self.time_edit.setTime(QTime(hours, 0))
        # A read-only line edit is the only reliable way to suppress the
        # blinking caret: Qt 6.10's windows11 style paints it regardless of
        # PM_TextCursorWidth or any palette colour. Digit entry is re-added
        # by hand in eventFilter (apply_time_digit)
        self.time_edit.lineEdit().setReadOnly(True)
        self.time_typed_value = None  # Pending typed digits for the active section

        # Overlay labels live on the card, not the input, so their glow is never
        # clipped by the input widget's small rectangle
        self.hour_label = self.make_display_label(self.card, time_font)
        self.colon_label = self.make_display_label(self.card, time_font)
        self.minute_label = self.make_display_label(self.card, time_font)
        self.hour_glow = GlowAnimator(make_glow(self.hour_label, *TIME_GLOW_BASE))
        self.minute_glow = GlowAnimator(make_glow(self.minute_label, *TIME_GLOW_BASE))
        make_glow(self.colon_label, *TIME_GLOW_BASE)

        duration_font = fira_mono(36, QFont.Weight.Medium, 1.4)
        self.duration_spinbox = DurationSpinBox()
        self.duration_spinbox.setFont(duration_font)
        self.duration_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_spinbox.setStyleSheet(display_input_style)
        self.duration_spinbox.setFixedWidth(QFontMetrics(duration_font).horizontalAdvance('23 h 55 min') + 28)
        self.duration_spinbox.setRange(5, 1440)  # 5 minutes up to 24 hours
        self.duration_spinbox.setValue(60)  # Default one hour
        self.duration_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        # Same caret suppression as time_edit; DurationSpinBox.keyPressEvent
        # re-adds digit entry itself
        self.duration_spinbox.lineEdit().setReadOnly(True)

        self.duration_hour_label = self.make_display_label(self.card, duration_font)
        self.duration_minute_label = self.make_display_label(self.card, duration_font)
        self.duration_hour_glow = GlowAnimator(make_glow(self.duration_hour_label, *DURATION_GLOW_BASE))
        self.duration_minute_glow = GlowAnimator(make_glow(self.duration_minute_label, *DURATION_GLOW_BASE))

        self.display_container = QWidget()
        display_layout = QHBoxLayout()
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.addStretch(1)
        display_layout.addWidget(self.time_edit, alignment=Qt.AlignmentFlag.AlignVCenter)
        display_layout.addWidget(self.duration_spinbox, alignment=Qt.AlignmentFlag.AlignVCenter)
        display_layout.addStretch(1)
        self.display_container.setLayout(display_layout)
        self.display_container.setFixedHeight(
            max(self.time_edit.sizeHint().height(), self.duration_spinbox.sizeHint().height())
        )
        card_layout.addWidget(self.display_container)
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
        self.control_button.setStyleSheet(BUTTON_STYLE_NORMAL)
        self.control_button_glow = GlowAnimator(make_glow(self.control_button, *BUTTON_GLOW_BASE), curve=punch_curve())
        self.control_button.clicked.connect(self.dispatch_shutdown)
        self.control_button.setDefault(True)
        card_layout.addWidget(self.control_button)

        self.card.setLayout(card_layout)
        outer_layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)
        central_widget.setLayout(outer_layout)
        self.setCentralWidget(central_widget)

        # Dotted scanline texture drifting over the whole card
        self.scanline_overlay = ScanlineOverlay(self.card)
        self.control_button.pressed.connect(self.scanline_overlay.blip)
        self.control_button.released.connect(self.scanline_overlay.end_blip)

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

        # Left/right section jumps plus focus/click glow updates
        self.time_edit.installEventFilter(self)
        self.duration_spinbox.installEventFilter(self)
        self.time_edit.lineEdit().installEventFilter(self)
        self.duration_spinbox.lineEdit().installEventFilter(self)

        # Reactive glow triggers
        self.time_edit.timeChanged.connect(self.on_time_interaction)
        self.duration_spinbox.textChanged.connect(lambda _: self.layout_duration_overlay())
        self.duration_spinbox.valueChanged.connect(lambda _: self.refresh_display_glow(flare=True))
        self.duration_spinbox.sectionSwitched.connect(lambda: self.refresh_display_glow(flare=True))

    def make_display_label(self, parent, font):
        label = QLabel('', parent)
        label.setFont(font)
        label.setStyleSheet("color: #FB3640; background: transparent;")
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return label

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
        row_glow = make_glow(radio, 22, 35)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(15, 0, 15, 0)
        row_layout.setSpacing(12)
        mark = QLabel("[ ]")
        mark.setFont(fira_mono(15, QFont.Weight.DemiBold))
        mark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mark_glow = make_glow(mark, 12, 137)
        text = QLabel(label_text)
        text.setFont(fira_mono(14))
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row_layout.addWidget(mark)
        row_layout.addWidget(text)
        row_layout.addStretch(1)
        radio.setLayout(row_layout)
        return radio, mark, text, row_glow, mark_glow

    def showEvent(self, event):
        super().showEvent(event)
        if not self.overlays_ready:
            self.overlays_ready = True
            self.layout_time_overlay()
            self.layout_duration_overlay()
            self.refresh_display_glow()
            self.scanline_overlay.setGeometry(self.card.rect())
            self.scanline_overlay.raise_()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) \
                and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Mirror the button's real down state instead of firing on a timer, so
            # holding Enter behaves exactly like holding the mouse button down.
            # Auto-repeat presses must still be swallowed here (not just ignored) —
            # otherwise, once Windows' key-repeat delay kicks in, the repeat press
            # falls through to the button's own native default-button-on-Enter
            # handling and fires a full click while the key is still held down
            if event.type() == QEvent.Type.KeyPress and not event.isAutoRepeat() \
                    and not self.control_button.isDown() and self.control_button.isEnabled():
                # setDown() deliberately skips the pressed/released signals, so the
                # scanline blip must be driven by hand to match the mouse behaviour
                self.control_button.setDown(True)
                self.scanline_overlay.blip()
            elif event.type() == QEvent.Type.KeyRelease and not event.isAutoRepeat() \
                    and self.control_button.isDown():
                self.control_button.setDown(False)
                self.scanline_overlay.end_blip()
                if self.control_button.isEnabled():
                    self.dispatch_shutdown()
            return True
        if obj is self.time_edit and event.type() == QEvent.Type.KeyPress:
            # The line edit is read-only (caret suppression), so digit entry is
            # re-implemented here instead of the native editor handling it
            digit = typed_digit(event)
            if digit is not None:
                self.apply_time_digit(digit)
                return True
            self.time_typed_value = None  # Any other key restarts typed entry
            # Tab must leave the widget entirely rather than hop hour -> minute;
            # the minute section stays reachable with the right arrow instead
            if event.key() == Qt.Key.Key_Tab:
                self.focusNextChild()
                return True
            if event.key() == Qt.Key.Key_Backtab:
                self.focusPreviousChild()
                return True
            if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                if event.key() == Qt.Key.Key_Right:
                    self.time_edit.setSelectedSection(QTimeEdit.Section.MinuteSection)
                    self.refresh_display_glow(flare=True)
                    return True
                if event.key() == Qt.Key.Key_Left:
                    self.time_edit.setSelectedSection(QTimeEdit.Section.HourSection)
                    self.refresh_display_glow(flare=True)
                    return True
        if obj is self.time_edit and event.type() == QEvent.Type.FocusIn \
                and event.reason() in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason):
            # Tabbing in always lands on the hour section, wherever it last was
            QTimer.singleShot(0, lambda: self.time_edit.setSelectedSection(QTimeEdit.Section.HourSection))
        if obj is self.time_edit and event.type() == QEvent.Type.FocusOut:
            self.time_typed_value = None
        if event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut, QEvent.Type.MouseButtonRelease):
            # Read focus and section state after the event has settled
            QTimer.singleShot(0, self.refresh_display_glow)
        if obj in (self.time_edit, self.duration_spinbox) \
                and event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
            # The inputs re-centre after mode switches; keep the overlays anchored
            self.layout_time_overlay()
            self.layout_duration_overlay()
        return super().eventFilter(obj, event)

    def layout_time_overlay(self):
        """Place the glowing hour/colon/minute layers over the invisible input"""
        if not self.overlays_ready:
            return
        fm = QFontMetrics(self.time_edit.font())
        text = self.time_edit.text()  # Always HH:mm
        origin = self.time_edit.mapTo(self.card, QPoint(0, 0))
        x0 = origin.x() + (self.time_edit.width() - fm.horizontalAdvance(text)) // 2
        y = origin.y() + (self.time_edit.height() - fm.height()) // 2
        time_mode = self.radio_at_time.isChecked()
        for label in (self.hour_label, self.colon_label, self.minute_label):
            label.setVisible(time_mode)
        self.hour_label.setText(text[:2])
        self.hour_label.setGeometry(x0, y, fm.horizontalAdvance(text[:2]) + 2, fm.height())
        self.colon_label.setText(':')
        self.colon_label.setGeometry(x0 + fm.horizontalAdvance(text[:2]), y,
                                     fm.horizontalAdvance(':') + 2, fm.height())
        self.minute_label.setText(text[3:])
        self.minute_label.setGeometry(x0 + fm.horizontalAdvance(text[:3]), y,
                                      fm.horizontalAdvance(text[3:]) + 2, fm.height())

    def layout_duration_overlay(self):
        """Place the glowing hour/minute layers over the invisible duration input"""
        if not self.overlays_ready:
            return
        sb = self.duration_spinbox
        fm = QFontMetrics(sb.font())
        text = sb.textFromValue(sb.value())
        if ' h ' in text:
            hour_text = text[:text.index(' h ') + 2]
            minute_text = text[text.index(' h ') + 3:]
        else:
            hour_text, minute_text = '', text
        origin = sb.mapTo(self.card, QPoint(0, 0))
        x0 = origin.x() + (sb.width() - fm.horizontalAdvance(text)) // 2
        y = origin.y() + (sb.height() - fm.height()) // 2
        duration_mode = not self.radio_at_time.isChecked()
        if hour_text:
            self.duration_hour_label.setText(hour_text)
            self.duration_hour_label.setGeometry(x0, y, fm.horizontalAdvance(hour_text) + 2, fm.height())
            minute_x = x0 + fm.horizontalAdvance(text[:len(hour_text) + 1])
        else:
            minute_x = x0
        self.duration_hour_label.setVisible(duration_mode and bool(hour_text))
        self.duration_minute_label.setVisible(duration_mode)
        self.duration_minute_label.setText(minute_text)
        self.duration_minute_label.setGeometry(minute_x, y, fm.horizontalAdvance(minute_text) + 2, fm.height())

    def on_time_interaction(self):
        self.layout_time_overlay()
        self.refresh_display_glow(flare=True)

    def apply_time_digit(self, digit):
        """Successive digits build up the active section's value, rolling on to
        the minutes once the typed hour can take no further digit"""
        hour_section = self.time_edit.currentSection() == QTimeEdit.Section.HourSection
        maximum = 23 if hour_section else 59
        candidate = self.time_typed_value * 10 + digit if self.time_typed_value is not None else digit
        if candidate > maximum:
            candidate = digit  # Overflowing digits start a fresh entry
        current = self.time_edit.time()
        self.time_edit.setTime(QTime(candidate, current.minute()) if hour_section
                               else QTime(current.hour(), candidate))
        if candidate * 10 > maximum:
            self.time_typed_value = None
            if hour_section:
                self.time_edit.setSelectedSection(QTimeEdit.Section.MinuteSection)
                self.refresh_display_glow(flare=True)
        else:
            self.time_typed_value = candidate

    def set_label_heat(self, label, colour):
        label.setStyleSheet(f"color: {colour}; background: transparent;")

    def apply_section_glow(self, label, animator, is_active, focused, flare, base, selected, hot, flare_state):
        if is_active and focused:
            if flare:
                animator.flare_to(flare_state, hot, FLARE_TRANSITION_MS)
                # Flash the text near-white, then let a plain refresh restore it
                self.set_label_heat(label, GLOW_TEXT_FLARE)
                QTimer.singleShot(FLARE_TRANSITION_MS, lambda: self.refresh_display_glow(False))
            else:
                animator.transition_to(*hot, FOCUS_TRANSITION_MS)
                self.set_label_heat(label, GLOW_TEXT_HOT)
        elif is_active:
            # The selected section keeps a permanently raised glow, even unfocused
            animator.transition_to(*selected, FOCUS_TRANSITION_MS)
            self.set_label_heat(label, GLOW_TEXT_SELECTED)
        else:
            # On a section switch (flare refresh) the old section must release
            # its glow immediately; slow fades are only for losing window focus
            animator.transition_to(*base, SECTION_FADE_MS if flare else FOCUS_TRANSITION_MS)
            self.set_label_heat(label, GLOW_TEXT_BASE)

    def refresh_display_glow(self, flare=False):
        """The selected section always stands out; focus heats it, keypresses flare it"""
        if not self.overlays_ready:
            return
        time_focused = self.time_edit.hasFocus()
        hour_active = self.time_edit.currentSection() == QTimeEdit.Section.HourSection
        self.apply_section_glow(self.hour_label, self.hour_glow, hour_active, time_focused, flare,
                                TIME_GLOW_BASE, TIME_GLOW_SELECTED, TIME_GLOW_HOT, TIME_GLOW_FLARE)
        self.apply_section_glow(self.minute_label, self.minute_glow, not hour_active, time_focused, flare,
                                TIME_GLOW_BASE, TIME_GLOW_SELECTED, TIME_GLOW_HOT, TIME_GLOW_FLARE)

        sb = self.duration_spinbox
        duration_focused = sb.hasFocus()
        minutes_active = sb.minutes_section_active or sb.value() < 60
        self.apply_section_glow(self.duration_hour_label, self.duration_hour_glow,
                                not minutes_active, duration_focused, flare,
                                DURATION_GLOW_BASE, DURATION_GLOW_SELECTED, DURATION_GLOW_HOT, DURATION_GLOW_FLARE)
        self.apply_section_glow(self.duration_minute_label, self.duration_minute_glow,
                                minutes_active, duration_focused, flare,
                                DURATION_GLOW_BASE, DURATION_GLOW_SELECTED, DURATION_GLOW_HOT, DURATION_GLOW_FLARE)

    def update_input_visibility(self):
        at_time = self.radio_at_time.isChecked()
        self.time_edit.setVisible(at_time)
        self.duration_spinbox.setVisible(not at_time)
        # Qt defers the relayout caused by setVisible to the next event-loop
        # pass, so without forcing it here the overlays below would be placed
        # against the input's stale (left-aligned) geometry and visibly jump
        # to centre a frame later
        self.display_container.layout().activate()
        self.mode_sub_label.setText("SHUTDOWN AT" if at_time else "SHUTDOWN IN")
        self.update_mode_visuals()
        self.layout_time_overlay()
        self.layout_duration_overlay()
        self.refresh_display_glow()

    def update_mode_visuals(self):
        for radio, mark, text, row_glow, mark_glow in self.mode_rows:
            checked = radio.isChecked()
            mark.setText("[x]" if checked else "[ ]")
            mark.setStyleSheet("color: #FB3640;" if checked else "color: rgba(248, 255, 229, 35%);")
            text.setStyleSheet("color: #F8FFE5;" if checked else "color: rgba(248, 255, 229, 45%);")
            row_glow.setEnabled(checked)
            mark_glow.setEnabled(checked)

    def update_card_glow(self, phase):
        alpha = round(CARD_PULSE_ALPHA_MIN + phase * (CARD_PULSE_ALPHA_MAX - CARD_PULSE_ALPHA_MIN))
        self.card_glow.setColor(QColor(251, 54, 64, alpha))

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
        save_scheduled_epoch(time.time() + seconds)
        return True

    def dispatch_shutdown(self):
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
            self.celebrate_and_close()

    def set_shutdown_after(self):
        seconds = self.duration_spinbox.value() * 60

        if self.execute_shutdown_command(seconds):
            self.celebrate_and_close()

    def celebrate_and_close(self):
        """Flash the button, card and scanline texture; hold the moment before the app closes"""
        self.control_button.setEnabled(False)
        self.control_button.setText("LIFE CONTROL REGAINED")
        self.control_button.setStyleSheet(
            "QPushButton {background-color: #FB3640; color: #160A0E; border: 2px solid #FB3640; border-radius: 5px; padding: 16px;}"
            "QPushButton:disabled {background-color: #FB3640; color: #160A0E;}"
        )
        self.control_button_glow.flare_to(BUTTON_GLOW_FLASH, BUTTON_GLOW_HELD, EXIT_DELAY_MS)

        self.pulse_animation.stop()  # Freeze the emberpulse loop so the flare reads clearly
        self.card_glow_animator.flare_to(CARD_GLOW_FLASH, CARD_GLOW_HELD, EXIT_DELAY_MS)

        self.scanline_overlay.surge(EXIT_DELAY_MS)

        QTimer.singleShot(EXIT_DELAY_MS, self.close)

    def enter_countdown_mode(self, epoch):
        """A shutdown is already pending: the button becomes a live countdown
        display and cannot be pressed. The inputs open on the pending shutdown's
        clock time but stay fully interactive"""
        self.shutdown_epoch = epoch
        scheduled = time.localtime(epoch)
        self.radio_at_time.setChecked(True)
        self.time_edit.setTime(QTime(scheduled.tm_hour, scheduled.tm_min))
        self.control_button.setEnabled(False)
        self.control_button.setStyleSheet(BUTTON_STYLE_COUNTDOWN)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)
        self.update_countdown()

    def update_countdown(self):
        """Tick the button text, recomputed from the clock so sleep cannot skew it"""
        remaining = int(self.shutdown_epoch - time.time())
        if remaining <= 0:
            self.leave_countdown_mode()
            return
        hours, rest = divmod(remaining, 3600)
        minutes, seconds = divmod(rest, 60)
        self.control_button.setText(f"SHUTDOWN IN {hours:02d}:{minutes:02d}:{seconds:02d}")

    def leave_countdown_mode(self):
        """The shutdown moment passed yet the machine is still up (cancelled outside
        the app), so clear the stale note and hand the button back"""
        self.countdown_timer.stop()
        clear_scheduled_epoch()
        self.control_button.setEnabled(True)
        self.control_button.setStyleSheet(BUTTON_STYLE_NORMAL)
        self.control_button.setText("GET LIFE CONTROL")

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
    # Self-registration flags: act on the registry and leave before any UI comes up
    if '--install-startup' in sys.argv[1:]:
        install_startup()
        sys.exit(0)
    if '--uninstall-startup' in sys.argv[1:]:
        uninstall_startup()
        sys.exit(0)

    app = QApplication(sys.argv)

    # Set application-wide icon
    app.setWindowIcon(QIcon(resource_path('assets', 'icon.png')))

    load_bundled_fonts()

    main_window = LifeControlButtonApp()
    main_window.center_window_on_primary_monitor()

    main_window.show()
    sys.exit(app.exec())
