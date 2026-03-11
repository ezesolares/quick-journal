import requests
from datetime import datetime
from .base import BaseBackend

class NotionBackend(BaseBackend):
    def __init__(self, token, diary_parent_id, tasks_page_id):
        self.token = token
        self.diary_parent_id = diary_parent_id
        self.tasks_page_id = tasks_page_id
        self.last_error = ""

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def get_error(self) -> str:
        return self.last_error

    def buscar_pagina_hoy(self, parent_id):
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        url = f"https://api.notion.com/v1/blocks/{parent_id}/children"
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=5)
            if response.status_code == 200:
                items = response.json().get("results", [])
                for item in items:
                    if item["type"] == "child_page" and fecha_hoy in item["child_page"]["title"]:
                        return item["id"]
        except Exception as e:
            self.last_error = str(e)
        return None

    def crear_nueva_pagina(self, parent_id, mode, text, timestamp):
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        url = "https://api.notion.com/v1/pages"
        title_prefix = "Diario" if mode == "diario" else "Tareas"
        
        payload = {
            "parent": { "page_id": parent_id },
            "properties": {
                "title": { "title": [{ "text": { "content": f"{title_prefix} {fecha_hoy}" } }] }
            },
            "children": self._format_blocks(text, timestamp, mode)
        }
        return requests.post(url, json=payload, headers=self.get_headers(), timeout=5)

    def añadir_bloques(self, page_id, text, timestamp, mode):
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        payload = { "children": self._format_blocks(text, timestamp, mode) }
        return requests.patch(url, json=payload, headers=self.get_headers(), timeout=5)

    def _format_blocks(self, text, timestamp, mode):
        blocks = []
        if mode == "tarea":
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            lineas = [l.strip() for l in text.split('\n') if l.strip()]
            for linea in lineas:
                content = f"{fecha_hoy} - {timestamp} - {linea}"
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{ "type": "text", "text": { "content": content } }],
                        "checked": False
                    }
                })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{ "type": "text", "text": { "content": f"[{timestamp}] {text}" } }]
                }
            })
        return blocks

    def save(self, text: str, timestamp: str, mode: str) -> bool:
        try:
            if mode == "tarea":
                if not self.tasks_page_id:
                    self.last_error = "ID de tareas no configurado"
                    return False
                res = self.añadir_bloques(self.tasks_page_id, text, timestamp, mode)
            else:
                if not self.diary_parent_id:
                    self.last_error = "ID de diario no configurado"
                    return False
                page_id = self.buscar_pagina_hoy(self.diary_parent_id)
                if page_id:
                    res = self.añadir_bloques(page_id, text, timestamp, mode)
                else:
                    res = self.crear_nueva_pagina(self.diary_parent_id, mode, text, timestamp)

            if res.status_code in [200, 201]:
                return True
            else:
                self.last_error = f"Notion Error {res.status_code}: {res.text}"
                return False
        except Exception as e:
            self.last_error = str(e)
            return False
