import sys
import os
import wave
import struct
import math
from PyQt6.QtWidgets import QWidget, QPlainTextEdit, QTextEdit
from PyQt6.QtGui import QColor, QTextFormat, QPainter, QFont, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QImage
from PyQt6.QtCore import QRect, QSize, Qt, QRegularExpression, QUrl
from PyQt6.QtMultimedia import QSoundEffect

def write_wav(filename, frequency, duration, decay):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    with wave.open(filename, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(num_samples):
            t = float(i) / sample_rate
            envelope = math.exp(-decay * t)
            val = math.sin(2.0 * math.pi * frequency * t) * envelope
            sample = int(val * 32767.0)
            wav.writeframesraw(struct.pack('<h', sample))

def generate_sound_effects():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    click_path = os.path.join(current_dir, 'click.wav')
    if not os.path.exists(click_path):
        write_wav(click_path, frequency=1200.0, duration=0.04, decay=50.0)
        
    backspace_path = os.path.join(current_dir, 'backspace.wav')
    if not os.path.exists(backspace_path):
        write_wav(backspace_path, frequency=800.0, duration=0.06, decay=40.0)
        
    enter_path = os.path.join(current_dir, 'enter.wav')
    if not os.path.exists(enter_path):
        write_wav(enter_path, frequency=1500.0, duration=0.08, decay=30.0)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        # Keyword format
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#39FF14"))  # Neon Green
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "and", "as", "assert", "async", "await", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda", "None",
            "nonlocal", "not", "or", "pass", "raise", "return", "True", "try",
            "while", "with", "yield"
        ]
        for word in keywords:
            pattern = QRegularExpression(rf"\b{word}\b")
            self.highlightingRules.append((pattern, keyword_format))

        # Builtins format
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#00FFCC"))  # Neon Cyan/Teal
        builtins = ["print", "len", "range", "str", "int", "float", "list", "dict", "set", "tuple", "open", "type"]
        for word in builtins:
            pattern = QRegularExpression(rf"\b{word}\b")
            self.highlightingRules.append((pattern, builtin_format))

        # Self format
        self_format = QTextCharFormat()
        self_format.setForeground(QColor("#FF3366"))  # Red/Pink
        self.highlightingRules.append((QRegularExpression(r"\bself\b"), self_format))

        # Function format
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#D2FF2D"))  # Yellow-Green
        self.highlightingRules.append((QRegularExpression(r"\b[A-Za-z0-9_]+(?=\()"), function_format))

        # String format
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#B5FF68"))  # Bright Lime-Green
        self.highlightingRules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.string_format))
        self.highlightingRules.append((QRegularExpression(r"'[^'\\]*(\\.['\\\\]*)*'"), self.string_format))

        # Comment format
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#005500"))  # Dark Forest Green
        self.highlightingRules.append((QRegularExpression(r"#[^\n]*"), self.comment_format))

        # Multi-line string / docstring formats
        self.multi_line_comment_format = QTextCharFormat()
        self.multi_line_comment_format.setForeground(QColor("#006600"))  # Darker Green for triple strings

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QRegularExpression(pattern)
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

        # Handle multi-line strings (""" or ''')
        self.setCurrentBlockState(0)
        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = text.find('"""')
            if startIndex == -1:
                startIndex = text.find("'''")

        while startIndex >= 0:
            delimiter = '"""' if text[startIndex:startIndex+3] == '"""' else "'''"
            endIndex = text.find(delimiter, startIndex + 3)

            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + 3

            self.setFormat(startIndex, commentLength, self.multi_line_comment_format)
            startIndex = text.find(delimiter, startIndex + commentLength)


