import json
import httpx
from typing import Optional, Dict, Any
import copy
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
    
    def __init__(self, config: Any, tokens_file: Optional[str] = None, base_url: Optional[str] = None):
        """
        Инициализация клиента API
        
        Args:
            config_file: Путь к файлу конфигурации endpoints
            tokens_file: Путь к файлу с токенами (опционально)
            base_url: Базовый URL для относительных путей (опционально)
        """
        self.config = copy.deepcopy(config)
        self.tokens_file = tokens_file
        self.base_url = base_url
        self.endpoints = {}
        self.tokens = {}
        self.client = None

        # Загружаем конфигурацию
        self._load_configuration() 

    def _load_configuration(self):
        """Загружает конфигурацию endpoints из файла"""
        self.endpoints = self.config
        if self.tokens_file:
            self.tokens = self._load_tokens()
    
    def _load_tokens(self):
        """Загружает токены из файла"""
        try:
            with open(self.tokens_file, 'r', encoding='utf-8') as f:
                tokens = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки токенов: {e}")
            tokens = {}
        return tokens

    # TODO 
    # проверка есть ли ключи словаря в спеке
    # Если required один то подставить его к списку значений
    # формировать data, формировать очередь единичных загрузок
    # Текущая реализация непотокобезопасна


    def execute(self, data:Optional[dict] = None):
        #работаем со входными переменными
        payload = []
        pagination = False
        entity = self.endpoints
        required = entity.get('required',[])
        variables = entity.get('variables',[])
        datatype =  type(data)
        if datatype == dict:
            entity_variables = entity.get('variables',None)
            keys = data.keys()
            if set(entity_variables) & set(keys):
                print('переменная(ые) есть в списке')
            payload = [data]
        elif datatype == list:
            if  all(isinstance(item, dict) for item in data): #проверяем что это не список словарей
                payload = data
            else:
                if len(required) == 1:
                        payload = [{required[0]: value} for value in data]    
                else:
                    print('Требуется явно указать параметр(ы) запроса')
        elif data:
            payload = [{required[0]: value} for value in [data]]

        #собираем хидор
        method = entity.get('method','GET') #GET - по умолчанию
        headers = entity.get('headers',{}) 
        url = entity.get('url','') 
        
        entity_name = entity
        #TODO
        # Ищем параметры с Page,они не всегда обязательные

        page = list(set(required+variables))
        if 'Page'.upper() in [i.upper() for i in page]:
            pagination = True
            page = 1
            

        #Инициализация движка
        self.init_dataLoader(header=headers,secret = self.tokens[entity.get('operationalId')])
        result = []

        for i in payload:
            try:
                    url = url.format(**i)
                    _dbg = self.make_request(url,method,**i)
                    empty_dict = True
                    if isinstance(_dbg,dict):
                        for value in _dbg.values():
                            if not value:  
                                    empty_dict =  True
                            else:
                                empty_dict = False
                        if not empty_dict:
                            result.append(_dbg)
                    else:
                        result.append(_dbg)

            except Exception as e: 
                print(f'Загрузка остановлена по причине: {e}')

        return result

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

    def init_dataLoader(self,header:dict,secret:dict,timeout=5):
        self.client = ClientBase(
            headers = header,
            secret=secret
        )
    
    def _post(self,url:str,data):
        
        response = self.client._post(url=url,data=data)
        return response if response else None
    
    def _get(self,url:str,data):
        
        response = self.client._get(url=url,data=data)
        return response if response else None
    



if __name__ == "__main__":

    from utils.api_reader import OASParser

    parser = OASParser('C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/accuweather.yaml')

    entity  = parser.request.get('getCurrentConditions')
  

    with open("C:/Users/kdenis/mu_code/conf.json", "w", encoding="utf-8") as f:
        json.dump(entity, f, indent=4, ensure_ascii=False)

    '''
    suggestions.yml
    ex3.yaml
    Untitled-2.json
    pagi.yaml
    ex4.yaml
    ex4.yaml
    '''

    test = URESTAdapter(entity,'C:/Users/kdenis/mu_code/keys.json')


        #dict1 = {'query':'ITRORU8YXXX'}
    input_data = {'lat':'50','lon':'50'}
    input_data = [666,777,888,999,1111,2222,3333]
    #input_data = {'q':'RUSSIA'}
    swift_codes = [
    'SABRRUMM', 'VTBRRUMM', 'GAZPRUMM', 'ALFARUMM', 'MOSCRUMM',
    'RSBNRUMM', 'RUWCRUMM', 'ICBKRUMM', 'KOSKRUMM', 'PARNRUMM',
    'ABNYRUMM', 'CRYPRUMM', 'TICSRUMM', 'PSBZRUMM', 'TKRBRUMM',
    'JSNMRUMM', 'MIRBRUMM', 'ELSRUMMXXX', 'RNGBRUMM', 'IRONRUMM',
    'AVJSRUMM', 'ARESRUMM', 'ALILRUMM', 'ITRORU8Y', 'BOCSRUMM',
    'DOMRRUMM', 'FORTRUMM', 'GLBKRUMM', 'HDCBRUMM', 'KBKTRUMM',
    'KREMRUMM', 'LBRURUMM', 'MDMBRUMM', 'MEZHRUMM', 'MOPARUMM',
    'OLMDRUMM', 'ROYCRUMM', 'RZCBRUMM', 'SBERRUMM', 'SGBZRUMM',
    'SLAVRUMM', 'SOGZRUMM', 'TATKRUMM', 'TKBKRUMM', 'TKZLRUMM',
    'TKZVRUMM', 'TRNVRUMM', 'VEFKRUMM', 'VTBKRUMM', 'ZENIRUMM'
]
    
    result = test.execute(input_data)
    with open("C:/Users/kdenis/mu_code/answer.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
                
    print(result)

