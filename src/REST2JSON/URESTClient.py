import httpx
from typing import Optional, Any
import copy

class ClientBase:
    """Base class for API client"""

    def __init__(
        self, 
        headers: dict,
        extra_headers: Optional[dict] = None,
        timeout: int = 3,
    ):
        self.headers = headers
        self.headers["Accept"] = "application/json" #default
        if extra_headers:
            for key,value in extra_headers.items():
                self.headers[key] = value
        self._client = httpx.Client(headers=headers, timeout=timeout)

    def __enter__(self) -> "ClientBase":
        return self

    def __exit__(self):
        self.close()

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

class URESTClient():
    
    def __init__(self, config: Any, token: Optional[str] = None, base_url: Optional[str] = None,timeout = None):
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
        self._client_instance = None
        self.timeout = timeout
        self._client_owned = False 

    def _prepare_headers(self):
        headers = self.config.get('headers', {})
        if self.token:
            if isinstance(self.token, dict):
                headers.update(self.token)  
        return headers    


    def execute(self, data=None):
        data = data or {}  
        
        try:
            base = self.base_url or ''
            url_template = f"{base}{self.config.get('url', '')}"
            try:
                if isinstance(data, dict): 
                    url = url_template.format(**data)
                else: #просочилась строка
                    import json
                    data_dict = json.loads(data)
                    url = url_template.format(data_dict)
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
            #print(f"Error in execute: {e}")
            self.close() 
            raise

    
    @property
    def client(self):
        if self._client_instance is None:
            self._client_instance = ClientBase(
                headers=self._prepare_headers(),
                timeout=self.timeout
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