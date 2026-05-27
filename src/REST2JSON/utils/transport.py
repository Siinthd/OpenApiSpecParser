from abc import ABC, abstractmethod

class TransportInterface(ABC):
    @abstractmethod
    def request(self, method, url, **kwargs):
        """Выполнить HTTP-запрос и вернуть часть данных."""
        ...
    
    @abstractmethod
    def get_header(self):
        """Вернуть заголовки последнего ответа."""
        ...
    
    @abstractmethod
    def __enter__(self):
        ...
    
    @abstractmethod
    def __exit__(self, *args):
        ...