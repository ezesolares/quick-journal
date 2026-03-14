from abc import ABC, abstractmethod

class BaseBackend(ABC):
    @abstractmethod
    def save(self, text: str, timestamp: str, mode: str, priority: int = 9) -> bool:
        """
        Guarda el texto en el backend.
        mode: 'diario' o 'tarea'
        priority: 1 (máxima) a 9 (mínima/default)
        """
        pass

    @abstractmethod
    def get_error(self) -> str:
        """Retorna el último mensaje de error."""
        pass

    def update_task_status(self, task_id: str, title: str, completed: bool) -> bool:
        """
        Actualiza el estado de una tarea existente.
        Opcional para backends que no lo soporten.
        """
        return True
