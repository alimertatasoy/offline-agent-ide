import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QSlider, QLabel, QGroupBox
from PyQt6.QtCore import pyqtSignal, Qt
import qtawesome as qta

class SettingsWidget(QWidget):
    sound_toggled = pyqtSignal(bool)
    volume_changed = pyqtSignal(int) # 0 to 100
    minimap_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #39FF14;
                font-family: 'Consolas', monospace;
            }
            QGroupBox {
                border: 1px solid #00FF00;
                margin-top: 12px;
                padding-top: 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #39FF14;
            }
            QCheckBox {
                color: #00FF00;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #00FF00;
                background-color: #000000;
            }
            QCheckBox::indicator:checked {
                background-color: #39FF14;
                border: 1px solid #39FF14;
            }
            QSlider::groove:horizontal {
                border: 1px solid #00FF00;
                height: 8px;
                background: #000000;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #39FF14;
                border: 1px solid #39FF14;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QLabel {
                color: #00FF00;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Title
        title_label = QLabel("EDİTÖR AYARLARI")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #39FF14; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Group 1: Ses Efektleri (Audio Settings)
        audio_group = QGroupBox("Klavye Sesleri")
        audio_layout = QVBoxLayout(audio_group)

        self.sound_check = QCheckBox("Klavye Sesini Etkinleştir")
        self.sound_check.setChecked(True)
        self.sound_check.toggled.connect(self.sound_toggled.emit)
        audio_layout.addWidget(self.sound_check)

        # Volume Slider
        vol_label_layout = QHBoxLayout()
        vol_label_layout.addWidget(QLabel("Ses Seviyesi:"))
        self.vol_value_lbl = QLabel("50%")
        vol_label_layout.addWidget(self.vol_value_lbl, 0, Qt.AlignmentFlag.AlignRight)
        audio_layout.addLayout(vol_label_layout)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        audio_layout.addWidget(self.volume_slider)

        layout.addWidget(audio_group)

        # Group 2: Görünüm Ayarları (Appearance Settings)
        view_group = QGroupBox("Görünüm")
        view_layout = QVBoxLayout(view_group)

        self.minimap_check = QCheckBox("Minimap Göster")
        self.minimap_check.setChecked(True)
        self.minimap_check.toggled.connect(self.minimap_toggled.emit)
        view_layout.addWidget(self.minimap_check)

        layout.addWidget(view_group)
        layout.addStretch()

    def on_volume_changed(self, val):
        self.vol_value_lbl.setText(f"{val}%")
        self.volume_changed.emit(val)
