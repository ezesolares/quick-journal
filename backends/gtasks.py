import os.path
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .base import BaseBackend

class GoogleTasksBackend(BaseBackend):
    # If modifying these SCOPES, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/tasks']

    def __init__(self, credentials_path="credentials.json", token_path="token.pickle"):
        self.credentials_path = credentials_path
        self.token_path = token_path
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

    def get_error(self) -> str:
        return self.last_error

    def save(self, text: str, timestamp: str, mode: str) -> bool:
        if mode != "tarea":
            return True
            
        service = self._get_service()
        if not service:
            return False
            
        try:
            # Buscar la lista correcta
            target_list_name = self.list_name 
            tasklists = service.tasklists().list().execute().get('items', [])
            
            list_id = "@default" # Fallback
            for tl in tasklists:
                if tl['title'] == target_list_name:
                    list_id = tl['id']
                    break
            
            # Si no existe, podrías crearla o usar @default. 
            # Por ahora seguiremos el patrón de buscarla.

            lineas = [l.strip() for l in text.split('\n') if l.strip()]
            for linea in lineas:
                task = {
                    'title': f"{linea}",
                    'notes': f"Anotado vía OpenDeck Journal el {timestamp}"
                }
                service.tasks().insert(tasklist=list_id, body=task).execute()
            return True
        except Exception as e:
            self.last_error = f"GTasks Save Error: {str(e)}"
            return False
