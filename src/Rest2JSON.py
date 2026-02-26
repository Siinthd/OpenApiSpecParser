#Объединяет класс парсера и класс клиента

#на вход получает конфигурацию - разбивает ее,выбирает стратегию,по возможности - внешняя оценка результата для контроля загрузки

from src.utils.OASParser import OASParser
from src.URESTAdapter import URESTAdapter

class ParserAdapter(OASParser):
    def __init__(self, filename):
        self._parser = None
        self.filename = filename
    
    def get_parser(self): 
        if self._parser is None:
            self._parser = OASParser(self.filename)
        return self._parser

class ClientAdapter(URESTAdapter):
    def __init__(self, entity,secret):
        super().__init__(entity, secret)
    
    def get_client(self):
        return self
    

    # TODO 
    # проверка есть ли ключи словаря в спеке
    # Если required один то подставить его к списку значений
    # формировать data, формировать очередь единичных загрузок
    # Текущая реализация непотокобезопасна

class REST2JSON:
    def __init__(self,
                config_file = None):
        self.config_file = config_file
        self.entity_name,self.OpenAPISpecYAMLFilename,self.TokensFilename = self.__load_configuration(config_file)
        self.parser_adapter = ParserAdapter(self.OpenAPISpecYAMLFilename).get_parser()
        self.entity_config = self.parser_adapter.request.get(self.entity_name)
        self.Tokens = self.Tokens_MOCK(self.TokensFilename)
        self.client_adapter = ClientAdapter(self.entity_config,self.Tokens)
        self.parser = None
        self.data_loader = None
        self.run()
    
    def parse_config(self):
        # реализация
        pass
    def __load_configuration(self,filename = ''):
    
        from omegaconf import OmegaConf

        config = OmegaConf.load(filename).REST2JSON
        return config.entity,config.OpenAPISpecYAMLFilename,config.Token_src
    
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
        
    def get_response(self,data):
        with self.RESTClient as client:
            payload = self._prepare_payload(data)
            results = []
            
            for item in payload:
                try:
                    response = client.execute(item)
                    if self._is_valid_response(response):
                        results.append(response)
                except Exception as e:
                    print(f"Error processing {item}: {e}")        
        return results
    
    def Tokens_MOCK(self,filename):
        import json
            #Mock сервера ключей
        with open(filename, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
        token = tokens.get(self.entity_config.get('base_url'))
        return token

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

