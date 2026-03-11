from abc import ABC, abstractmethod

class BaseBackend(ABC):
    @abstractmethod
    def save(self, text: str, timestamp: str, mode: str) -> bool:
        """
        Guarda la entrada en el backend.
        :param text: Contenido del texto.
        :param timestamp: Marca de tiempo format HH:MM.
        :param mode: 'diario' o 'tarea'.
        :return: True si fue exitoso, False de lo contrario.
        """
        pass

    @abstractmethod
    def get_error(self) -> str:
        """Retorna el último mensaje de error."""
        pass
