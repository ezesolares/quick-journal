import os
from datetime import datetime
from .base import BaseBackend

class LocalFileBackend(BaseBackend):
    def __init__(self, directory="notes"):
        self.directory = directory
        self.last_error = ""
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

    def get_error(self) -> str:
        return self.last_error

    def save(self, text: str, timestamp: str, mode: str) -> bool:
        try:
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            filename = f"{mode}_{fecha_hoy}.txt"
            path = os.path.join(self.directory, filename)
            
            with open(path, "a", encoding="utf-8") as f:
                if mode == "tarea":
                    lineas = [l.strip() for l in text.split('\n') if l.strip()]
                    for linea in lineas:
                        f.write(f"[ ] {fecha_hoy} - {timestamp} - {linea}\n")
                else:
                    f.write(f"[{timestamp}] {text}\n")
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
