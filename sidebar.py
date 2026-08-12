import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeView, 
                             QComboBox, QPushButton, QTextBrowser, QTextEdit, 
                             QLabel, QSplitter, QMenu, QInputDialog, QMessageBox,
                             QFileIconProvider)
from PyQt6.QtGui import QFileSystemModel, QFont
from PyQt6.QtCore import pyqtSignal, Qt, QFileInfo, QSortFilterProxyModel, QTimer
import qtawesome as qta

class IgnoreFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        name = model.fileName(index)
        ignored = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache", ".idea", ".vscode"}
        if name in ignored:
            return False
        return True

class CustomIconProvider(QFileIconProvider):
    def icon(self, parameter):
        if isinstance(parameter, QFileInfo):
            path = parameter.filePath()
            if parameter.isDir():
                return qta.icon('fa5s.folder', color='#E0B034')
            
            ext = parameter.suffix().lower()
            if ext == "py":
                return qta.icon('fa5b.python', color='#3776AB')
            elif ext == "php":
                return qta.icon('fa5b.php', color='#777BB4')
            elif ext in ("html", "htm"):
                return qta.icon('fa5b.html5', color='#E34F26')
            elif ext == "css":
                return qta.icon('fa5b.css3-alt', color='#1572B6')
            elif ext in ("js", "jsx"):
                return qta.icon('fa5b.js', color='#F7DF1E')
            elif ext in ("ts", "tsx"):
                return qta.icon('fa5s.code', color='#3178C6') # TypeScript blue representation
            elif ext in ("json", "yml", "yaml", "toml", "xml"):
                return qta.icon('fa5s.file-code', color='#F1C40F')
            elif ext in ("md", "txt"):
                return qta.icon('fa5s.file-alt', color='#5D6D7E')
            else:
                return qta.icon('fa5s.file', color='#CCCCCC')
                
        return super().icon(parameter)

