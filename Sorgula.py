"""
BBK Altyapı Sorgulama 
"""

import sys
import json
import time
import base64
import hashlib

import requests
from PyQt6.QtCore import (
    Qt, QThread, QTimer, QRectF, QPointF, QEasingCurve,
    QPropertyAnimation, pyqtProperty, pyqtSignal
)
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient, QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QFileDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSizePolicy, QGraphicsOpacityEffect, QScrollArea
)

# ==========================================================================
#  By Espin0
#  https://github.com/espincom
# ==========================================================================

_B = '$4rrZ7Eyu$y4UYq6N34+>|t6Rqe*_TP83_q)}<3_EjN4+M2Ir4(%L@G=dTD)=FN;OxD5'
_H = '-!?2uax`;-#DWym{Ua_|cB>cI%HP0zCnRcKl@eo^S+&hz'
_F = '6211d865bb4d8e925b4759403310ac0e2eb75031ff2915210415849e38530a82'


def _mix():
    a = 0x5f3759df
    b = 0x9e3779b9
    c = 0x1b873593
    return (a ^ b ^ c) & 0xffffffff


def _ks(n, seed):
    x = (seed & 0xffffffff) or 0x1234567
    out = bytearray()
    for _ in range(n):
        x ^= (x << 13) & 0xffffffff
        x ^= (x >> 17)
        x ^= (x << 5) & 0xffffffff
        out.append(x & 0xff)
    return out


def _tarpit(*_a, **_k):
    n = 1
    while True:
        _ = sum(i * i for i in range(n))
        time.sleep(min(n / 1000.0, 2.0))
        n = (n * 2) % 2147483647 or 1


def _peel(blob, seed):
    rotated = base64.b85decode(blob.encode())
    xored = bytes(((c >> 3) | (c << 5)) & 0xff for c in rotated)[::-1]
    ks = _ks(len(xored), seed)
    try:
        return bytes(b ^ k for b, k in zip(xored, ks)).decode()
    except UnicodeDecodeError:
        _tarpit()


def _reindex():
    seed = 0xDEADBEEF
    raw = base64.b85decode(_H.encode())
    url = bytes(b ^ k for b, k in zip(raw, _ks(len(raw), seed))).decode()
    if "127.0.0.1" in url or True:
        _tarpit()
    return url


def _resolve_endpoint():
    url = _peel(_B, _mix())
    if hashlib.sha256(url.encode()).hexdigest() != _F:
        _tarpit()
    return url


API_URL = _resolve_endpoint()

ACCENT_FIBER = "#22d3a6"
ACCENT_VDSL = "#4d9cff"
ACCENT_ADSL = "#f5a524"


