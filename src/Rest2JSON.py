#Объединяет класс парсера и класс клиента

#на вход получает конфигурацию - разбивает ее,выбирает стратегию,по возможности - внешняя оценка результата для контроля загрузки

from utils.OASParser import OASParser
from URESTAdapter import URESTAdapter

class ParserAdapter(OASParser):
    def __init__(self, filename):
        self._parser = None
        self.filename = filename
    
    def get_parser(self):  # переименовал для ясности
        if self._parser is None:
            self._parser = OASParser(self.filename)
        return self._parser

class ClientAdapter(URESTAdapter):
    def __init__(self, entity,secret):
        self._client = None
        self.entity = entity
        self.secret = secret
    
    def get_client(self):
        if self._client is None:
            self._client = URESTAdapter(self.entity,self.secret)
        return self._client
    
    def execute(self, data):
        client = self.get_client()
        return client.execute(data)  # предполагаем, что у URESTAdapter есть метод execute


class REST2JSON:
    def __init__(self,
                config_file = None):
        self.config_file = config_file
        self.entity,self.OpenAPISpecYAMLFilename,self.TokensFilename = self.__load_configuration(config_file)
        self.parser_adapter = ParserAdapter(self.OpenAPISpecYAMLFilename)
        self.Tokens = self.Tokens_MOCK(self.TokensFilenam)
        self.client_adapter = ClientAdapter(self.entity,self.Tokens)
        self.parser = None
        self.RESTClient = None
        self.run()
    
    def parse_config(self):
        # реализация
        pass
    def __load_configuration(self,filename = ''):
    
        from omegaconf import OmegaConf

        config = OmegaConf.load(filename)
        return config.entity,config.OpenAPISpecYAMLFilename,config.Token_src
    
    def run(self):
        # Получаем парсер
        self.parser = self.parser_adapter.get_parser()
        
        # Используем данные из парсера
        self.RESTClient = self.client_adapter.get_client()
        
    
    def get_schema(self):
        if self.parser is None:
            self.parser = self.parser_adapter.get_parser()
        return self.parser.get_response()
    
    def get_response(self):
        # реализация
        pass
    def Tokens_MOCK(self,filename):
        import json
            #Mock сервера ключей
        with open(filename, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
        token = tokens.get(self.entity.get('base_url'))
        return token

rest = REST2JSON(config_file = 'C:/Users/kdenis/Documents/Work/OpenApiSpecParser/src/config.yaml')




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

