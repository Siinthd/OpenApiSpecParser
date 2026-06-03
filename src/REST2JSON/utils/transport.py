from abc import ABC, abstractmethod
import requests


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


class HTTPTransport(TransportInterface):
    def __init__(self, timeout=30, verify=True, stream=True):
        self._timeout = timeout
        self._verify = verify
        self._stream = stream
        self._session = None
        self._header = None
        self._active = False
        self._current_response = None

    def request(self, method, url, **kwargs):
        if not self._active:
            raise RuntimeError(...)
        if self._session is None:
            self._session = requests.Session()
        if self._current_response is not None:
            self._current_response.close()
        kwargs.setdefault('timeout', self._timeout)
        kwargs.setdefault('verify', self._verify)
        kwargs.setdefault('stream', self._stream)
        raw = self._session.request(method, url, **kwargs)
        self._current_response = raw
        # Прямой доступ к неизмененным заголовкам сокета urllib3
        #TODO можно вызывать обращаясь напрямую к raw.headers но после получения всех чанков
        self._header = raw.raw.headers
        return raw

    def get_header(self):
        return self._header

    def __enter__(self):
        self._active = True
        return self

    def __exit__(self, *args):
        self._active = False
        if self._current_response:
            self._current_response.close()
        if self._session:
            self._session.close()
            self._session = None
        return False