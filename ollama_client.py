import sys
import ollama
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class OllamaChatWorker(QThread):
    token_received = pyqtSignal(str)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, model, messages):
        super().__init__()
        self.model = model
        self.messages = messages
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            client = ollama.Client()
            response = client.chat(
                model=self.model,
                messages=self.messages,
                stream=True
            )
            for chunk in response:
                if self._is_cancelled:
                    break
                content = chunk.get('message', {}).get('content', '')
                if content:
                    self.token_received.emit(content)
            self.finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

def get_local_models():
    """Returns a list of local Ollama model names, or empty if Ollama is not running."""
    try:
        client = ollama.Client()
        models_data = client.list()
        return [m['model'] for m in models_data.get('models', [])]
    except Exception:
        return []
