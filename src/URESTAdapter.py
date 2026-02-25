import json
import httpx
from typing import Optional, Any
import copy
from src.utils.loggerdec import log_this

class ClientBase:
    """Base class for API client"""

    def __init__(
        self, 
        headers: dict,
        secret: Optional[dict] = None,
        timeout: int = 3,
    ):
        self.headers = headers
        self.headers["Accept"] = "application/json"
        if secret:
            for key,value in secret.items():
                self.headers[key] = value

        self._client = httpx.Client(headers=headers, timeout=timeout)

    def __aenter__(self) -> "ClientBase":
        return self

    def __aexit__(self, exc_type, exc_value, traceback):
        return self.close()

    def close(self):
        """Close network connections"""
        self._client.aclose()

    def _get(self, url, data,headers = None,timeout = None):
        """GET request to Dadata API"""
        response = self._client.get(url, params=data)
        response.raise_for_status()
        return response.json()

    def _post(self, url, data,headers = None,timeout = None):
        """POST request to Dadata API"""
        response = self._client.post(url, json=data)
        response.raise_for_status()
        return response.json()

class URESTAdapter():
    
    def __init__(self, config: Any, token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Инициализация клиента API
        
        Args:
            config_file: Путь к файлу конфигурации endpoints
            tokens_file: Путь к файлу с токенами (опционально)
            base_url: Базовый URL для относительных путей (опционально)
        """
        self.config = copy.deepcopy(config)
        self.token = token
        self.base_url = base_url
        self.endpoints = {}
        self.tokens = {}
        self.client = None
        self.headers = {}

        # Загружаем конфигурацию
        self._load_configuration() 
        

    @log_this(log_args=False, log_result=False)
    def _load_configuration(self):
        """Загружает конфигурацию endpoints из файла"""
        self.endpoints = self.config
        if self.token:
            self.tokens = self.token
        self.headers = self.config.get('headers',{}) 

    
    '''
    @log_this(log_args=False, log_result=False)
    def _load_tokens(self):
        """Загружает токены из файла"""
        try:
            with open(self.tokens_file, 'r', encoding='utf-8') as f:
                tokens = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки токенов: {e}")
            tokens = {}
        return tokens
    '''

    # TODO 
    # проверка есть ли ключи словаря в спеке
    # Если required один то подставить его к списку значений
    # формировать data, формировать очередь единичных загрузок
    # Текущая реализация непотокобезопасна

    @log_this(log_args=False, log_result=False)
    def execute(self,data:Optional[dict] = None):
        method = self.config.get('method','GET') #GET - по умолчанию
        url = self.config.get('url','').format(**data)
        return self.make_request(url,method,**data)
        #возврат одного вызова


    def make_request(self,url, method, **kwargs):

        methods = {
        'GET': self._get,
        'POST': self._post
       # 'PUT': requests.put,
       # 'DELETE': requests.delete,
       # 'PATCH': requests.patch
    }
        if method.upper() not in methods:
            raise ValueError(f"Unsupported method: {method}")
    
        return methods[method.upper()](url, kwargs)

    def init_dataLoader(self,timeout=5):
        
        self.client = ClientBase(
            headers = self.headers,
            secret=self.token
        )
    
    def _post(self,url:str,data):
        
        response = self.client._post(url=url,data=data)
        return response if response else None
    
    def _get(self,url:str,data):
        
        response = self.client._get(url=url,data=data)
        return response if response else None