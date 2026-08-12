import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTabWidget, 
                             QFileDialog, QMessageBox, QStatusBar, QMenuBar, QMenu)
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtCore import Qt, QTimer, QProcess

from editor import CodeEditor
from sidebar import FileExplorer, OllamaSidebar
from ollama_client import OllamaChatWorker, get_local_models
from console import ConsoleWidget
from youtube_player import YoutubePlayerWidget
from settings_panel import SettingsWidget
from planning_panel import PlanningWidget

class MainWindow(QMainWindow):
    def __init__(self, workspace_path=None):
        super().__init__()
        self.setWindowTitle("Antigravity Local AI Code Editor")
        self.setGeometry(100, 100, 1200, 800)

        # Active workspace
        self.workspace_path = workspace_path or os.getcwd()

        # Dictionary to track file path per editor tab: {tab_widget_index: file_path}
        self.open_files = {}

        # Set Dark Palette/Style for main window
        self.setStyleSheet("""
            * {
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QMainWindow {
                background-color: #000000;
            }
            QMenuBar {
                background-color: #000000;
                color: #00FF00;
                border-bottom: 1px solid #003300;
            }
            QMenuBar::item:selected {
                background-color: #003300;
                color: #39FF14;
            }
            QMenu {
                background-color: #000000;
                color: #00FF00;
                border: 1px solid #00FF00;
            }
            QMenu::item:selected {
                background-color: #005500;
                color: #39FF14;
            }
            QTabWidget::pane {
                border-top: 1px solid #003300;
            }
            QTabBar::tab {
                background-color: #050505;
                color: #008800;
                padding: 8px 12px;
                border-right: 1px solid #003300;
            }
            QTabBar::tab:selected {
                background-color: #000000;
                color: #39FF14;
                border-bottom: 2px solid #39FF14;
            }
            QStatusBar {
                background-color: #000000;
                color: #39FF14;
                border-top: 1px solid #003300;
            }
        """)

        # Main splitter (Left Sidebar | Editor/Console | Right Chat Sidebar)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)

        # Left Sidebar (File Explorer)
        self.file_explorer = FileExplorer(self.workspace_path)
        self.file_explorer.file_double_clicked.connect(self.open_file)
        self.main_splitter.addWidget(self.file_explorer)

        # Middle Area (Splitter for Editor Tabs on top and Console on bottom)
        self.middle_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.middle_splitter.addWidget(self.tabs)

        self.console = ConsoleWidget(self.workspace_path)
        self.middle_splitter.addWidget(self.console)
        
        # Set initial sizes for middle vertical splitter (Editor: 600px, Console: 200px)
        self.middle_splitter.setSizes([600, 200])

        self.main_splitter.addWidget(self.middle_splitter)

        # Right Sidebar Tabs (Yapay Zeka & Planlama & YouTube & Ayarlar)
        self.right_tabs = QTabWidget()
        
        self.ollama_sidebar = OllamaSidebar()
        self.ollama_sidebar.send_prompt_signal.connect(self.start_ai_chat)
        self.ollama_sidebar.cancel_signal.connect(self.cancel_ai_chat)
        self.ollama_sidebar.quick_action_signal.connect(self.run_quick_action)
        self.ollama_sidebar.refresh_btn.clicked.connect(self.refresh_models)
        self.ollama_sidebar.insert_code_signal.connect(self.insert_ai_code)

        self.youtube_player = YoutubePlayerWidget()
        
        self.settings_panel = SettingsWidget()
        self.settings_panel.sound_toggled.connect(self.on_sound_toggled)
        self.settings_panel.volume_changed.connect(self.on_volume_changed)
        self.settings_panel.minimap_toggled.connect(self.on_minimap_toggled)

        self.planning_panel = PlanningWidget()
        self.planning_panel.approved.connect(self.execute_plan)
        self.planning_panel.rejected.connect(self.reject_plan)

        self.right_tabs.addTab(self.ollama_sidebar, "Yapay Zeka")
        self.right_tabs.addTab(self.planning_panel, "Planlama")
        self.right_tabs.addTab(self.youtube_player, "YouTube")
        self.right_tabs.addTab(self.settings_panel, "Ayarlar")

        self.main_splitter.addWidget(self.right_tabs)

        # Set default splitter ratios (Explorer: 200px, Middle: 700px, Chat: 300px)
        self.main_splitter.setSizes([200, 700, 300])

        # Active Ollama Worker
        self.ai_worker = None

        # Debounce timer for linter
        self.linter_timer = QTimer(self)
        self.linter_timer.setSingleShot(True)
        self.linter_timer.setInterval(500)
        self.linter_timer.timeout.connect(self.on_linter_timeout)
        self.pending_linter_editor = None

        # Real-time code streaming state variables
        self.streaming_file = None
        self.streaming_editor = None
        self.stream_buffer = ""

        # Build Menu & Status Bar
        self.create_menu()
        self.create_status_bar()

        # Load models
        self.refresh_models()

        # Open blank file on startup if nothing is open
        if self.tabs.count() == 0:
            self.new_file()

    def create_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Hazır")

    def create_menu(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("Dosya")
        
        new_act = QAction("Yeni Dosya", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self.new_file)
        file_menu.addAction(new_act)

        open_act = QAction("Dosya Aç...", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_act)

        open_folder_act = QAction("Klasör Aç...", self)
        open_folder_act.triggered.connect(self.open_folder_dialog)
        file_menu.addAction(open_folder_act)

        save_act = QAction("Kaydet", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self.save_file)
        file_menu.addAction(save_act)

        save_as_act = QAction("Farklı Kaydet...", self)
        save_as_act.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_act.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        close_act = QAction("Sekmeyi Kapat", self)
        close_act.setShortcut(QKeySequence.StandardKey.Close)
        close_act.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        file_menu.addAction(close_act)

        # Edit Menu
        edit_menu = menu_bar.addMenu("Düzen")
        
        undo_act = QAction("Geri Al", self)
        undo_act.setShortcut(QKeySequence.StandardKey.Undo)
        undo_act.triggered.connect(self.trigger_undo)
        edit_menu.addAction(undo_act)

        redo_act = QAction("Yinele", self)
        redo_act.setShortcut(QKeySequence.StandardKey.Redo)
        redo_act.triggered.connect(self.trigger_redo)
        edit_menu.addAction(redo_act)

        edit_menu.addSeparator()

        self.sound_act = QAction("Klavye Sesi", self, checkable=True)
        self.sound_act.setChecked(True)
        self.sound_act.triggered.connect(self.toggle_sound)
        edit_menu.addAction(self.sound_act)

        # AI Menu
        ai_menu = menu_bar.addMenu("Yapay Zeka")
        
        shortcut_act = QAction("Seçili Alanı Açıkla", self)
        shortcut_act.setShortcut("Ctrl+E")
        shortcut_act.triggered.connect(lambda: self.run_quick_action("explain", self.ollama_sidebar.model_combo.currentText()))
        ai_menu.addAction(shortcut_act)

        refactor_shortcut = QAction("Seçili Alanı Refaktör Et", self)
        refactor_shortcut.setShortcut("Ctrl+R")
        refactor_shortcut.triggered.connect(lambda: self.run_quick_action("refactor", self.ollama_sidebar.model_combo.currentText()))
        ai_menu.addAction(refactor_shortcut)

    # File actions
    def new_file(self):
        editor = CodeEditor()
        editor.textChanged.connect(lambda: self.trigger_linter_debounced(editor))
        editor.set_minimap_visible(self.settings_panel.minimap_check.isChecked())
        index = self.tabs.addTab(editor, "adsız.py")
        self.tabs.setCurrentIndex(index)
        self.open_files[index] = None

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", self.workspace_path, "Tüm Dosyalar (*)")
        if file_path:
            self.open_file(file_path)

    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Klasör Aç", self.workspace_path)
        if folder_path:
            self.workspace_path = folder_path
            self.file_explorer.set_workspace(folder_path)
            self.console.change_directory(folder_path)
            self.status.showMessage(f"Klasör Açıldı: {folder_path}", 4000)

    def open_file(self, file_path):
        # Check if already open
        for idx, path in self.open_files.items():
            if path == file_path:
                self.tabs.setCurrentIndex(idx)
                return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            editor = CodeEditor()
            editor.setPlainText(content)
            editor.textChanged.connect(lambda: self.trigger_linter_debounced(editor))
            editor.set_minimap_visible(self.settings_panel.minimap_check.isChecked())
            
            filename = os.path.basename(file_path)
            idx = self.tabs.addTab(editor, filename)
            self.tabs.setCurrentIndex(idx)
            self.open_files[idx] = file_path
            self.run_linter(editor)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı: {e}")

    def run_linter(self, editor):
        idx = self.tabs.indexOf(editor)
        if idx == -1:
            return
        file_path = self.open_files.get(idx)
        err_msg = editor.check_syntax(file_path)
        if err_msg:
            self.status.showMessage(err_msg)
        else:
            if self.tabs.currentWidget() == editor:
                self.status.showMessage("Hazır")

    def trigger_linter_debounced(self, editor):
        self.pending_linter_editor = editor
        self.linter_timer.start()

    def on_linter_timeout(self):
        if self.pending_linter_editor:
            self.run_linter(self.pending_linter_editor)

    def save_file(self):
        idx = self.tabs.currentIndex()
        if idx == -1:
            return
        
        file_path = self.open_files.get(idx)
        if not file_path:
            self.save_file_as()
        else:
            self.write_file_content(file_path, idx)

    def save_file_as(self):
        idx = self.tabs.currentIndex()
        if idx == -1:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Farklı Kaydet", self.workspace_path, "Python Dosyaları (*.py);;Tüm Dosyalar (*)")
        if file_path:
            self.open_files[idx] = file_path
            self.tabs.setTabText(idx, os.path.basename(file_path))
            self.write_file_content(file_path, idx)

    def write_file_content(self, file_path, idx):
        try:
            editor = self.tabs.widget(idx)
            if editor:
                content = editor.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status.showMessage(f"Kaydedildi: {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi: {e}")

    def close_tab(self, index):
        if index == -1:
            return
        self.tabs.removeTab(index)
        if index in self.open_files:
            del self.open_files[index]

    # Edit actions
    def trigger_undo(self):
        editor = self.tabs.currentWidget()
        if editor:
            editor.undo()

    def trigger_redo(self):
        editor = self.tabs.currentWidget()
        if editor:
            editor.redo()

    def toggle_sound(self, enabled):
        CodeEditor.sound_enabled = enabled
        self.settings_panel.sound_check.setChecked(enabled)
        if enabled:
            self.status.showMessage("Klavye sesleri açıldı.", 3000)
        else:
            self.status.showMessage("Klavye sesleri kapatıldı.", 3000)

    def speak(self, text):
        import subprocess
        import sys
        if sys.platform == "win32":
            escaped = text.replace('"', '\\"')
            ps_command = f'Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak("{escaped}")'
            subprocess.Popen(["powershell", "-Command", ps_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_sound_toggled(self, enabled):
        CodeEditor.sound_enabled = enabled
        self.sound_act.setChecked(enabled)
        if enabled:
            self.status.showMessage("Klavye sesleri açıldı.", 3000)
        else:
            self.status.showMessage("Klavye sesleri kapatıldı.", 3000)

    def on_volume_changed(self, val):
        CodeEditor.sound_volume = val / 100.0

    def on_minimap_toggled(self, visible):
        # Update all open editors
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if isinstance(editor, CodeEditor):
                editor.set_minimap_visible(visible)
        self.status.showMessage(f"Minimap {'gösteriliyor' if visible else 'gizlendi'}.", 3000)

    def on_tab_changed(self, index):
        pass

    # Ollama AI tasks
    def refresh_models(self):
        self.status.showMessage("Ollama modelleri yükleniyor...")
        models = get_local_models()
        self.ollama_sidebar.set_models(models)
        if models:
            self.status.showMessage(f"Modeller yüklendi. Toplam: {len(models)} model", 4000)
        else:
            self.status.showMessage("Lokalde çalışan Ollama bulunamadı veya model yüklü değil!", 5000)

    def get_workspace_files_list(self):
        if not self.workspace_path or not os.path.exists(self.workspace_path):
            return []
        files_list = []
        ignored = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache", ".idea", ".vscode"}
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in ignored]
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.workspace_path)
                files_list.append(rel_path.replace('\\', '/'))
        return files_list

    def start_ai_chat(self, model, prompt, context_code=""):
        if self.ai_worker and self.ai_worker.isRunning():
            return

        files = self.get_workspace_files_list()
        files_str = ", ".join(files) if files else "Çalışma alanı boş."

        # System message for file operations agentic control and planning
        system_prompt = f"""Sen kıdemli bir yazılım mimarı ve otonom bir yapay zeka ajanısın. Kullanıcının çalışma alanında dosya/klasör yönetebilirsin.
Mevcut Çalışma Alanındaki Dosyalar: [{files_str}]

### ÖNEMLİ KURALLAR VE PROTOKOLLER:
1. NPM VE PAKET YÖNETİMİ:
   - Herhangi bir paket yüklemeden (örn: `npm install`) önce dizinde 'package.json' olup olmadığını kontrol et. 
   - Eğer 'package.json' YOKSA, ilk adım olarak kesinlikle `[RUN_COMMAND: npm init -y]` çalıştırarak projeyi başlatmalısın!
2. TAILWIND CSS KURULUM REHBERİ:
   - Projeye Tailwind eklerken sırasıyla şu adımları plana eklemeli ve uygulamalısın:
     a) `npm init -y` (package.json yoksa)
     b) `npm install -D tailwindcss` (tailwindcss paketini yükler)
     c) `npx tailwindcss init` (tailwind.config.js ayar dosyasını oluşturur)
     d) tailwind.config.js dosyasındaki `content` dizisini HTML/JS dosyalarının yollarını arayacak şekilde güncelle (Örn: `content: ["./pages/**/*.html", "./*.html", "./js/**/*.js"]`).
     e) styles.css dosyasının en üstüne şu direktifleri yaz:
        @tailwind base;
        @tailwind components;
        @tailwind utilities;
     f) En son aşamada, bu direktifleri tarayıcının anlayacağı gerçek CSS koduna derlemek için şu build komutunu çalıştır:
        `[RUN_COMMAND: npx tailwindcss -i ./css/styles.css -o ./pages/styles.css]` (veya uygun girdi-çıktı yolları).
3. PLANLAMA KURALI:
   - Eğer kullanıcının talebi birden fazla adımlı veya karmaşıksa (örneğin birden fazla dosya oluşturma, yapısal değişiklik vb.), kod yazmaya başlamadan önce kullanıcıya [PROPOSE_PLAN] etiketiyle sarmalanmış bir JSON dizisi planı öner. 

Örnek Plan Formatı:
[PROPOSE_PLAN]
[
  {{"task": "İlk adım açıklaması"}},
  {{"task": "İkinci adım açıklaması"}}
]
[/PROPOSE_PLAN]

Kullanıcı onay verdikten sonra sırayla şu komutları kullanarak dosyaları ve terminali yönet:
1. Dosya oluşturmak/içerik yazmak için:
[CREATE_FILE: dosya_adi.py]
kodlar/içerik
[/CREATE_FILE]
2. Klasör oluşturmak için:
[CREATE_FOLDER: klasor_adi]
3. Dosya veya klasör silmek için:
[DELETE_FILE: dosya_adi.py]
4. Terminal komutu çalıştırmak için (paket kurmak, script çalıştırmak veya build almak için):
[RUN_COMMAND: komut]
5. KOD DOĞRULAMA KURALI: Yazdığın veya değiştirdiğin kodların derleme hatası içerip içermediğini kontrol etmek için mutlaka doğrulama komutu çalıştır. Örneğin Python dosyası yazdıysan [RUN_COMMAND: python -m py_compile dosya_adi.py] çalıştırarak hata kontrolü yap."""

        messages = [
            {"role": "user", "content": f"[SİSTEM TALİMATLARI - LÜTFEN BUNLARI OKU VE UYGULA]:\n{system_prompt}"},
            {"role": "assistant", "content": "Anlaşıldı. Bu kurallara ve dosya yapısına göre adımları ve planları otonom olarak yöneteceğim."}
        ]

        # Add recent conversation history (max last 6 messages) to prevent context window overflow
        history_limit = 6
        recent_history = self.ollama_sidebar.chat_history[-history_limit:] if self.ollama_sidebar.chat_history else []
        for sender, msg_text in recent_history:
            if sender == "Kullanıcı":
                messages.append({"role": "user", "content": msg_text})
            elif sender == "AI":
                messages.append({"role": "assistant", "content": msg_text})
        
        # Add basic context if code is selected
        editor = self.tabs.currentWidget()
        selected_text = editor.textCursor().selectedText().strip() if editor else ""
        
        final_prompt = prompt
        if selected_text:
            final_prompt = f"Seçili Kod:\n```python\n{selected_text}\n```\n\nSoru: {prompt}"
        elif editor:
            content = editor.toPlainText()
            lines = content.split('\n')
            if len(lines) > 300:
                cursor = editor.textCursor()
                curr_line = cursor.blockNumber()
                start_line = max(0, curr_line - 50)
                end_line = min(len(lines), curr_line + 50)
                chunk = "\n".join(lines[start_line:end_line])
                final_prompt = f"Bağlamsal Kod (Dosya çok büyük olduğu için sadece imleç etrafındaki 100 satır gönderiliyor):\n# ... [Dosya başı gizlendi] ...\n{chunk}\n# ... [Dosya sonu gizlendi] ...\n\nSoru: {prompt}"
            else:
                final_prompt = f"Tüm Dosya İçeriği:\n```python\n{content}\n```\n\nSoru: {prompt}"

        messages.append({"role": "user", "content": final_prompt})

        self.ollama_sidebar.send_btn.setEnabled(False)
        self.ollama_sidebar.stop_btn.setEnabled(True)
        self.status.showMessage("Ollama yanıt oluşturuyor...")

        self.streaming_file = None
        self.streaming_editor = None
        self.stream_buffer = ""

        self.ai_worker = OllamaChatWorker(model, messages)
        self.ai_worker.token_received.connect(self.ollama_sidebar.update_last_message)
        self.ai_worker.token_received.connect(self.on_ai_token_received)
        self.ai_worker.finished.connect(self.on_ai_finished)
        self.ai_worker.error_occurred.connect(self.on_ai_error)
        self.ai_worker.start()

    def cancel_ai_chat(self):
        if self.ai_worker:
            self.ai_worker.cancel()
            self.status.showMessage("İşlem kullanıcı tarafından iptal edildi.")

    def on_ai_token_received(self, token):
        self.stream_buffer += token
        
        if not self.streaming_file:
            import re
            # Look for [CREATE_FILE: filename]
            match = re.search(r"\[CREATE_FILE:\s*([^\s\]]+)\]", self.stream_buffer)
            if match:
                filename = match.group(1).strip()
                filename = filename.replace('`', '').replace('*', '')
                
                # Resolve path
                file_path = os.path.join(self.workspace_path, filename)
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                except Exception:
                    pass
                
                # Find if file is already open
                tab_idx = -1
                for idx, path in self.open_files.items():
                    if path == file_path:
                        tab_idx = idx
                        break
                
                if tab_idx != -1:
                    self.tabs.setCurrentIndex(tab_idx)
                    self.streaming_editor = self.tabs.widget(tab_idx)
                else:
                    self.streaming_editor = CodeEditor()
                    self.streaming_editor.textChanged.connect(lambda ed=self.streaming_editor: self.trigger_linter_debounced(ed))
                    self.streaming_editor.set_minimap_visible(self.settings_panel.minimap_check.isChecked())
                    new_idx = self.tabs.addTab(self.streaming_editor, os.path.basename(file_path))
                    self.tabs.setCurrentIndex(new_idx)
                    self.open_files[new_idx] = file_path
                
                self.streaming_editor.clear()
                self.streaming_file = file_path
                tag_start = self.stream_buffer.find(match.group(0))
                self.stream_buffer = self.stream_buffer[tag_start + len(match.group(0)):]
        
        if self.streaming_file and self.streaming_editor:
            if "[/CREATE_FILE]" in self.stream_buffer:
                parts = self.stream_buffer.split("[/CREATE_FILE]", 1)
                content_chunk = parts[0]
                
                # Clean code block indicators
                if content_chunk.startswith("```"):
                    lines = content_chunk.split('\n')
                    if lines and (lines[0].startswith("```") or not lines[0].strip()):
                        lines = lines[1:]
                    content_chunk = "\n".join(lines)
                if content_chunk.endswith("```"):
                    content_chunk = content_chunk[:-3]
                
                self.streaming_editor.insertPlainText(content_chunk)
                
                # Save the file to disk
                try:
                    with open(self.streaming_file, 'w', encoding='utf-8') as f:
                        f.write(self.streaming_editor.toPlainText())
                except Exception:
                    pass
                
                # Reset
                self.streaming_file = None
                self.streaming_editor = None
                self.stream_buffer = parts[1] if len(parts) > 1 else ""
            else:
                # Buffer last 20 characters to avoid outputting tags prematurely
                if len(self.stream_buffer) > 20:
                    to_write = self.stream_buffer[:-20]
                    self.stream_buffer = self.stream_buffer[-20:]
                    
                    if to_write.startswith("```"):
                        lines = to_write.split('\n')
                        if lines and (lines[0].startswith("```") or not lines[0].strip()):
                            lines = lines[1:]
                        to_write = "\n".join(lines)
                    
                    self.streaming_editor.insertPlainText(to_write)
                    self.streaming_editor.ensureCursorVisible()

    def on_ai_finished(self):
        self.ollama_sidebar.send_btn.setEnabled(True)
        self.ollama_sidebar.stop_btn.setEnabled(False)
        self.status.showMessage("Yapay zeka yanıtı tamamlandı.")

        # Extract and execute agentic commands from the latest chat history message
        if self.ollama_sidebar.chat_history:
            sender, text = self.ollama_sidebar.chat_history[-1]
            if sender == "AI":
                import re
                plan_match = re.search(r"\[PROPOSE_PLAN\]\s*(.*?)\s*\[/PROPOSE_PLAN\]", text, re.DOTALL)
                if plan_match:
                    plan_json_str = plan_match.group(1).strip()
                    try:
                        import json
                        steps = json.loads(plan_json_str)
                        for step in steps:
                            step['status'] = 'pending'
                        self.right_tabs.setCurrentIndex(1)  # Focus the "Planlama" tab
                        self.planning_panel.load_plan(steps)
                        self.ollama_sidebar.append_message("Sistem", "Yapay zeka bir uygulama planı önerdi! Lütfen 'Planlama' sekmesini kontrol edin.")
                        self.speak("Plan hazırlandı. Onayınız bekleniyor.")
                    except Exception as e:
                        self.ollama_sidebar.append_message("Sistem", f"Önerilen plan JSON formatı okunamadı: {e}")
                else:
                    self.parse_and_execute_ai_commands(text)

    def execute_plan(self, steps):
        self.active_plan = steps
        self.current_step_index = 0
        self.speak("Plan onaylandı. Adımlar yürütülüyor.")
        self.run_next_plan_step()

    def reject_plan(self):
        self.active_plan = []
        self.planning_panel.load_plan([])
        self.ollama_sidebar.append_message("Sistem", "Plan reddedildi.")
        self.status.showMessage("Plan kullanıcı tarafından reddedildi.", 4000)
        self.speak("Plan iptal edildi.")

    def run_next_plan_step(self):
        if not self.active_plan:
            return
            
        while self.current_step_index < len(self.active_plan):
            step = self.active_plan[self.current_step_index]
            if step.get('status', 'pending') == 'pending':
                step['status'] = 'running'
                self.planning_panel.load_plan(self.active_plan)
                
                task_desc = step.get('task', '')
                self.status.showMessage(f"Plan adımı yürütülüyor: {task_desc}")
                self.speak(f"{self.current_step_index + 1}. adım yürütülüyor.")
                
                # Send special instruction to AI for this step
                prompt = f"Planımızın şu adımını otonom olarak gerçekleştir (dosyaları/klasörleri oluştur): '{task_desc}'. Bu adımı tamamladıktan sonra başka bir açıklama yapmadan işlemi tamamla."
                self.start_ai_chat_for_step(prompt)
                return
            self.current_step_index += 1
            
        self.status.showMessage("Tüm plan adımları tamamlandı!", 5000)
        self.ollama_sidebar.append_message("Sistem", "Tüm plan adımları başarıyla tamamlandı! Bir sonraki aşama için yapay zeka yönlendiriliyor...")
        self.speak("Tüm adımlar başarıyla tamamlandı. Sonraki aşama başlatılıyor.")
        
        continuation_prompt = "Önceki hazırlık adımları başarıyla tamamlandı. Şimdi projenin ana hedefi olan sayfaları ve tasarımları oluşturma aşamasına geç. Gerekli dosyaları oluşturmak için yeni bir plan öner veya doğrudan dosyaları oluşturmaya baş."
        QTimer.singleShot(1000, lambda: self.start_ai_chat(self.ollama_sidebar.model_combo.currentText(), continuation_prompt))

    def start_ai_chat_for_step(self, prompt):
        if self.ai_worker and self.ai_worker.isRunning():
            return
            
        model = self.ollama_sidebar.model_combo.currentText()
        if not model:
            self.status.showMessage("Model seçilmedi, plan yürütülemedi.")
            return

        files = self.get_workspace_files_list()
        files_str = ", ".join(files) if files else "Çalışma alanı boş."

        messages = [
            {"role": "user", "content": f"[SİSTEM TALİMATI]: Sen plan adımlarını uygulayan kıdemli bir yazılım mimarı ve otonom etmen (agentic AI) asistanısın. Çalışma alanındaki dosyalar: [{files_str}]. NPM komutları çalıştırmadan önce package.json yoksa mutlaka 'npm init -y' yapmalısın. Kod yazdıktan veya değiştirdikten sonra derleme hatası kontrolü için mutlaka [RUN_COMMAND: python -m py_compile dosya.py] gibi doğrulama komutları çalıştırmalısın. Dosya oluşturmak/silmek için [CREATE_FILE], [CREATE_FOLDER], [DELETE_FILE] formatlarını; komut çalıştırmak için ise [RUN_COMMAND: komut] formatını kullanmalısın."},
            {"role": "assistant", "content": "Anlaşıldı. Verilen adım talimatını otonom olarak ve hata kontrolleriyle yerine getireceğim."},
            {"role": "user", "content": prompt}
        ]
        
        self.ollama_sidebar.send_btn.setEnabled(False)
        self.ollama_sidebar.stop_btn.setEnabled(True)
        
        self.streaming_file = None
        self.streaming_editor = None
        self.stream_buffer = ""

        self.ai_worker = OllamaChatWorker(model, messages)
        self.ai_worker.token_received.connect(self.ollama_sidebar.update_last_message)
        self.ai_worker.token_received.connect(self.on_ai_token_received)
        self.ai_worker.finished.connect(self.on_step_ai_finished)
        self.ai_worker.error_occurred.connect(self.on_step_ai_error)
        self.ai_worker.start()

    def on_step_ai_finished(self):
        self.ollama_sidebar.send_btn.setEnabled(True)
        self.ollama_sidebar.stop_btn.setEnabled(False)
        
        if self.ollama_sidebar.chat_history:
            sender, text = self.ollama_sidebar.chat_history[-1]
            if sender == "AI":
                self.parse_and_execute_ai_commands(text)
                
                if self.active_plan and self.current_step_index < len(self.active_plan):
                    self.active_plan[self.current_step_index]['status'] = 'completed'
                    
                self.run_next_plan_step()

    def on_step_ai_error(self, err_msg):
        self.ollama_sidebar.send_btn.setEnabled(True)
        self.ollama_sidebar.stop_btn.setEnabled(False)
        self.ollama_sidebar.append_message("Hata", f"Plan adımı çalıştırılırken hata: {err_msg}")
        self.speak("Hata oluştu, işlem durduruldu.")
        
        if self.active_plan and self.current_step_index < len(self.active_plan):
            self.active_plan[self.current_step_index]['status'] = 'failed'
            self.planning_panel.load_plan(self.active_plan)

    def insert_ai_code(self):
        editor = self.tabs.currentWidget()
        if editor:
            code = self.ollama_sidebar.get_last_code_block()
            if code:
                # Insert at cursor
                editor.textCursor().insertText(code)
                self.status.showMessage("Kod editöre aktarıldı.", 3000)

    def parse_and_execute_ai_commands(self, text):
        import re
        import shutil

        # 1. CREATE_FOLDER
        folders = re.findall(r"\[CREATE_FOLDER:\s*(.+?)\]", text)
        for folder in folders:
            folder = folder.strip()
            path = os.path.join(self.workspace_path, folder)
            try:
                os.makedirs(path, exist_ok=True)
                self.ollama_sidebar.append_message("Sistem", f"Klasör oluşturuldu: '{folder}'")
            except Exception as e:
                self.ollama_sidebar.append_message("Sistem", f"Klasör oluşturma hatası ('{folder}'): {e}")

        # 2. CREATE_FILE
        files = re.findall(r"\[CREATE_FILE:\s*(.+?)\]\n(.*?)\n\[/CREATE_FILE\]", text, re.DOTALL)
        for filename, content in files:
            filename = filename.strip()
            path = os.path.join(self.workspace_path, filename)
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                # Strip markdown code fences if AI wrapped the content in them
                clean_content = content.strip()
                if clean_content.startswith("```"):
                    newline_idx = clean_content.find("\n")
                    if newline_idx != -1:
                        clean_content = clean_content[newline_idx+1:]
                    else:
                        clean_content = clean_content[3:]
                if clean_content.endswith("```"):
                    clean_content = clean_content[:-3]
                clean_content = clean_content.strip()

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(clean_content)
                self.ollama_sidebar.append_message("Sistem", f"Dosya oluşturuldu: '{filename}'")
            except Exception as e:
                self.ollama_sidebar.append_message("Sistem", f"Dosya oluşturma hatası ('{filename}'): {e}")

        # 3. DELETE_FILE
        del_files = re.findall(r"\[DELETE_FILE:\s*(.+?)\]", text)
        for filename in del_files:
            filename = filename.strip()
            path = os.path.join(self.workspace_path, filename)
            try:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    self.ollama_sidebar.append_message("Sistem", f"Dosya/klasör silindi: '{filename}'")
                else:
                    self.ollama_sidebar.append_message("Sistem", f"Silinecek dosya bulunamadı: '{filename}'")
            except Exception as e:
                self.ollama_sidebar.append_message("Sistem", f"Silme hatası ('{filename}'): {e}")

        # 4. RUN_COMMAND (Confirming with user before running)
        commands = re.findall(r"\[RUN_COMMAND:\s*(.+?)\]", text)
        for cmd in commands:
            cmd = cmd.strip()
            reply = QMessageBox.question(
                self, "Komut Çalıştırma Onayı",
                f"Yapay zeka şu terminal komutunu çalıştırmak istiyor:\n\n{cmd}\n\nOnaylıyor musunuz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.console.run_command_programmatically(cmd)
                self.ollama_sidebar.append_message("Sistem", f"Komut çalıştırıldı: '{cmd}'")
            else:
                self.ollama_sidebar.append_message("Sistem", f"Komut kullanıcı tarafından reddedildi: '{cmd}'")

    def on_ai_error(self, err_msg):
        self.ollama_sidebar.send_btn.setEnabled(True)
        self.ollama_sidebar.stop_btn.setEnabled(False)
        self.ollama_sidebar.append_message("Hata", f"Ollama ile iletişim hatası: {err_msg}")
        self.status.showMessage("AI Hatası oluştu.")

    def run_quick_action(self, action_name, model):
        editor = self.tabs.currentWidget()
        if not editor:
            return
        
        selected_text = editor.textCursor().selectedText().strip()
        if not selected_text:
            QMessageBox.warning(self, "Uarı", "Lütfen önce kod editöründen bir kod bloğu seçin.")
            return

        if action_name == "explain":
            prompt = "Lütfen aşağıdaki kodu detaylıca ve Türkçe olarak açıkla."
        elif action_name == "refactor":
            prompt = "Lütfen aşağıdaki kodu en iyi pratikleri (best practices) kullanarak refaktör et, performansı ve okunabilirliği artır. Sadece kodu veya önerilerini açıkla."
        else:
            return

        self.ollama_sidebar.append_message("Kullanıcı", f"Hızlı Eylem ({action_name}): Seçili Kod üzerinde işlem yapılıyor...")
        self.start_ai_chat(model, prompt, selected_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Custom workspace argument if provided
    workspace = None
    if len(sys.argv) > 1:
        workspace = sys.argv[1]

    win = MainWindow(workspace)
    win.show()
    sys.exit(app.exec())