class FileExplorer(QWidget):
    file_double_clicked = pyqtSignal(str)

    def __init__(self, workspace_path=None, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path or os.getcwd()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setIconProvider(CustomIconProvider())
        
        self.proxy_model = IgnoreFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)

        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setColumnHidden(1, True) # Hide Size
        self.tree.setColumnHidden(2, True) # Hide Type
        self.tree.setColumnHidden(3, True) # Hide Date Modified
        self.tree.setHeaderHidden(True)
        self.tree.doubleClicked.connect(self.on_double_click)

        # Context Menu setup
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # Style TreeView
        self.tree.setStyleSheet("""
            QTreeView {
                background-color: #000000;
                color: #00FF00;
                border: none;
            }
            QTreeView::item:hover {
                background-color: #002200;
            }
            QTreeView::item:selected {
                background-color: #004400;
                color: #39FF14;
            }
        """)

        layout.addWidget(self.tree)
        
        if workspace_path:
            self.set_workspace(workspace_path)

    def set_workspace(self, path):
        self.workspace_path = path
        source_index = self.model.index(path)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.tree.setRootIndex(proxy_index)

    def on_double_click(self, index):
        source_index = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_index)
        if os.path.isfile(path):
            self.file_double_clicked.emit(path)

    def show_context_menu(self, position):
        proxy_index = self.tree.indexAt(position)
        source_index = self.proxy_model.mapToSource(proxy_index)
        menu = QMenu(self)

        new_file_action = menu.addAction("Yeni Dosya")
        new_folder_action = menu.addAction("Yeni Klasör")
        
        delete_action = None
        if proxy_index.isValid():
            menu.addSeparator()
            delete_action = menu.addAction("Sil")

        action = menu.exec(self.tree.mapToGlobal(position))
        
        # Get target directory for creation
        target_dir = self.workspace_path
        if proxy_index.isValid():
            selected_path = self.model.filePath(source_index)
            if os.path.isdir(selected_path):
                target_dir = selected_path
            else:
                target_dir = os.path.dirname(selected_path)

        if action == new_file_action:
            name, ok = QInputDialog.getText(self, "Yeni Dosya", "Dosya Adı:")
            if ok and name:
                file_path = os.path.join(target_dir, name)
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("")
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Dosya oluşturulamadı: {e}")
        elif action == new_folder_action:
            name, ok = QInputDialog.getText(self, "Yeni Klasör", "Klasör Adı:")
            if ok and name:
                dir_path = os.path.join(target_dir, name)
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Klasör oluşturulamadı: {e}")
        elif delete_action and action == delete_action:
            selected_path = self.model.filePath(source_index)
            confirm = QMessageBox.question(self, "Silmeyi Onayla", f"Silmek istediğinize emin misiniz?\n{selected_path}",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    if os.path.isdir(selected_path):
                        import shutil
                        shutil.rmtree(selected_path)
                    else:
                        os.remove(selected_path)
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Silme işlemi başarısız: {e}")


class OllamaSidebar(QWidget):
    send_prompt_signal = pyqtSignal(str, str, str) # model_name, user_prompt, context_code
    cancel_signal = pyqtSignal()
    quick_action_signal = pyqtSignal(str, str) # action_name, model_name
    insert_code_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #00FF00;
            }
            QComboBox {
                background-color: #000000;
                border: 1px solid #00FF00;
                color: #39FF14;
                padding: 4px;
                border-radius: 3px;
            }
            QTextBrowser {
                background-color: #000000;
                border: 1px solid #00FF00;
                border-radius: 4px;
                color: #8AE9C1;
                padding: 8px;
            }
            QTextEdit {
                background-color: #000000;
                border: 1px solid #00FF00;
                border-radius: 4px;
                color: #39FF14;
            }
            QPushButton {
                background-color: #002200;
                color: #39FF14;
                border: 1px solid #39FF14;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #004400;
            }
            QPushButton:disabled {
                color: #004400;
                border: 1px solid #002200;
                background-color: #000000;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Model Selection Panel
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        model_layout.addWidget(self.model_combo, 1)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(qta.icon('fa5s.sync-alt', color='#39FF14'))
        self.refresh_btn.setToolTip("Modelleri Yenile")
        model_layout.addWidget(self.refresh_btn)
        layout.addLayout(model_layout)

        # Quick Actions
        actions_layout = QHBoxLayout()
        self.explain_btn = QPushButton("Açıkla")
        self.explain_btn.setIcon(qta.icon('fa5s.info-circle', color='#39FF14'))
        self.explain_btn.setToolTip("Seçili kodu açıkla")

        self.refactor_btn = QPushButton("Refaktör")
        self.refactor_btn.setIcon(qta.icon('fa5s.magic', color='#39FF14'))
        self.refactor_btn.setToolTip("Seçili kodu iyileştir")

        actions_layout.addWidget(self.explain_btn)
        actions_layout.addWidget(self.refactor_btn)
        layout.addLayout(actions_layout)

        # Chat display area
        self.chat_display = QTextBrowser()
        self.chat_display.setFont(QFont("Consolas", 10))
        self.chat_display.setOpenExternalLinks(True)
        self.clear_chat()
        layout.addWidget(self.chat_display)

        # Insert Code button
        self.insert_code_btn = QPushButton("Kodları İmlece Aktar")
        self.insert_code_btn.setIcon(qta.icon('fa5s.code', color='#39FF14'))
        self.insert_code_btn.setToolTip("Yapay zekanın yazdığı son kod bloğunu editördeki imleç konumuna yapıştırır.")
        layout.addWidget(self.insert_code_btn)

        # Render buffering timer (40ms throttled refresh)
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(40)
        self.update_timer.timeout.connect(self.refresh_chat_display)

        # Prompt input area
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Yapay zekaya sorun... (Ctrl+Enter Gönderir)")
        self.input_edit.setMaximumHeight(80)
        layout.addWidget(self.input_edit)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setIcon(qta.icon('fa5s.trash', color='#39FF14'))
        self.clear_btn.setStyleSheet("background-color: #001100; border: 1px solid #39FF14; color: #39FF14;")

        self.stop_btn = QPushButton("Durdur")
        self.stop_btn.setIcon(qta.icon('fa5s.stop', color='#FF3333'))
        self.stop_btn.setStyleSheet("background-color: #220000; border: 1px solid #FF3333; color: #FF3333;")
        self.stop_btn.setEnabled(False)

        self.send_btn = QPushButton("Gönder")
        self.send_btn.setIcon(qta.icon('fa5s.paper-plane', color='#39FF14'))

        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.send_btn)
        layout.addLayout(btn_layout)

        # Connect signals
        self.send_btn.clicked.connect(self.on_send)
        self.stop_btn.clicked.connect(self.cancel_signal.emit)
        self.clear_btn.clicked.connect(self.clear_chat)
        self.explain_btn.clicked.connect(lambda: self.quick_action_signal.emit("explain", self.model_combo.currentText()))
        self.refactor_btn.clicked.connect(lambda: self.quick_action_signal.emit("refactor", self.model_combo.currentText()))
        self.insert_code_btn.clicked.connect(self.insert_code_signal.emit)

    def clear_chat(self):
        self.chat_display.setHtml("""
            <div style='color: #888888; font-style: italic; text-align: center; margin-top: 50px;'>
                Kodunuzla ilgili sorular sorabilir, seçili alanları açıklamasını veya yeniden yazmasını isteyebilirsiniz.
            </div>
        """)
        self.chat_history = []

    def set_models(self, models):
        self.model_combo.clear()
        self.model_combo.addItems(models)

    def refresh_chat_display(self):
        html = ""
        for s, t in self.chat_history:
            bg = "#161616" if s == "AI" else "#333333"
            align = "left" if s == "AI" else "right"
            margin = "margin-right: 10%;" if s == "AI" else "margin-left: 10%;"
            
            # Simple line break format
            formatted_text = t.replace('\n', '<br>').replace('    ', '&nbsp;&nbsp;&nbsp;&nbsp;')
            
            html += f"""
            <div style='text-align: {align}; margin-bottom: 10px;'>
                <div style='display: inline-block; background-color: {bg}; color: white; 
                            padding: 8px; border-radius: 8px; {margin} text-align: left;'>
                    <b>{s}:</b><br>{formatted_text}
                </div>
            </div>
            """
        self.chat_display.setHtml(html)
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def append_message(self, sender, text):
        if not self.chat_history:
            self.chat_display.clear()

        self.chat_history.append((sender, text))
        self.refresh_chat_display()

    def update_last_message(self, token):
        # Appends token to the last message if it's from AI
        if self.chat_history and self.chat_history[-1][0] == "AI":
            sender, text = self.chat_history[-1]
            self.chat_history[-1] = (sender, text + token)
        else:
            self.chat_history.append(("AI", token))

        # Start timer for throttled UI rendering instead of direct drawing on every token
        if not self.update_timer.isActive():
            self.update_timer.start()

    def on_send(self):
        prompt = self.input_edit.toPlainText().strip()
        if not prompt:
            return
        
        model = self.model_combo.currentText()
        if not model:
            self.append_message("Sistem", "Lütfen önce bir model seçin veya yenileyin.")
            return

        self.append_message("Kullanıcı", prompt)
        self.input_edit.clear()
        
        self.send_prompt_signal.emit(model, prompt, "")

    def get_last_code_block(self):
        for sender, text in reversed(self.chat_history):
            if sender == "AI":
                import re
                matches = re.findall(r"```(?:[a-zA-Z0-9]+)?\n(.*?)\n```", text, re.DOTALL)
                if matches:
                    return matches[-1]
                else:
                    return text
        return ""