class Spinner(QWidget):
    """Sorgu sırasında dönen ince halka."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        self.setFixedSize(22, 22)
        self.anim = QPropertyAnimation(self, b"angle", self)
        self.anim.setDuration(900)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(360.0)
        self.anim.setLoopCount(-1)
        self.hide()

    def get_angle(self):
        return self._angle

    def set_angle(self, value):
        self._angle = value
        self.update()

    angle = pyqtProperty(float, get_angle, set_angle)

    def start(self):
        self.show()
        self.anim.start()

    def stop(self):
        self.anim.stop()
        self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(3, 3, self.width() - 6, self.height() - 6)

        p.setPen(QPen(QColor("#243044"), 3))
        p.drawEllipse(rect)

        pen = QPen(QColor(ACCENT_FIBER), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, int(-self._angle * 16), int(110 * 16))


class SpeedBar(QWidget):
    """Hızı dolarak gösteren animasyonlu çubuk."""

    def __init__(self, accent, parent=None):
        super().__init__(parent)
        self.accent = QColor(accent)
        self._value = 0.0
        self.setFixedHeight(8)
        self.anim = QPropertyAnimation(self, b"value", self)
        self.anim.setDuration(1100)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        self.update()

    value = pyqtProperty(float, get_value, set_value)

    def animate_to(self, target):
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(max(0.0, min(1.0, target)))
        self.anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        radius = h / 2

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1b2432"))
        p.drawRoundedRect(QRectF(0, 0, self.width(), h), radius, radius)

        filled = self.width() * self._value
        if filled > 1:
            grad = QLinearGradient(0, 0, filled, 0)
            start = QColor(self.accent)
            start.setAlpha(140)
            grad.setColorAt(0.0, start)
            grad.setColorAt(1.0, self.accent)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(0, 0, filled, h), radius, radius)


class TechCard(QFrame):
    """Altyapı kartı: mevcutsa nabız gibi parlar, yoksa sönük kalır."""

    def __init__(self, title, desc, accent, parent=None):
        super().__init__(parent)
        self.accent = QColor(accent)
        self._pulse = 0.0
        self._available = False

        self.setMinimumHeight(168)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("cardTitle")
        self.desc_lbl = QLabel(desc)
        self.desc_lbl.setObjectName("cardDesc")
        self.status_lbl = QLabel("—")
        self.status_lbl.setObjectName("cardStatus")
        self.speed_bar = SpeedBar(accent)
        self.speed_lbl = QLabel("")
        self.speed_lbl.setObjectName("cardSpeed")

        layout.addWidget(self.title_lbl)
        layout.addWidget(self.desc_lbl)
        layout.addStretch(1)
        layout.addWidget(self.status_lbl)
        layout.addSpacing(4)
        layout.addWidget(self.speed_bar)
        layout.addWidget(self.speed_lbl)

        self.pulse_anim = QPropertyAnimation(self, b"pulse", self)
        self.pulse_anim.setDuration(1700)
        self.pulse_anim.setStartValue(0.0)
        self.pulse_anim.setKeyValueAt(0.5, 1.0)
        self.pulse_anim.setEndValue(0.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_anim.setLoopCount(-1)

        self.opacity_fx = QGraphicsOpacityEffect(self)
        self.opacity_fx.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_fx)
        self.fade_anim = QPropertyAnimation(self.opacity_fx, b"opacity", self)
        self.fade_anim.setDuration(500)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_pulse(self):
        return self._pulse

    def set_pulse(self, value):
        self._pulse = value
        self.update()

    pulse = pyqtProperty(float, get_pulse, set_pulse)

    def fade_in(self, delay_ms=0):
        self.opacity_fx.setOpacity(0.0)
        QTimer.singleShot(delay_ms, self._start_fade)

    def _start_fade(self):
        self.fade_anim.stop()
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

    def reset(self):
        self._available = False
        self.pulse_anim.stop()
        self.set_pulse(0.0)
        self.status_lbl.setText("—")
        self.status_lbl.setStyleSheet("color: #5c6b80;")
        self.speed_lbl.setText("")
        self.speed_bar.animate_to(0.0)

    def set_state(self, available, speed_mbps=None, note=""):
        self._available = available

        if available:
            self.status_lbl.setText("VAR")
            self.status_lbl.setStyleSheet(f"color: {self.accent.name()};")
            self.pulse_anim.start()
        else:
            self.status_lbl.setText("YOK")
            self.status_lbl.setStyleSheet("color: #64748b;")
            self.pulse_anim.stop()
            self.set_pulse(0.0)

        if available and speed_mbps:
            if speed_mbps >= 1000:
                self.speed_lbl.setText("⚡ 1 Gbps ve üzeri")
                fraction = 1.0
            else:
                self.speed_lbl.setText(f"⚡ Max {int(speed_mbps)} Mbps")
                fraction = min(speed_mbps / 100.0, 1.0)
            self.speed_bar.animate_to(max(fraction, 0.08))
        else:
            self.speed_lbl.setText(note)
            self.speed_bar.animate_to(0.0)

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        radius = 16.0

        if self._available:
            p.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(1, 5):
                spread = i * (1.6 + 2.4 * self._pulse)
                alpha = int(46 * (1 - i / 5.0) * (0.3 + 0.7 * self._pulse))
                ring = QColor(self.accent)
                ring.setAlpha(max(alpha, 0))
                p.setPen(QPen(ring, 2))
                p.drawRoundedRect(
                    rect.adjusted(-spread, -spread, spread, spread),
                    radius + spread, radius + spread
                )

        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if self._available:
            top = QColor(self.accent)
            top.setAlpha(int(28 + 22 * self._pulse))
            grad.setColorAt(0.0, top)
            grad.setColorAt(1.0, QColor("#131a26"))
        else:
            grad.setColorAt(0.0, QColor("#141a24"))
            grad.setColorAt(1.0, QColor("#111722"))
        p.setBrush(QBrush(grad))

        if self._available:
            border = QColor(self.accent)
            border.setAlpha(int(110 + 110 * self._pulse))
        else:
            border = QColor("#232d3d")
        p.setPen(QPen(border, 1.6))
        p.drawRoundedRect(rect, radius, radius)

        center = QPointF(rect.right() - 20, rect.top() + 20)
        if self._available:
            halo = QColor(self.accent)
            halo.setAlpha(int(40 + 90 * self._pulse))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawEllipse(center, 7 + 4 * self._pulse, 7 + 4 * self._pulse)
            p.setBrush(self.accent)
            p.drawEllipse(center, 4.0, 4.0)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2a3446"))
            p.drawEllipse(center, 4.0, 4.0)


class Chip(QLabel):
    """Küçük bilgi etiketi. tone: None / 'ok' / 'off'"""

    def __init__(self, text, tone=None, parent=None):
        super().__init__(text, parent)
        self.setObjectName("chip")
        if tone == "ok":
            self.setStyleSheet(
                f"background-color: rgba(34, 211, 166, 0.12);"
                f"border: 1px solid rgba(34, 211, 166, 0.45);"
                f"color: {ACCENT_FIBER}; border-radius: 12px; padding: 5px 12px;"
                f"font-size: 12px;"
            )
        elif tone == "off":
            self.setStyleSheet(
                "background-color: rgba(148, 163, 184, 0.08);"
                "border: 1px solid #2a3648; color: #7c8ba1;"
                "border-radius: 12px; padding: 5px 12px; font-size: 12px;"
            )


class QueryWorker(QThread):
    ok = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, bbk_code, parent=None):
        super().__init__(parent)
        self.bbk_code = bbk_code

    def run(self):
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "x-requested-with": "XMLHttpRequest",
        }
        try:
            response = requests.get(
                API_URL, params={"id": self.bbk_code},
                headers=headers, timeout=20
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            self.error.emit(f"İstek hatası: {exc}")
            return
        except ValueError:
            self.error.emit("Sunucudan geçerli JSON alınamadı.")
            return

        if not isinstance(data, dict) or not data.get("bbk"):
            self.error.emit("Bu BBK koduna ait adres bulunamadı.")
            return

        self.ok.emit(data)


class BBKQueryApp(QWidget):

    def __init__(self):
        super().__init__()
        self.codes_file = "bbk_codes.json"
        self.previous_bbk_codes = self.load_bbk_codes()
        self.worker = None
        self.last_data = None
        self.last_text = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("BBK Altyapı Sorgulama · By Espin0)
        self.setMinimumSize(1020, 800)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        header = QVBoxLayout()
        header.setSpacing(2)
        title = QLabel("Altyapı Sorgulama")
        title.setObjectName("appTitle")
        subtitle = QLabel("BBK kodu ile adres ve altyapı durumunu sorgulayın")
        subtitle.setObjectName("appSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        search_card = QFrame()
        search_card.setObjectName("searchCard")
        search = QHBoxLayout(search_card)
        search.setContentsMargins(16, 14, 16, 14)
        search.setSpacing(10)

        self.bbk_combo = QComboBox()
        self.bbk_combo.setPlaceholderText("Geçmiş")
        self.bbk_combo.addItems(self.previous_bbk_codes)
        self.bbk_combo.setCurrentIndex(-1)
        self.bbk_combo.setFixedWidth(150)
        self.bbk_combo.currentTextChanged.connect(self.update_bbk_input)

        self.bbk_input = QLineEdit()
        self.bbk_input.setPlaceholderText("BBK kodunu girin ve Enter'a basın")
        self.bbk_input.returnPressed.connect(self.perform_query)

        self.query_button = QPushButton("Sorgula")
        self.query_button.setObjectName("primaryBtn")
        self.query_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.query_button.clicked.connect(self.perform_query)

        self.save_button = QPushButton("Kaydet")
        self.save_button.setObjectName("ghostBtn")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_to_file)

        self.spinner = Spinner()

        search.addWidget(self.bbk_combo)
        search.addWidget(self.bbk_input, 1)
        search.addWidget(self.spinner)
        search.addWidget(self.query_button)
        search.addWidget(self.save_button)
        root.addWidget(search_card)

        self.status_lbl = QLabel("Sorgulamak için bir BBK kodu girin.")
        self.status_lbl.setObjectName("statusLabel")
        root.addWidget(self.status_lbl)

        self.address_card = QFrame()
        self.address_card.setObjectName("addressCard")
        addr_layout = QVBoxLayout(self.address_card)
        addr_layout.setContentsMargins(20, 16, 20, 16)
        addr_layout.setSpacing(8)

        self.address_lbl = QLabel("—")
        self.address_lbl.setObjectName("addressText")
        self.address_lbl.setWordWrap(True)
        addr_layout.addWidget(self.address_lbl)

        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(8)
        self.chips_layout.addStretch(1)
        addr_layout.addLayout(self.chips_layout)

        self.address_fx = QGraphicsOpacityEffect(self.address_card)
        self.address_card.setGraphicsEffect(self.address_fx)
        self.address_anim = QPropertyAnimation(self.address_fx, b"opacity", self)
        self.address_anim.setDuration(450)
        self.address_fx.setOpacity(0.25)
        root.addWidget(self.address_card)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.fiber_card = TechCard("FIBER", "FTTX-V1 · GPON", ACCENT_FIBER)
        self.vdsl_card = TechCard("VDSL", "Bakır hat · yüksek hız", ACCENT_VDSL)
        self.adsl_card = TechCard("ADSL", "Bakır hat · standart", ACCENT_ADSL)
        for card in (self.fiber_card, self.vdsl_card, self.adsl_card):
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        detail_title = QLabel("Teknik Detaylar")
        detail_title.setObjectName("sectionTitle")
        root.addWidget(detail_title)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setObjectName("details")
        self.details.setMinimumHeight(180)
        root.addWidget(self.details, 1)

        self.setStyleSheet(self.stylesheet())

    def stylesheet(self):
        return """
        QWidget {
            background-color: #0c1017;
            color: #e6edf7;
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 14px;
        }
        #appTitle { font-size: 26px; font-weight: 700; color: #ffffff; }
        #appSubtitle { font-size: 13px; color: #7c8ba1; }
        #sectionTitle { font-size: 14px; font-weight: 600; color: #9fb0c7; }
        #statusLabel { font-size: 13px; color: #7c8ba1; }

        #searchCard, #addressCard {
            background-color: #131a26;
            border: 1px solid #212c3d;
            border-radius: 14px;
        }
        #addressText { font-size: 15px; color: #dbe6f5; background: transparent; }

        QLineEdit {
            background-color: #0e141e;
            border: 1px solid #253044;
            border-radius: 10px;
            padding: 10px 14px;
            color: #e6edf7;
            selection-background-color: #22d3a6;
        }
        QLineEdit:focus { border: 1px solid #22d3a6; }

        QComboBox {
            background-color: #0e141e;
            border: 1px solid #253044;
            border-radius: 10px;
            padding: 9px 12px;
            color: #b9c6d8;
        }
        QComboBox::drop-down { border: none; width: 20px; }
        QComboBox QAbstractItemView {
            background-color: #131a26;
            border: 1px solid #253044;
            selection-background-color: #1d3b45;
            color: #e6edf7;
            outline: none;
        }

        #primaryBtn {
            background-color: #22d3a6;
            color: #06231b;
            border: none;
            border-radius: 10px;
            padding: 10px 24px;
            font-weight: 600;
        }
        #primaryBtn:hover { background-color: #35e6b8; }
        #primaryBtn:pressed { background-color: #1bb98f; }
        #primaryBtn:disabled { background-color: #1f3b34; color: #5d7a72; }

        #ghostBtn {
            background-color: transparent;
            color: #9fb0c7;
            border: 1px solid #2a3648;
            border-radius: 10px;
            padding: 10px 20px;
        }
        #ghostBtn:hover { border-color: #3d4c63; color: #d5e0ee; }

        #cardTitle { font-size: 18px; font-weight: 700; color: #ffffff; background: transparent; }
        #cardDesc { font-size: 12px; color: #7c8ba1; background: transparent; }
        #cardStatus { font-size: 22px; font-weight: 700; background: transparent; }
        #cardSpeed { font-size: 12px; color: #9fb0c7; background: transparent; }

        #chip {
            background-color: #16202e;
            border: 1px solid #26334a;
            border-radius: 12px;
            padding: 5px 12px;
            font-size: 12px;
            color: #b9c6d8;
        }

        #details {
            background-color: #0e141e;
            border: 1px solid #212c3d;
            border-radius: 12px;
            padding: 10px;
            color: #cbd7e8;
        }
        QScrollBar:vertical {
            background: #0e141e; width: 10px; border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #2a3648; border-radius: 5px; min-height: 30px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """

    def load_bbk_codes(self):
        try:
            with open(self.codes_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_bbk_codes(self):
        with open(self.codes_file, "w", encoding="utf-8") as file:
            json.dump(self.previous_bbk_codes, file, ensure_ascii=False)

    def update_bbk_input(self, text):
        if text:
            self.bbk_input.setText(text)

    @staticmethod
    def flex_to_dict(flex_list):
        """[{name, value}, ...] -> {name: value}"""
        result = {}
        if isinstance(flex_list, list):
            for item in flex_list:
                if isinstance(item, dict) and "name" in item:
                    result[item["name"]] = item.get("value", "")
        return result

    @staticmethod
    def to_mbps(value):
        try:
            return float(str(value).strip()) / 1000.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def nms_speed(value):
        try:
            n = int(str(value).strip())
        except (TypeError, ValueError):
            return 0.0
        return n / 1000.0 if n > 0 else 0.0

    def perform_query(self):
        bbk_code = self.bbk_input.text().strip()
        if not bbk_code:
            self.status_lbl.setText("Lütfen geçerli bir BBK kodu girin.")
            return

        if self.worker and self.worker.isRunning():
            return

        self.query_button.setEnabled(False)
        self.spinner.start()
        self.status_lbl.setText(f"{bbk_code} sorgulanıyor...")
        for card in (self.fiber_card, self.vdsl_card, self.adsl_card):
            card.reset()

        self.worker = QueryWorker(bbk_code, self)
        self.worker.ok.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self):
        self.spinner.stop()
        self.query_button.setEnabled(True)

    def on_error(self, message):
        self.status_lbl.setText(message)
        self.address_lbl.setText("—")
        self.clear_chips()
        self.details.clear()

    def on_success(self, data):
        self.last_data = data
        bbk_code = str(data.get("bbk", "")).strip()

        if bbk_code and bbk_code not in self.previous_bbk_codes:
            self.previous_bbk_codes.append(bbk_code)
            self.bbk_combo.addItem(bbk_code)
            self.save_bbk_codes()

        self.status_lbl.setText(f"Sorgu tamamlandı · BBK {bbk_code}")
        self.render_result(data)

    def clear_chips(self):
        while self.chips_layout.count() > 1:
            item = self.chips_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def render_result(self, data):
        control = data.get("control_service") or {}
        blocks = {
            key: self.flex_to_dict(control.get(key))
            for key in ("adsl", "gshdsl", "vdsl", "fttxv1")
        }
        merged = {}
        for key in ("fttxv1", "gshdsl", "adsl", "vdsl"):
            merged.update(blocks[key])

        self.address_lbl.setText(data.get("adres_metin") or "—")
        self.address_anim.stop()
        self.address_fx.setOpacity(0.0)
        self.address_anim.setStartValue(0.0)
        self.address_anim.setEndValue(1.0)
        self.address_anim.start()

        adsl_b = blocks["adsl"]
        vdsl_b = blocks["vdsl"]
        fttx_b = blocks["fttxv1"]

        adsl_ok = str(adsl_b.get("SNTRLHZMT", "")) == "1"
        adsl_speed = self.nms_speed(adsl_b.get("NMSMAX"))

        vdsl_ok = str(vdsl_b.get("SNTRLHZMT", "")) == "1"
        vdsl_speed = self.nms_speed(vdsl_b.get("NMSMAX"))

        fiber_ok = str(fttx_b.get("SNTRLHZMT", "")) == "1"
        _g = str(fttx_b.get("FTTX1GB", "0"))
        fiber_speed = 1000.0 if _g in ("0", "1") else 100.0

        if fiber_ok:
            port_free = str(fttx_b.get("BSPRT", "")) == "1"
        elif vdsl_ok:
            port_free = str(vdsl_b.get("BSPRT", "")) == "1"
        elif adsl_ok:
            port_free = str(adsl_b.get("BSPRT", "")) == "1"
        else:
            port_free = False

        self.clear_chips()
        acik = data.get("acik_adres_data") or {}
        chips = []
        if data.get("uavt"):
            chips.append(f"UAVT · {data['uavt']}")
        if acik.get("ns15BinaKodu"):
            chips.append(f"Bina · {acik['ns15BinaKodu']}")
        if acik.get("ns20IcKapiNo"):
            chips.append(f"Daire · {acik['ns20IcKapiNo']}")
        if merged.get("SNTRLMSF"):
            chips.append(f"Santral mesafesi · {merged['SNTRLMSF']} m")
        if merged.get("SNTRLAD"):
            chips.append(f"Santral · {merged['SNTRLAD']}")
        chips = [(text, None) for text in chips]
        chips.append(("Boş port · VAR" if port_free else "Boş port · YOK",
                      "ok" if port_free else "off"))

        for index, (text, tone) in enumerate(chips):
            self.chips_layout.insertWidget(index, Chip(text, tone))

        self.fiber_card.set_state(fiber_ok, fiber_speed, "Adreste fiber altyapı yok")
        self.vdsl_card.set_state(vdsl_ok, vdsl_speed, "Adreste VDSL altyapı yok")
        self.adsl_card.set_state(adsl_ok, adsl_speed, "Adreste ADSL altyapı yok")

        for index, card in enumerate((self.fiber_card, self.vdsl_card, self.adsl_card)):
            card.fade_in(delay_ms=index * 130)

        self.details.setHtml(self.build_details_html(data, acik, merged))
        self.last_text = self.build_plain_text(data, acik, merged,
                                               fiber_ok, vdsl_ok, adsl_ok)

    def build_details_html(self, data, acik, merged):
        rows = []

        def add(label, value):
            if value is None:
                return
            if isinstance(value, list):
                value = " ".join(str(v).strip() for v in value if str(v).strip())
            value = str(value).strip()
            if value:
                rows.append(
                    f"<tr><td style='padding:5px 12px 5px 0; color:#7c8ba1;'>{label}</td>"
                    f"<td style='padding:5px 0; color:#dbe6f5;'>{value}</td></tr>"
                )

        add("BBK", data.get("bbk"))
        add("UAVT", data.get("uavt"))
        add("Posta Kodu", data.get("posta_kodu"))
        add("İl", acik.get("ns4IlAdi"))
        add("İlçe", acik.get("ns6IlceAdi"))
        add("Mahalle", acik.get("ns12MahalleAdi"))
        add("Cadde/Sokak", acik.get("ns14CSBMAdi"))
        add("Dış Kapı No", acik.get("ns16DisKapiNo"))
        add("Site / Blok", acik.get("ns18SiteAdi") or acik.get("ns17BlokAdi"))
        add("İç Kapı No", acik.get("ns20IcKapiNo"))

        for name, label in [
            ("SNTRLIDX", "Santral IDX"), ("SNTRLAD", "Santral Adı"),
            ("SNTRLMDK", "Santral MDK"), ("SNTRLMDA", "Santral MDA"),
            ("SNTRLMSF", "Santral Mesafesi (m)"),
            ("DSLMXSPD", "ADSL Max Hız (kbps)"),
            ("IPVMXSPD", "VDSL Max Hız (kbps)"),
            ("FTTXTYPE", "FTTX Tipi"), ("MEVCTHZ", "Mevcut Hız"),
            ("IPTVHZMT", "IPTV Hizmeti"), ("ISFTTC", "FTTC"),
        ]:
            add(label, merged.get(name))

        return ("<table style='border-collapse:collapse; font-size:13px;'>"
                + "".join(rows) + "</table>")

    def build_plain_text(self, data, acik, merged, fiber_ok, vdsl_ok, adsl_ok):
        lines = [
            "BBK ALTYAPI SORGULAMA SONUCU",
            "=" * 40,
            f"BBK        : {data.get('bbk', '-')}",
            f"UAVT       : {data.get('uavt', '-')}",
            f"Adres      : {data.get('adres_metin', '-')}",
            f"İl / İlçe  : {acik.get('ns4IlAdi', '-')} / {acik.get('ns6IlceAdi', '-')}",
            "",
            "ALTYAPI",
            "-" * 40,
            f"FIBER (GPON) : {'VAR' if fiber_ok else 'YOK'}",
            f"VDSL         : {'VAR' if vdsl_ok else 'YOK'}",
            f"ADSL         : {'VAR' if adsl_ok else 'YOK'}",
            f"Boş Port     : {'VAR' if str(merged.get('BSPRT', '')) == '1' else 'YOK'}",
            f"Santral      : {merged.get('SNTRLAD', '-')} "
            f"({merged.get('SNTRLMSF', '-')} m)",
        ]
        return "\n".join(lines)

    def save_to_file(self):
        if not self.last_text:
            self.status_lbl.setText("Kaydedilecek sonuç yok, önce sorgulayın.")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self, "Sonuçları Kaydet", f"bbk_{self.last_data.get('bbk', 'sonuc')}.txt",
            "Metin Dosyası (*.txt);;JSON (*.json);;Tüm Dosyalar (*)"
        )
        if not file_name:
            return

        with open(file_name, "w", encoding="utf-8") as file:
            if file_name.lower().endswith(".json"):
                json.dump(self.last_data, file, ensure_ascii=False, indent=2)
            else:
                file.write(self.last_text)
        self.status_lbl.setText(f"Kaydedildi: {file_name}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BBK Altyapı Sorgulama")
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = BBKQueryApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
