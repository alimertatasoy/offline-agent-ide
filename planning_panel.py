import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QAbstractItemView)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import pyqtSignal, QRect, Qt
import qtawesome as qta

class FlowchartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = []
        self.setMinimumHeight(200)

    def set_steps(self, steps):
        self.steps = steps
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Black background
        painter.fillRect(self.rect(), QColor("#000000"))

        if not self.steps:
            painter.setPen(QColor("#005500"))
            painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aktif bir plan bulunmuyor.")
            return

        # Draw steps vertically
        width = self.width()
        box_w = min(220, width - 40)
        box_h = 40
        spacing = 30
        
        y_offset = 20
        positions = []

        # First calculate positions and draw connections
        for i in range(len(self.steps)):
            x = (width - box_w) // 2
            y = y_offset + i * (box_h + spacing)
            positions.append((x, y))

        # Draw arrow lines between boxes
        for i in range(len(positions) - 1):
            x1, y1 = positions[i]
            x2, y2 = positions[i+1]
            
            # Start of arrow: bottom center of box i
            start_x = x1 + box_w // 2
            start_y = y1 + box_h
            
            # End of arrow: top center of box i+1
            end_x = start_x
            end_y = y2

            # Determine arrow color based on status of target step
            next_status = self.steps[i+1].get('status', 'pending')
            if next_status == 'completed':
                pen = QPen(QColor("#39FF14"), 2, Qt.PenStyle.SolidLine)
            elif next_status == 'running':
                pen = QPen(QColor("#00FFCC"), 2, Qt.PenStyle.DashLine)
            else:
                pen = QPen(QColor("#005500"), 2, Qt.PenStyle.SolidLine)

            painter.setPen(pen)
            painter.drawLine(start_x, start_y, end_x, end_y)
            
            # Draw tiny arrowhead
            painter.setBrush(QBrush(pen.color()))
            arrow_points = [
                Qt.Key.Key_Up, # just placeholder
            ]
            # Simple arrowhead drawing
            painter.drawPolygon([
                self.map_point(end_x, end_y),
                self.map_point(end_x - 5, end_y - 8),
                self.map_point(end_x + 5, end_y - 8)
            ])

        # Draw boxes
        for i, step in enumerate(self.steps):
            x, y = positions[i]
            rect = QRect(x, y, box_w, box_h)
            
            status = step.get('status', 'pending')
            title = step.get('task', f"Adım {i+1}")
            
            # Colors based on status
            if status == 'completed':
                border_color = QColor("#39FF14")  # Neon Green
                bg_color = QColor("#001100")
                text_color = QColor("#39FF14")
                status_text = "[X]"
            elif status == 'running':
                border_color = QColor("#00FFCC")  # Cyan
                bg_color = QColor("#002222")
                text_color = QColor("#00FFCC")
                status_text = "[>]"
            elif status == 'failed':
                border_color = QColor("#FF3333")  # Red
                bg_color = QColor("#220000")
                text_color = QColor("#FF3333")
                status_text = "[!]"
            else:
                border_color = QColor("#005500")  # Dark Green
                bg_color = QColor("#000000")
                text_color = QColor("#008800")
                status_text = "[ ]"

            # Draw rounded box
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(rect, 4.0, 4.0)

            # Draw text
            painter.setPen(text_color)
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            
            # Left align status
            painter.drawText(x + 10, y + 25, f"{status_text} {title[:20]}")

        # Update widget minimum height dynamically
        needed_height = y_offset + len(self.steps) * (box_h + spacing) + 20
        if self.minimumHeight() != needed_height:
            self.setMinimumHeight(needed_height)

    def map_point(self, x, y):
        from PyQt6.QtCore import QPoint
        return QPoint(x, y)


class PlanningWidget(QWidget):
    approved = pyqtSignal(list) # Emits edited steps list when approved
    rejected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = [] # list of dicts: {'id': 1, 'task': 'create main.py', 'status': 'pending'}

        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #39FF14;
                font-family: 'Consolas', monospace;
            }
            QTableWidget {
                background-color: #000000;
                color: #00FF00;
                border: 1px solid #00FF00;
                gridline-color: #003300;
            }
            QTableWidget::item:selected {
                background-color: #002200;
                color: #39FF14;
            }
            QHeaderView::section {
                background-color: #050505;
                color: #39FF14;
                border: 1px solid #00FF00;
                padding: 4px;
            }
            QPushButton {
                background-color: #002200;
                color: #39FF14;
                border: 1px solid #39FF14;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #004400;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Plan Info Header
        self.header_lbl = QLabel("PLANLAMA VE AJAN MODU")
        self.header_lbl.setStyleSheet("font-size: 11pt; font-weight: bold; color: #39FF14; margin-bottom: 6px;")
        layout.addWidget(self.header_lbl)

        # Buttons Bar
        btn_layout = QHBoxLayout()
        
        self.approve_btn = QPushButton("Onayla")
        self.approve_btn.setIcon(qta.icon('fa5s.check', color='#39FF14'))
        self.approve_btn.setStyleSheet("background-color: #002200; border: 1px solid #39FF14; color: #39FF14;")
        self.approve_btn.clicked.connect(self.on_approve)
        
        self.reject_btn = QPushButton("Reddet")
        self.reject_btn.setIcon(qta.icon('fa5s.times', color='#FF3333'))
        self.reject_btn.setStyleSheet("background-color: #220000; border: 1px solid #FF3333; color: #FF3333;")
        self.reject_btn.clicked.connect(self.rejected.emit)

        self.add_step_btn = QPushButton("Adım Ekle")
        self.add_step_btn.setIcon(qta.icon('fa5s.plus', color='#00FFCC'))
        self.add_step_btn.clicked.connect(self.add_empty_step)

        btn_layout.addWidget(self.approve_btn)
        btn_layout.addWidget(self.reject_btn)
        btn_layout.addWidget(self.add_step_btn)
        layout.addLayout(btn_layout)

        # Steps Table (Editable list of steps)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Sıra", "Görev Adımı", "Durum"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setMinimumHeight(150)
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)

        # Visual Flowchart Section Header
        flowchart_lbl = QLabel("PLAN AKIŞ ŞEMASI")
        flowchart_lbl.setStyleSheet("font-size: 9pt; font-weight: bold; color: #39FF14; margin-top: 10px; margin-bottom: 2px;")
        layout.addWidget(flowchart_lbl)

        # Flowchart Canvas
        self.flowchart = FlowchartWidget()
        layout.addWidget(self.flowchart, 1)

    def load_plan(self, steps):
        self.steps = steps
        self.table.blockSignals(True)
        self.table.setRowCount(len(steps))
        for i, step in enumerate(steps):
            # ID/Order
            id_item = QTableWidgetItem(str(i+1))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, id_item)

            # Task Description
            task_item = QTableWidgetItem(step.get('task', ''))
            self.table.setItem(i, 1, task_item)

            # Status
            status_item = QTableWidgetItem(step.get('status', 'pending'))
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 2, status_item)

        self.table.blockSignals(False)
        self.flowchart.set_steps(steps)

    def on_item_changed(self, item):
        row = item.row()
        col = item.column()
        if col == 1 and row < len(self.steps):
            self.steps[row]['task'] = item.text()
            self.flowchart.set_steps(self.steps)

    def add_empty_step(self):
        new_step = {'task': 'Yeni Görev Adımı', 'status': 'pending'}
        self.steps.append(new_step)
        self.load_plan(self.steps)

    def on_approve(self):
        self.approved.emit(self.steps)
