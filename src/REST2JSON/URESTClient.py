import httpx
from typing import Optional, Any
import copy

#TODO
#Потенциальная утечка данных - при подстановке параметров в URL нет экранирования
#Нет обработки редиректов - httpx по умолчанию следует редиректам, но это не контролируется
#Нет лимита на размер ответа
#Нет таймаута на чтение/подключение отдельно - только общий таймаут
#Логирование ошибок через print - лучше использовать logging


class ClientBase:
    """
    Базовый класс для HTTP клиента на основе httpx.
    Обеспечивает базовую функциональность для выполнения GET и POST запросов.
    Поддерживает контекстный менеджер для автоматического управления соединениями.
    """
    
    def __init__(
        self, 
        headers: dict,
        extra_headers: Optional[dict] = None,
        timeout: int = 3,
    ):
        """
        Инициализация базового HTTP клиента.
        
        Args:
            headers: Базовые заголовки для всех запросов
            extra_headers: Дополнительные заголовки, которые будут добавлены к базовым
            timeout: Таймаут запросов в секундах (по умолчанию 3 секунды)
        """
        self.headers = headers
        self.headers["Accept"] = "application/json"  # Устанавливаем Accept по умолчанию
        
        # Добавляем дополнительные заголовки, если они предоставлены
        if extra_headers:
            for key, value in extra_headers.items():
                self.headers[key] = value
        
        # Создаем HTTP клиент с заданными заголовками и таймаутом
        self._client = httpx.Client(headers=headers, timeout=timeout)

    def __enter__(self) -> "ClientBase":
        """
        Вход в контекстный менеджер.
        
        Returns:
            ClientBase: Экземпляр текущего клиента
        """
        return self

    def __exit__(self):
        """
        Выход из контекстного менеджера.
        Автоматически закрывает соединения при выходе из контекста.
        """
        self.close()

    def close(self):
        """
        Закрытие сетевых соединений.
        Освобождает ресурсы, связанные с HTTP клиентом.
        """
        self._client.close()

    def _get(self, url, data, headers=None, timeout=None):
        """
        Выполнение GET запроса.
        
        Args:
            url: URL для запроса
            data: Параметры запроса (будут переданы как query parameters)
            headers: Дополнительные заголовки для этого запроса (не используются в текущей реализации)
            timeout: Таймаут для этого запроса (не используется в текущей реализации)
            
        Returns:
            tuple: (response_json, response_headers) - JSON ответ и заголовки ответа
            
        Raises:
            httpx.HTTPStatusError: При HTTP ошибке (status code >= 400)
        """
        response = self._client.get(url, params=data)
        response.raise_for_status()  # Выбрасывает исключение при HTTP ошибке
        return response.json(), response.headers

    def _post(self, url, data, headers=None, timeout=None):
        """
        Выполнение POST запроса с JSON телом.
        
        Args:
            url: URL для запроса
            data: Данные для отправки (будут сериализованы в JSON)
            headers: Дополнительные заголовки для этого запроса (не используются в текущей реализации)
            timeout: Таймаут для этого запроса (не используется в текущей реализации)
            
        Returns:
            tuple: (response_json, response_headers) - JSON ответ и заголовки ответа
            
        Raises:
            httpx.HTTPStatusError: При HTTP ошибке (status code >= 400)
        """
        response = self._client.post(url, json=data)
        response.raise_for_status()  # Выбрасывает исключение при HTTP ошибке
        return response.json(), response.headers


