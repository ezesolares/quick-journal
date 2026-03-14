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

    def save(self, text: str, timestamp: str, mode: str, priority: int = 9) -> bool:
        try:
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            filename = f"{mode}_{fecha_hoy}.txt"
            path = os.path.join(self.directory, filename)
            
            with open(path, "a", encoding="utf-8") as f:
                if mode == "tarea":
                    lineas = [l.strip() for l in text.split('\n') if l.strip()]
                    for linea in lineas:
                        f.write(f"[ ] {fecha_hoy} - {timestamp} - {linea} (IMP: {priority})\n")
                else:
                    f.write(f"[{timestamp}] {text}\n")
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    def update_task_status(self, task_id: str, title: str, completed: bool) -> bool:
        """Actualiza el estado de la tarea en los archivos locales buscando por texto"""
        try:
            # Buscar en todos los archivos del directorio de notas
            for root, _, files in os.walk(self.directory):
                for file in files:
                    if not file.endswith(".txt"): continue
                    
                    path = os.path.join(root, file)
                    updated = False
                    new_lines = []
                    
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        
                    for line in lines:
                        # Si la línea contiene el título de la tarea
                        if title in line:
                            current_state = "[ ]" if not completed else "[x]"
                            old_state = "[x]" if not completed else "[ ]"
                            if old_state in line:
                                line = line.replace(old_state, current_state)
                                updated = True
                        new_lines.append(line)
                    
                    if updated:
                        with open(path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
            return True
        except Exception as e:
            self.last_error = f"Local Update error: {str(e)}"
            return False
