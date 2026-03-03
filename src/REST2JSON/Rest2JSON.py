#Объединяет класс парсера и класс клиента

#на вход получает конфигурацию - разбивает ее,выбирает стратегию,по возможности - внешняя оценка результата для контроля загрузки
from omegaconf import DictConfig, OmegaConf
from .utils.OASParser import OASParser
from .URESTAdapter import URESTAdapter

class ParserAdapter(OASParser):
    def __init__(self,OpName,endpoint_url,method,spec):
        self._parser = None
        self.spec = spec
        self.OpName = OpName
        self.endpoint_url = endpoint_url
        self.method = method
    
    def get_parser(self): 
        if self._parser is None:
            self._parser = OASParser(self.OpName,self.endpoint_url,self.method,self.spec)
        return self._parser

class ClientAdapter(URESTAdapter):
    def __init__(self, entity,secret,base_url):
        super().__init__(entity, secret,base_url)
    
    def get_client(self):
        return self
    

    # TODO 
    # проверка есть ли ключи словаря в спеке
    # Если required один то подставить его к списку значений
    # формировать data, формировать очередь единичных загрузок
    # Текущая реализация непотокобезопасна

class REST2JSON:
    def __init__(self,
                Omegaconfig_stream: DictConfig = None):
        #Загружаем объект DictConfig
        self.Omegaconfig_stream = Omegaconfig_stream
        self.OpenAPISpecYAMLFilename,self.OpenAPISpecYAMLURL,self.TokensFilename,self.OpName,self.endpoint_url,self.method = self.__load_configuration(Omegaconfig_stream)
        #Получаем спецификацию
        self.spec = self._load_specification_(self.OpenAPISpecYAMLFilename,self.OpenAPISpecYAMLURL)
        #Загрузка адаптера
        self.parser_adapter = ParserAdapter(self.OpName,self.endpoint_url,self.method,self.spec).get_parser()
        self.entity_config = self.parser_adapter.request
        self.base_url = self.__getbase_url(Omegaconfig_stream,self.entity_config)
        self.Tokens = self.Tokens_MOCK(self.TokensFilename,self.base_url)
        self.client_adapter = ClientAdapter(self.entity_config,self.Tokens,self.base_url)
        self.parser = None
        self.data_loader = None
        self.run()

    

    def _load_specification_(self,filename,url) ->dict:
        import json,yaml
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                raise ValueError("Ошибка при открытии файла OpenAPI spec")
            # пробуем JSON, потом YAML
            try:
                return json.loads(content)
            except:
                try:
                    return yaml.safe_load(content)
                except:
                    raise ValueError("Невалидный OpenAPI spec")
        elif url:
            return self._get_specfromrequest(url)

    def _get_specfromrequest(self,url):
        import requests,yaml
        try:
            response = requests.get(url)
            response.raise_for_status()  # Проверяем успешность запроса
            response.encoding = response.apparent_encoding or 'utf-8'
            data = yaml.safe_load(response.text)
            return data
        except requests.exceptions.RequestException as e:
            return None
        except yaml.YAMLError as e:
            return None
        


    def __getbase_url(self,config_input,entity_config):
        base_url = entity_config.get("base_url",None)
        if OmegaConf.select(config_input, "base_url", default=None):
            return config_input.base_url
        elif base_url:
            return base_url
        else:
            return ''

    def parse_config(self):
        # реализация
        pass
    def __load_configuration(self,config_input):

        if isinstance(config_input, DictConfig):
            return config_input.spec_data,config_input.spec_url,config_input.Token_src,config_input.name,config_input.endpoint_url,config_input.method
        else:
            return None
    
    def run(self):
        self.RESTClient = self.client_adapter.get_client()
        
    
    def get_schema(self):
        if self.parser is None:
            self.parser = self.parser_adapter.get_parser()
        return self.parser.get_response()
    
    #TODO
    #парсинг значений с файла
    #создание итератора по страницам
    def _prepare_payload(self, data):
        payload = []
        pagination = False
        required = self.entity_config.get('required',[])
        variables = self.entity_config.get('variables',[])
        datatype =  type(data)
        if datatype == dict:
            entity_variables = self.entity_config.get('variables',None)
            keys = data.keys()
            if set(entity_variables) & set(keys):
                print('переменная(ые) есть в списке')
            payload = [data]
        elif datatype == list:
            if  all(isinstance(item, dict) for item in data):
                payload = data
            else:
                if len(required) == 1:
                        payload = [{required[0]: value} for value in data]    
                else:
                    print('Требуется явно указать параметр(ы) запроса')
        elif data:
            payload = [{required[0]: value} for value in [data]]
        return payload
        
    def _is_valid_response(self, response):
        """
        Проверка валидности ответа от API
        """
        if response is None:
            return False
        
        if isinstance(response, dict):
            if not response:
                return False
            
            for key, value in response.items():
                if value not in (None, [], {}, '', 'null'):
                    return True
            return False
        
        elif isinstance(response, list):
            return len(response) > 0
        
        elif isinstance(response, str):
            return bool(response.strip())
        
        else:
            return response is not None
        




 ##############################










        
    def get_response(self,data):
        results = []
        with self.RESTClient as client:
            payload = self._prepare_payload(data)
            if not payload:
                try:
                    response = client.execute()  # Вызов без данных
                    if self._is_valid_response(response):
                        results.append(response)
                        return results
                    return []
                except Exception as e:
                    print(f"Error processing empty payload: {e}")
                    return []

            #разделить на два процесса в зависимости от пагинации
            
            for item in payload:
                try:
                    response = client.execute(item)
                    if self._is_valid_response(response): #вынести в контроль загрузки
                        results.append(response)
                except Exception as e:
                    print(f"Error processing {item}: {e}")        
        return results
    




##############################

    def get_response_(self, data):
        """
        Получение ответа от API с поддержкой:
        + 1 Пустого вызова (без данных)
        + 2 Пакетной обработки
         3 Пагинации
         Контроля загрузки ? в конце каждой итерации,если предусмотрена пагинация

         Собрать под единый шаблон
        """
        with self.RESTClient as client:
            payload = self._prepare_payload(data)
            
            # СЛУЧАЙ 1: Пустой payload -> одиночный вызов без данных
            if not payload:
                return self._execute_single_request(client, None)
            
            # Проверяем, нужна ли пагинация
            if self._requires_pagination():
                return self._execute_with_pagination(client, payload)
            
            # СЛУЧАЙ 2: Есть данные -> пакетная обработка
            return self._execute_batch_requests(client, payload)







    
    def Tokens_MOCK(self,filename,base_url):
        import json
            #Mock сервера ключей
        with open(filename, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
        token = tokens.get(base_url)
        return token
    
    def _paginate(self):
        pass

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
'''
    TODO
->get_response_schema_as_json()
->get_response_schema_as_xsd()
->get_response_as_json()
->get_response_as_xml()



input:
    #Если есть конфигурационный файл
    conf_file(str)
    conf_file_as_dict(dict)
    #если этого файла нет,но мы указываем их явно хардкодом
    entity(operation_name)
    OpenAPISpecYAMLFilename
    target_path
    Token_dict
    retry
    timeouts

    Pagination_param
    controlAnswerParam

'''