class URESTClient:
    """
    Универсальный REST клиент для работы с API.
    """
    
    def __init__(self, config: Any, token: Optional[str] = None, base_url: Optional[str] = None, timeout=None):
        """
        Инициализация универсального REST клиента.
        
        Args:
            config: Конфигурация эндпоинта (содержит method, url, headers и т.д.)
            token: Токен аутентификации (строка или словарь с заголовками аутентификации)
            base_url: Базовый URL для относительных путей (опционально)
            timeout: Таймаут запросов в секундах (опционально)
        """
        self.config = copy.deepcopy(config)  # Глубокая копия для предотвращения случайных изменений
        self.token = token
        self.base_url = base_url
        self._client_instance = None  # Экземпляр клиента (ленивая инициализация)
        self.timeout = timeout
        self._client_owned = False  # Флаг, указывающий, создан ли клиент этим экземпляром

    def _prepare_headers(self):
        """
        Подготовка заголовков для HTTP запросов.
        Объединяет заголовки из конфигурации с заголовками аутентификации.
        
        Returns:
            dict: Словарь с финальными заголовками
        """
        headers = self.config.get('headers', {})
        if self.token:
            if isinstance(self.token, dict):
                headers.update(self.token)  # Объединяем заголовки токена с основными заголовками
        return headers

    def execute(self, data=None):
        """
        Выполнение HTTP запроса согласно конфигурации.
        
        Args:
            data: Данные для отправки (используются для подстановки в URL и как тело запроса)
            
        Returns:
            tuple: (response_content, response_headers) - содержимое ответа и заголовки
            
        Raises:
            ValueError: При неподдерживаемом HTTP методе
            Exception: Прокидывает исключения от методов _get/_post
        """
        data = data or {}  # Заменяем None на пустой словарь
        
        try:
            # Формируем полный URL с учетом base_url
            base = self.base_url or ''
            url_template = f"{base}{self.config.get('url', '')}"
            
            # Подставляем параметры в URL шаблон
            try:
                if isinstance(data, dict):
                    url = url_template.format(**data)
                else:  # Если передана строка (например, JSON)
                    import json
                    data_dict = json.loads(data)
                    url = url_template.format(data_dict)
            except KeyError:
                # Если подстановка не удалась, используем шаблон как есть
                url = url_template
            
            # Определяем HTTP метод
            method = self.config.get('method', 'GET').upper()
            
            # Выполняем соответствующий запрос
            #TODO перенести в инициализацию клиента
            if method == 'GET':
                return self.client._get(url, data)
            elif method == 'POST':
                return self.client._post(url, data)
            else:
                raise RuntimeError(f"spec_url, spec_fallback, method_override: метод {method} не поддерживается")
                
        except Exception as e:
            print(f"Ошибка при выполнении запроса: {e}")
            self.close()  # Закрываем клиент при ошибке
            raise

    @property
    def client(self):
        """
        Свойство для доступа к HTTP клиенту с ленивой инициализацией.
        Клиент создается только при первом обращении к этому свойству.
        
        Returns:
            ClientBase: Экземпляр базового HTTP клиента
        """
        if self._client_instance is None:
            self._client_instance = ClientBase(
                headers=self._prepare_headers(),
                timeout=self.timeout
            )
            self._client_owned = True  # Отмечаем, что клиент создан этим экземпляром
        return self._client_instance
    
    def close(self):
        """
        Закрытие HTTP клиента и освобождение ресурсов.
        Закрывает соединение только если клиент был создан этим экземпляром.
        """
        if self._client_instance and self._client_owned:
            self._client_instance.close()
            self._client_instance = None
            self._client_owned = False
    
    def __enter__(self):
        """
        Вход в контекстный менеджер.
        
        Returns:
            URESTClient: Экземпляр текущего клиента
        """
        return self
    
    def __exit__(self, *args):
        """
        Выход из контекстного менеджера.
        Автоматически закрывает клиент при выходе из контекста.
        
        Args:
            *args: Аргументы исключения (exc_type, exc_val, exc_tb)
        """
        self.close()
    
    def _post(self, url: str, data):
        """
        Выполнение POST запроса (обертка над client._post).
        
        Args:
            url: URL для запроса
            data: Данные для отправки
            
        Returns:
            tuple: (response_json, response_headers) или None если ответа нет
        """
        response = self.client._post(url=url, data=data)
        return response if response else None
    
    def _get(self, url: str, data):
        """
        Выполнение GET запроса (обертка над client._get).
        
        Args:
            url: URL для запроса
            data: Параметры запроса
            
        Returns:
            tuple: (response_json, response_headers) или None если ответа нет
        """
        response = self.client._get(url=url, data=data)
        return response if response else None