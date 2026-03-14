import sys
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, 
                             QTextEdit, QPushButton, QLabel, QMessageBox,
                             QListWidget, QListWidgetItem, QScrollArea, QWidget, QHBoxLayout)
import signal
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize

import argparse

from backends.notion import NotionBackend
from backends.local import LocalFileBackend
from backends.gkeep import GoogleKeepBackend
from backends.gtasks import GoogleTasksBackend

# Permitir que Ctrl+C funcione en la terminal
signal.signal(signal.SIGINT, signal.SIG_DFL)
from PyQt6.QtGui import QShortcut, QKeySequence

# Configuración de argumentos
parser = argparse.ArgumentParser(description="Quick Journal and Task GUI")
parser.add_argument("--journal", action="store_true", help="Save to journal")
parser.add_argument("--task", action="store_true", help="Save to tasks")
parser.add_argument("--view-tasks", action="store_true", help="View existing tasks")
args, unknown = parser.parse_known_args()

# Cargar variables de entorno
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

def get_absolute_path(relative_path):
    """Convierte una ruta relativa al proyecto en absoluta"""
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(BASE_DIR, relative_path)

def get_backends(mode):
    """Factory para obtener la lista de backends configurados"""
    backends_str = os.getenv(f"{mode.upper()}_BACKEND", "notion")
    names = [n.strip().lower() for n in backends_str.split(",") if n.strip()]
    
    providers = []
    for name in names:
        if name == "notion":
            providers.append(NotionBackend(
                token=os.getenv("NOTION_TOKEN"),
                diary_parent_id=os.getenv("PARENT_PAGE_ID"),
                tasks_page_id=os.getenv("TASKS_PAGE_ID")
            ))
        elif name == "local":
            dir_name = os.getenv("LOCAL_BACKEND_DIR", "notas_locales")
            providers.append(LocalFileBackend(directory=get_absolute_path(dir_name)))
        elif name == "gkeep":
            providers.append(GoogleKeepBackend(
                email=os.getenv("GOOGLE_KEEP_EMAIL"),
                master_token=os.getenv("GOOGLE_KEEP_MASTER_TOKEN"),
                password=os.getenv("GOOGLE_KEEP_PASSWORD"),
                list_name=os.getenv("GOOGLE_KEEP_LIST_NAME", "InboxTareas2")
            ))
        elif name == "gtasks":
            cred_path = os.getenv("GOOGLE_TASKS_CREDENTIALS", "credentials.json")
            providers.append(GoogleTasksBackend(
                credentials_path=get_absolute_path(cred_path),
                token_path=get_absolute_path("token.pickle"),
                list_name=os.getenv("GOOGLE_TASKS_LIST_NAME", "InboxTareas2")
            ))
    return providers

# Determine mode
if args.task:
    MODE = "tarea"
    UI_TITLE = "New Task"
    UI_LABEL = "What task do you want to record?"
    UI_COLOR = "#3498db" # Blue for tasks
else:
    MODE = "diario"
    UI_TITLE = "Quick Journal"
    UI_LABEL = "What's on your mind?"
    UI_COLOR = "#2ecc71" # Green for journal

CACHE_FILE = os.path.join(BASE_DIR, "offline_cache.json")

class BackendWorker(QThread):
    """Hilo para guardar datos en todos los backends configurados"""
    finished = pyqtSignal(bool, str)

    def __init__(self, backends, texto, timestamp, mode, priority=9):
        super().__init__()
        self.backends = backends
        self.texto = texto
        self.timestamp = timestamp
        self.mode = mode
        self.priority = priority

    def run(self):
        if not self.backends:
            self.finished.emit(False, f"Sin backends configurados para {self.mode}")
            return
        
        results = []
        all_success = True
        
        for b in self.backends:
            backend_name = b.__class__.__name__.replace("Backend", "")
            if b.save(self.texto, self.timestamp, self.mode, self.priority):
                results.append(f"✅ {backend_name}")
            else:
                all_success = False
                error_msg = b.get_error()
                results.append(f"❌ {backend_name}: {error_msg}")
        
        status_message = "\n".join(results)
        self.finished.emit(all_success, status_message)

