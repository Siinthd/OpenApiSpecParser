import json
import httpx
from typing import Optional, Any
import copy
from .utils.loggerdec import log_this

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
        self._client.close()

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
        self._client_instance = None
        self.headers = {}

        self._client_owned = False 

    def _prepare_headers(self):
        headers = self.config.get('headers', {}).copy()
        
        if self.token:
            if isinstance(self.token, dict):
                headers.update(self.token)  
            elif isinstance(self.token, str):
                headers['Authorization'] = f"Bearer {self.token}"  
        
        return headers    


    
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

    def execute(self, data=None):
        data = data or {}  
        
        try:
            url_template = self.config.get('url', '')
            try:
                url = url_template.format(**data)
            except KeyError:
                url = url_template
            
            method = self.config.get('method', 'GET').upper()
            
            if method == 'GET':
                return self.client._get(url, data) 
            elif method == 'POST':
                return self.client._post(url, data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
        except Exception as e:
            print(f"Error in execute: {e}")
            self.close() 
            raise


    def make_request(self,url, method, data):

        methods = {
        'GET': self._get,
        'POST': self._post
       # 'PUT': requests.put,
       # 'DELETE': requests.delete,
       # 'PATCH': requests.patch
    }
        if method.upper() not in methods:
            raise ValueError(f"Unsupported method: {method}")
    
        return methods[method.upper()](url, data)
    
    @property
    def client(self):
        if self._client_instance is None:
            self._client_instance = ClientBase(
                headers=self._prepare_headers(),
                timeout=self.config.get('timeout', 3)
            )
            self._client_owned = True
        return self._client_instance
    
    def close(self):
        if self._client_instance and self._client_owned:
            self._client_instance.close()
            self._client_instance = None
            self._client_owned = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def _post(self,url:str,data):
        
        response = self.client._post(url=url,data=data)
        return response if response else None
    
    def _get(self,url:str,data):
        
        response = self.client._get(url=url,data=data)
        return response if response else None