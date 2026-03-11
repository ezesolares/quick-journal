import gkeepapi
from .base import BaseBackend
from datetime import datetime

class GoogleKeepBackend(BaseBackend):
    def __init__(self, email, master_token=None, password=None, list_name="InboxTareas2"):
        self.email = email
        self.master_token = master_token
        self.password = password
        self.list_name = list_name
        self.keep = gkeepapi.Keep()
        self.last_error = ""
        self.is_logged_in = False

    def _login(self):
        if self.is_logged_in:
            return True
        try:
            if self.master_token:
                # Intentar autenticar con token maestro
                self.keep.authenticate(self.email, self.master_token)
            elif self.password:
                # Autenticar con App Password
                self.keep.login(self.email, self.password)
            else:
                self.last_error = "Falta GOOGLE_KEEP_MASTER_TOKEN o GOOGLE_KEEP_PASSWORD en el .env"
                return False
                
            self.is_logged_in = True
            return True
        except Exception as e:
            self.last_error = f"GKeep Auth Error: {str(e)}"
            return False

    def get_error(self) -> str:
        return self.last_error

    def save(self, text: str, timestamp: str, mode: str) -> bool:
        if not self._login():
            return False
            
        try:
            if mode == "tarea":
                # Buscar o crear lista de tareas
                list_name = self.list_name
                glist = None
                for node in self.keep.find(func=lambda x: isinstance(x, gkeepapi.node.List) and x.title == list_name):
                    glist = node
                    break
                
                if not glist:
                    glist = self.keep.createList(list_name)
                
                lineas = [l.strip() for l in text.split('\n') if l.strip()]
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                for linea in lineas:
                    glist.add(f"{fecha_hoy} {timestamp}: {linea}", False)
            else:
                # Buscar o crear nota de diario (agrupada por año para no saturar)
                year = datetime.now().strftime("%Y")
                title = f"Diario {year}"
                gnote = None
                for node in self.keep.find(func=lambda x: isinstance(x, gkeepapi.node.TopLevelNode) and x.title == title):
                    gnote = node
                    break
                
                if not gnote:
                    gnote = self.keep.createNote(title, "")
                
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                new_text = f"\n\n--- {fecha_hoy} {timestamp} ---\n{text}"
                gnote.text += new_text
            
            self.keep.sync()
            return True
        except Exception as e:
            self.last_error = f"GKeep Save Error: {str(e)}"
            return False
