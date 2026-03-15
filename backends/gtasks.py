import os.path
import pickle
from datetime import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .base import BaseBackend

class GoogleTasksBackend(BaseBackend):
    # If modifying these SCOPES, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/tasks']

    def __init__(self, credentials_path="credentials.json", token_path="token.pickle", list_name="InboxTareas2"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.list_name = list_name
        self.service = None
        self.last_error = ""

    def _get_service(self):
        if self.service:
            return self.service
            
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    self.last_error = f"Falta {self.credentials_path}. Descárgalo de Google Cloud Console."
                    return None
                
                # Flow para autenticación interactiva (abrirá el navegador)
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        try:
            self.service = build('tasks', 'v1', credentials=creds)
            return self.service
        except Exception as e:
            self.last_error = f"GTasks build error: {str(e)}"
            return None

    def list_tasks(self) -> list:
        """Retorna una lista de tareas desde Google Tasks"""
        service = self._get_service()
        if not service:
            return []
            
        try:
            # Buscar la lista correcta
            tasklists = service.tasklists().list().execute().get('items', [])
            list_id = "@default"
            for tl in tasklists:
                if tl['title'] == self.list_name:
                    list_id = tl['id']
                    break
            
            results = service.tasks().list(tasklist=list_id, showHidden=False).execute()
            items = results.get('items', [])
            
            # Formatear para facilitar la visualización
            tasks = []
            for item in items:
                tasks.append({
                    'id': item['id'],
                    'title': item['title'],
                    'status': item.get('status', 'needsAction'),
                    'notes': item.get('notes', '')
                })
            return tasks
        except Exception as e:
            self.last_error = f"GTasks List error: {str(e)}"
            return []

    def update_task_status(self, task_id: str, title: str, completed: bool) -> bool:
        """Actualiza el estado de una tarea (completada o pendiente)"""
        service = self._get_service()
        if not service:
            return False
            
        try:
            # Google Tasks usa 'completed' o 'needsAction'
            status = 'completed' if completed else 'needsAction'
            
            # Buscamos la lista por defecto o la configurada
            # Para simplificar y ahorrar cuota, usamos '@default' si no guardamos el list_id
            # pero dado que el usuario puede tener varias, lo ideal es buscarla.
            tasklists = service.tasklists().list().execute().get('items', [])
            list_id = "@default"
            for tl in tasklists:
                if tl['title'] == self.list_name:
                    list_id = tl['id']
                    break

            # Patch para actualizar solo el estado
            body = {'status': status}
            # Si se marca como completada, Google a veces requiere borrar la fecha de completado si se vuelve a pendiente
            # pero con 'status' suele bastar.
            service.tasks().patch(tasklist=list_id, task=task_id, body=body).execute()
            return True
        except Exception as e:
            self.last_error = f"GTasks Update error: {str(e)}"
            return False

    def get_error(self) -> str:
        return self.last_error

    def _get_list_id(self, service):
        """Helper para obtener el ID de la lista por nombre"""
        try:
            tasklists = service.tasklists().list().execute().get('items', [])
            for tl in tasklists:
                if tl['title'] == self.list_name:
                    return tl['id']
            return "@default"
        except Exception:
            return "@default"

    def save(self, text: str, timestamp: str, mode: str, priority: int = 9) -> bool:
        if mode != "tarea":
            return True
            
        service = self._get_service()
        if not service:
            return False
            
        try:
            # Buscar lista
            list_id = self._get_list_id(service)
            
            # Formatos de fecha y hora para la nota
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            notes = f"IMP: {priority}\nFecha: {fecha_hoy}\nHora: {timestamp}"
            
            # Crear tareas (una por línea)
            lineas = [l.strip() for l in text.split('\n') if l.strip()]
            for linea in lineas:
                task = {
                    'title': linea,
                    'notes': notes
                }
                service.tasks().insert(tasklist=list_id, body=task).execute()
            
            return True
        except Exception as e:
            self.last_error = f"GTasks Save Error: {str(e)}"
            return False
