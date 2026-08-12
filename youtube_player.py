import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
import qtawesome as qta

class YoutubePlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #00FF00;
            }
            QLineEdit {
                background-color: #050505;
                color: #39FF14;
                border: 1px solid #00FF00;
                padding: 4px;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #002200;
                color: #39FF14;
                border: 1px solid #39FF14;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #004400;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        nav_layout = QHBoxLayout()

        self.back_btn = QPushButton()
        self.back_btn.setIcon(qta.icon('fa5s.arrow-left', color='#39FF14'))
        self.back_btn.setToolTip("Geri")
        
        self.forward_btn = QPushButton()
        self.forward_btn.setIcon(qta.icon('fa5s.arrow-right', color='#39FF14'))
        self.forward_btn.setToolTip("İleri")
        
        self.reload_btn = QPushButton()
        self.reload_btn.setIcon(qta.icon('fa5s.sync-alt', color='#39FF14'))
        self.reload_btn.setToolTip("Yenile")

        self.url_line = QLineEdit()
        self.url_line.setPlaceholderText("YouTube ara veya link girin...")
        self.url_line.returnPressed.connect(self.load_url)

        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.forward_btn)
        nav_layout.addWidget(self.reload_btn)
        nav_layout.addWidget(self.url_line, 1)

        layout.addLayout(nav_layout)

        # Quick Links Layout
        quick_layout = QHBoxLayout()
        
        self.yt_music_btn = QPushButton("YT Music")
        self.yt_music_btn.setIcon(qta.icon('fa5b.youtube', color='#39FF14'))
        self.yt_music_btn.clicked.connect(lambda: self.navigate_to("https://music.youtube.com"))
        
        self.lofi_btn = QPushButton("Lo-Fi")
        self.lofi_btn.setIcon(qta.icon('fa5s.music', color='#39FF14'))
        self.lofi_btn.clicked.connect(lambda: self.navigate_to("https://www.youtube.com/results?search_query=lofi+hip+hop+live+radio"))

        self.coding_beats_btn = QPushButton("Coding Beats")
        self.coding_beats_btn.setIcon(qta.icon('fa5s.headphones', color='#39FF14'))
        self.coding_beats_btn.clicked.connect(lambda: self.navigate_to("https://www.youtube.com/results?search_query=coding+music+focus"))

        quick_layout.addWidget(self.yt_music_btn)
        quick_layout.addWidget(self.lofi_btn)
        quick_layout.addWidget(self.coding_beats_btn)

        layout.addLayout(quick_layout)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background-color: #000000; border: 1px solid #00FF00;")
        layout.addWidget(self.web_view, 1)

        # Connect navigation
        self.back_btn.clicked.connect(self.web_view.back)
        self.forward_btn.clicked.connect(self.web_view.forward)
        self.reload_btn.clicked.connect(self.web_view.reload)
        self.web_view.urlChanged.connect(self.url_changed)

        # Default Page: YouTube
        self.navigate_to("https://www.youtube.com")

    def load_url(self):
        text = self.url_line.text().strip()
        if not text:
            return
        
        if text.startswith("http://") or text.startswith("https://"):
            self.navigate_to(text)
        else:
            # Treat as search query on YouTube
            search_url = f"https://www.youtube.com/results?search_query={text.replace(' ', '+')}"
            self.navigate_to(search_url)

    def navigate_to(self, url):
        self.web_view.load(QUrl(url))

    def url_changed(self, qurl):
        self.url_line.setText(qurl.toString())