class Minimap(QPlainTextEdit):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setDocument(editor.document())
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Tiny font for minimap representation
        font = QFont("Consolas", 3)
        self.setFont(font)
        
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #050505;
                color: #555555;
                border: none;
            }
        """)
        
        # Disable scroll signals loop by tracking if we are currently updating scroll
        self.is_syncing = False
        
        # Connect vertical scroll bar
        self.verticalScrollBar().valueChanged.connect(self.sync_to_editor)
        self.editor.verticalScrollBar().valueChanged.connect(self.sync_from_editor)

    def sync_to_editor(self, value):
        if self.is_syncing:
            return
        self.is_syncing = True
        
        editor_scrollbar = self.editor.verticalScrollBar()
        minimap_scrollbar = self.verticalScrollBar()
        
        if minimap_scrollbar.maximum() > 0:
            ratio = value / minimap_scrollbar.maximum()
            editor_scrollbar.setValue(int(ratio * editor_scrollbar.maximum()))
            
        self.is_syncing = False

    def sync_from_editor(self, value):
        if self.is_syncing:
            return
        self.is_syncing = True
        
        editor_scrollbar = self.editor.verticalScrollBar()
        minimap_scrollbar = self.verticalScrollBar()
        
        if editor_scrollbar.maximum() > 0:
            ratio = value / editor_scrollbar.maximum()
            minimap_scrollbar.setValue(int(ratio * minimap_scrollbar.maximum()))
            
        self.is_syncing = False

    def mousePressEvent(self, event):
        self.scroll_editor(event.position().y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.scroll_editor(event.position().y())
        super().mouseMoveEvent(event)

    def scroll_editor(self, y):
        # Calculate scroll value based on click position
        ratio = y / self.height()
        editor_scrollbar = self.editor.verticalScrollBar()
        editor_scrollbar.setValue(int(ratio * editor_scrollbar.maximum()))


class CodeEditor(QPlainTextEdit):
    sound_enabled = True
    sound_volume = 0.5  # Float 0.0 to 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.minimap = Minimap(self)

        # Generate sound files on startup
        generate_sound_effects()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.sound_click = QSoundEffect(self)
        self.sound_click.setSource(QUrl.fromLocalFile(os.path.join(current_dir, 'click.wav')))
        self.sound_click.setVolume(0.5)

        self.sound_backspace = QSoundEffect(self)
        self.sound_backspace.setSource(QUrl.fromLocalFile(os.path.join(current_dir, 'backspace.wav')))
        self.sound_backspace.setVolume(0.5)

        self.sound_enter = QSoundEffect(self)
        self.sound_enter.setSource(QUrl.fromLocalFile(os.path.join(current_dir, 'enter.wav')))
        self.sound_enter.setVolume(0.5)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)

        # Editor Styles with Skull background
        self.setFont(QFont("Consolas", 11))
        
        # Resize original skull image to a small watermark size (e.g. 180x180)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        original_skull = os.path.join(current_dir, 'skull.png')
        resized_skull = os.path.join(current_dir, 'skull_resized.png')
        
        if os.path.exists(original_skull):
            try:
                img = QImage(original_skull)
                if not img.isNull():
                    scaled_img = img.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    scaled_img.save(resized_skull)
            except Exception as e:
                print(f"Resim boyutlandırma hatası: {e}")

        skull_path = resized_skull.replace('\\', '/')
        
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #000000;
                color: #8AE9C1;
                border: none;
            }
        """)
        self.viewport().setStyleSheet(f"""
            background-image: url('{skull_path}');
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-color: transparent;
        """)

        # Initialize linter variables
        self.error_line = None
        self.error_message = ""

        # Install highlighter
        self.highlighter = PythonSyntaxHighlighter(self.document())
        self.highlightCurrentLine()

    def lineNumberAreaWidth(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        space = 24 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        # viewport margins: left=line numbers, right=minimap (80px if visible, else 0)
        right_margin = 80 if self.minimap.isVisible() else 0
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, right_margin, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
        
        # Position Minimap on the right
        minimap_width = 80
        self.minimap.setGeometry(QRect(cr.right() - minimap_width, cr.top(), minimap_width, cr.height()))

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#0C0C0C")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)

        if self.error_line is not None:
            err_selection = QTextEdit.ExtraSelection()
            err_selection.format.setUnderlineColor(QColor("#FF0000"))
            err_selection.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            # Find block
            block = self.document().findBlockByLineNumber(self.error_line - 1)
            if block.isValid():
                err_selection.cursor = QTextCursor(block)
                err_selection.cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                extraSelections.append(err_selection)

        self.setExtraSelections(extraSelections)

    def check_syntax(self, file_path):
        self.error_line = None
        self.error_message = ""
        
        code = self.toPlainText()
        if not code.strip():
            self.highlightCurrentLine()
            return None
            
        if file_path:
            if file_path.endswith(".py"):
                try:
                    import ast
                    ast.parse(code)
                except SyntaxError as e:
                    self.error_line = e.lineno
                    self.error_message = f"Python Hatası: {e.msg} (Satır {e.lineno})"
                except Exception:
                    pass
            elif file_path.endswith(".php"):
                # Basic PHP Tag/Brace matching linter
                opened = code.count('{')
                closed = code.count('}')
                if opened != closed:
                    # mark last line
                    self.error_line = max(1, len(code.splitlines()))
                    self.error_message = f"PHP Parantez Hatası: '{{' ve '}}' sayıları eşleşmiyor! (Açılan: {opened}, Kapanan: {closed})"
            elif file_path.endswith(".css"):
                opened = code.count('{')
                closed = code.count('}')
                if opened != closed:
                    self.error_line = max(1, len(code.splitlines()))
                    self.error_message = f"CSS Süslü Parantez Hatası: Eşleşmeyen parantezler var."

        self.highlightCurrentLine()
        return self.error_message

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#000000"))

        # Right border line
        painter.setPen(QColor("#151515"))
        painter.drawLine(self.lineNumberArea.width() - 1, event.rect().top(), 
                         self.lineNumberArea.width() - 1, event.rect().bottom())

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#005500"))
                # If current block, highlight line number
                if blockNumber == self.textCursor().blockNumber():
                    painter.setPen(QColor("#39FF14"))
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                else:
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)

                painter.drawText(0, top, self.lineNumberArea.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def wheelEvent(self, event):
        # Ctrl + Mouse Wheel for Font Zoom
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            font = self.font()
            size = font.pointSize()
            if delta > 0:
                font.setPointSize(size + 1)
            elif size > 6:
                font.setPointSize(size - 1)
            self.setFont(font)
            self.updateLineNumberAreaWidth(0)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if CodeEditor.sound_enabled:
            key = event.key()
            sound = None
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                sound = self.sound_enter
            elif key == Qt.Key.Key_Backspace:
                sound = self.sound_backspace
            # Ignore modifier keys (Ctrl, Alt, Shift alone)
            elif key not in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                sound = self.sound_click
            
            if sound:
                sound.setVolume(CodeEditor.sound_volume)
                sound.play()

    def set_minimap_visible(self, visible):
        self.minimap.setVisible(visible)
        self.updateLineNumberAreaWidth(0)