class SyncWorker(QThread):
    """Hilo para sincronizar entradas offline"""
    finished = pyqtSignal(int, int) # éxitos, fallos

    def __init__(self, entries):
        super().__init__()
        self.entries = entries

    def run(self):
        exitos = 0
        fallos = 0
        
        # Mapeo de listas de backends
        backend_map = {
            "diario": get_backends("diario"),
            "tarea": get_backends("tarea")
        }

        for entry in self.entries:
            mode = entry.get("mode", "diario")
            backends = backend_map.get(mode, [])
            
            if not backends:
                fallos += 1
                continue

            # Para sincronización, consideramos éxito si se guarda en AL MENOS un backend
            # o podríamos ser estrictos. Usaremos éxito si todos guardan.
            all_ok = True
            print(f"DEBUG: Sincronizando entrada offline: {entry['texto']}")
            # Sincronizar todos los backends
            priority = entry.get("priority", 9)
            for b in backends:
                if not b.save(entry["texto"], entry["timestamp"], mode, priority):
                    all_ok = False
            
            if all_ok:
                exitos += 1
            else:
                fallos += 1
        
        self.finished.emit(exitos, fallos)


class TaskViewerDialog(QDialog):
    """Diálogo para visualizar las tareas actuales de Google Tasks"""
    def __init__(self, all_backends):
        super().__init__()
        # Filtrar solo backends que pueden tener tareas (o todos, ya que manejan update_task_status)
        self.all_backends = all_backends
        # Usamos el primero (preferiblemente GTasks) para la carga inicial de la lista
        self.primary_backend = next((b for b in all_backends if b.__class__.__name__ == "GoogleTasksBackend"), all_backends[0])
        self.pending_updates = {} # id -> (title, bool)
        self.sync_timer = QTimer()
        self.sync_timer.setSingleShot(True)
        self.sync_timer.timeout.connect(self.sync_pending_updates)
        self.init_ui()
        self.load_tasks()

    def init_ui(self):
        self.setWindowTitle("Google Tasks List")
        self.setMinimumSize(400, 500)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QLabel { color: #ecf0f1; font-weight: bold; font-size: 16px; margin-bottom: 10px; }
            QListWidget { 
                background-color: #1e1e1e; 
                color: #ecf0f1; 
                border: 1px solid #555; 
                border-radius: 4px;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #333; }
            QListWidget::item:selected { background-color: #3498db; color: white; }
            QPushButton { 
                background-color: #3498db; 
                color: white; 
                padding: 10px; 
                border-radius: 4px; 
                font-weight: bold;
                margin-top: 10px;
            }
        """)

        layout = QVBoxLayout()
        self.label = QLabel("Tus Tareas Pendientes")
        layout.addWidget(self.label)

        self.lbl_sync_status = QLabel("")
        self.lbl_sync_status.setStyleSheet("color: #3498db; font-size: 11px;")
        layout.addWidget(self.lbl_sync_status)

        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.list_widget)

        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.clicked.connect(self.load_tasks)
        layout.addWidget(self.btn_refresh)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("background-color: #7f8c8d;")
        layout.addWidget(self.btn_close)

        self.setLayout(layout)

    def load_tasks(self):
        # Asegurar que se guarden cambios antes de recargar
        self.sync_pending_updates()
        
        self.list_widget.blockSignals(True) # Evitar disparar eventos mientras cargamos
        self.list_widget.clear()
        self.label.setText("Cargando tareas...")
        
        tasks = self.primary_backend.list_tasks()
        
        if not tasks:
            if self.primary_backend.get_error():
                QMessageBox.warning(self, "Error", f"No se pudieron cargar las tareas: {self.primary_backend.get_error()}")
            else:
                QListWidgetItem("No hay tareas pendientes 🎉", self.list_widget)
        else:
            # Ordenar: primero pendientes (needsAction), luego completadas (completed)
            tasks.sort(key=lambda x: x['status'] == 'completed')
            
            for t in tasks:
                is_completed = t['status'] == 'completed'
                title = t['title']
                item_text = title
                if t['notes']:
                    item_text += f"\n   📝 {t['notes']}"
                
                item = QListWidgetItem(item_text)
                # Guardar ID y Título para sincronización multi-backend
                item.setData(Qt.ItemDataRole.UserRole, (t['id'], title))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if is_completed else Qt.CheckState.Unchecked)
                
                # Tachado si está completada
                if is_completed:
                    font = item.font()
                    font.setStrikeOut(True)
                    item.setFont(font)
                    item.setForeground(Qt.GlobalColor.gray)
                
                self.list_widget.addItem(item)
        
        self.label.setText("Tus Tareas Pendientes")
        self.list_widget.blockSignals(False)

    def on_item_changed(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, tuple):
            return
            
        task_id, title = data
        completed = item.checkState() == Qt.CheckState.Checked
        
        # Buffer de cambios (incluyendo título para otros backends)
        self.pending_updates[task_id] = (title, completed)
        
        # Feedback visual inmediato
        font = item.font()
        font.setStrikeOut(completed)
        item.setFont(font)
        item.setForeground(Qt.GlobalColor.gray if completed else Qt.GlobalColor.white)
        
        # Reiniciar timer de 10 segundos
        self.lbl_sync_status.setText("Guardando cambios en 10s...")
        self.lbl_sync_status.show()
        self.sync_timer.start(10000)

    def sync_pending_updates(self):
        if not self.pending_updates:
            return

        self.sync_timer.stop()
        self.lbl_sync_status.setText("Sincronizando con Google Tasks...")
        self.lbl_sync_status.setStyleSheet("color: #f39c12; font-size: 11px;")
        QApplication.processEvents() # Forzar actualización de UI

        items_to_sync = self.pending_updates.copy()
        self.pending_updates.clear()
        
        total_backends = len(self.all_backends)
        success_ops = 0
        total_ops = len(items_to_sync) * total_backends
        
        for tid, (title, done) in items_to_sync.items():
            for b in self.all_backends:
                if b.update_task_status(tid, title, done):
                    success_ops += 1
                else:
                    print(f"Error sincronizando {b.__class__.__name__} para '{title}': {b.get_error()}")
        
        if success_ops == total_ops:
            self.lbl_sync_status.setText(f"✓ Sincronizado en {total_backends} backends")
            self.lbl_sync_status.setStyleSheet("color: #2ecc71; font-size: 11px;")
        else:
            self.lbl_sync_status.setText(f"⚠ Sincronización parcial ({success_ops}/{total_ops})")
            self.lbl_sync_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
        
        # Ocultar después de un momento
        QTimer.singleShot(3000, self.lbl_sync_status.hide)

    def closeEvent(self, event):
        """Asegurar que se guarden cambios al cerrar"""
        self.sync_pending_updates()
        event.accept()


class DiarioDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.priority = 9 
        self.priority_buttons = {}
        self.init_ui()
        self.sincronizar_cache()

    def init_ui(self):
        self.setWindowTitle(UI_TITLE)
        self.setFixedWidth(400)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #2b2b2b;
                border: 2px solid {UI_COLOR};
                border-radius: 8px;
            }}
            QLabel {{
                color: #ecf0f1;
                font-size: 14px;
            }}
            QTextEdit {{
                background-color: #1e1e1e;
                color: #ecf0f1;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.label = QLabel(UI_LABEL)
        layout.addWidget(self.label)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Escribe aquí... (Ctrl+Enter para guardar, Esc para salir)")
        layout.addWidget(self.text_edit)

        self.shortcut_enter = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_enter.activated.connect(self.procesar_diario)
        
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self.close)

        # Atajos para prioridades Ctrl+1 a Ctrl+9
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda p=i: self.set_priority(p))

        # Selector de prioridad para tareas
        if MODE == "tarea":
            priority_layout = QHBoxLayout()
            priority_layout.setSpacing(5)
            priority_label = QLabel("Prioridad (Ctrl+1-9):")
            priority_label.setStyleSheet("font-size: 11px; color: #aaa;")
            priority_layout.addWidget(priority_label)
            
            for i in range(1, 10):
                btn = QPushButton(str(i))
                btn.setFixedSize(24, 24)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, p=i: self.set_priority(p))
                priority_layout.addWidget(btn)
                self.priority_buttons[i] = btn
                
            priority_layout.addStretch()
            layout.addLayout(priority_layout)
            self.update_priority_ui()

        self.btn_enviar = QPushButton(f"Guardar {MODE.capitalize()} (Ctrl+Enter)")
        self.btn_enviar.clicked.connect(self.procesar_diario)
        self.btn_enviar.setStyleSheet(f"""
            QPushButton {{
                background-color: {UI_COLOR}; 
                color: white; 
                font-weight: bold; 
                padding: 8px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {UI_COLOR};
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: #7f8c8d;
            }}
        """)
        layout.addWidget(self.btn_enviar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
        self.lbl_status.hide()
        layout.addWidget(self.lbl_status)

        self.setLayout(layout)
        self.text_edit.setFocus()

        # Botón extra si es modo tarea y hay GTasks
        if MODE == "tarea":
            self.all_task_backends = get_backends(MODE)
            if self.all_task_backends:
                self.btn_view_tasks = QPushButton("Ver Tareas Existentes")
                self.btn_view_tasks.setStyleSheet("""
                    QPushButton { 
                        background-color: transparent; 
                        color: #3498db; 
                        text-decoration: underline; 
                        border: none;
                        font-size: 11px;
                        margin-top: 5px;
                    }
                """)
                self.btn_view_tasks.clicked.connect(self.abrir_visor_tareas)
                layout.addWidget(self.btn_view_tasks)

    def abrir_visor_tareas(self):
        if hasattr(self, 'all_task_backends') and self.all_task_backends:
            viewer = TaskViewerDialog(self.all_task_backends)
            viewer.exec()

    def set_priority(self, p):
        self.priority = p
        self.update_priority_ui()

    def update_priority_ui(self):
        if MODE != "tarea": return
        for i, btn in self.priority_buttons.items():
            if i == self.priority:
                # Color según urgencia
                color = "#e74c3c" if i <= 3 else "#f1c40f" if i <= 6 else "#2ecc71"
                btn.setStyleSheet(f"background-color: {color}; color: black; font-weight: bold; border-radius: 12px; border: 1px solid white;")
            else:
                btn.setStyleSheet("background-color: #333; color: white; border-radius: 12px;")

    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_to_cache(self, texto, timestamp):
        entries = self.load_cache()
        entries.append({
            "texto": texto, 
            "timestamp": timestamp, 
            "mode": MODE,
            "priority": self.priority if MODE == "tarea" else 9
        })
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    def sincronizar_cache(self):
        entries = self.load_cache()
        if entries:
            self.lbl_status.setText(f"Sincronizando {len(entries)} notas pendientes...")
            self.lbl_status.setStyleSheet("color: #f39c12; font-size: 11px;")
            self.lbl_status.show()
            
            self.sync_worker = SyncWorker(entries)
            self.sync_worker.finished.connect(self.on_sync_finished)
            self.sync_worker.start()

    def on_sync_finished(self, exitos, fallos):
        if fallos == 0:
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE) 
            self.lbl_status.setText(f"✓ {exitos} notas sincronizadas.")
            self.lbl_status.setStyleSheet("color: #2ecc71; font-size: 11px;")
        else:
            self.lbl_status.setText(f"Sincronización incompleta. {fallos} fallos.")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")

    def procesar_diario(self):
        texto = self.text_edit.toPlainText().strip()
        if not texto:
            self.close()
            return
            
        timestamp = datetime.now().strftime('%H:%M')
        backends = get_backends(MODE)

        # Si no hay backends válidos, guardamos en caché
        if not backends:
            print(f"DEBUG: Guardando en caché (Falta config para {MODE})")
            self.save_to_cache(texto, timestamp)
            self.close()
            return

        self.btn_enviar.setEnabled(False)
        self.btn_enviar.setText("Guardando...")
        self.text_edit.setEnabled(False)
        self.lbl_status.hide()
        
        timestamp = datetime.now().strftime("%H:%M")
        
        self.worker = BackendWorker(get_backends(MODE), texto, timestamp, MODE, self.priority)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self, success, message):
        self.lbl_status.setText(message)
        self.lbl_status.show()
        
        if success:
            self.lbl_status.setStyleSheet("color: #2ecc71; font-size: 11px;")
            print(f"DEBUG: Envío exitoso ({MODE}). Cerrando en 2s...")
        else:
            # Falló algo pero mostramos el detalle
            self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
            print(f"DEBUG: Resultados con errores: {message}")

        # Cerrar automáticamente después de 2.5 segundos para que de tiempo a leer
        QTimer.singleShot(2500, self.close)

    def closeEvent(self, event):
        """Asegura que el proceso termine al cerrar la ventana"""
        print("DEBUG: Aplicación terminada.")
        QApplication.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if args.view_tasks:
        # Modo solo visualización de tareas
        task_backends = get_backends("tarea")
        if task_backends:
            viewer = TaskViewerDialog(task_backends)
            viewer.show()
            sys.exit(app.exec())
        else:
            print("Error: No hay backends de tareas configurados.")
            sys.exit(1)

    # Timer para permitir que Python procese señales (Ctrl+C) cada 500ms
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    
    window = DiarioDialog()
    window.show()
    sys.exit(app.exec())
