#Объединяет класс парсера и класс клиента

#на вход получает конфигурацию - разбивает ее,выбирает стратегию,по возможности - внешняя оценка результата для контроля загрузки

from src.utils.OASParser import OASParser
from src.URESTAdapter import URESTAdapter

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
        return self.client.execute(data)  #у URESTAdapter есть метод execute


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
        self.RESTClient = None
        self.run()
    
    def parse_config(self):
        # реализация
        pass
    def __load_configuration(self,filename = ''):
    
        from omegaconf import OmegaConf

        config = OmegaConf.load(filename).REST2JSON
        return config.entity,config.OpenAPISpecYAMLFilename,config.Token_src
    
    def run(self):
        # Получаем парсер
        #self.parser = self.parser_adapter.get_parser()
        
        # Используем данные из парсера
        self.RESTClient = self.client_adapter.get_client()
        
    
    def get_schema(self):
        if self.parser is None:
            self.parser = self.parser_adapter.get_parser()
        return self.parser.get_response()
    

    #пока что ленивая реализация из адаптера
    def get_response(self,data):
        #работаем со входными переменными - это все перенести в REST2API
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
            if  all(isinstance(item, dict) for item in data): #проверяем что это не список словарей
                payload = data
            else:
                if len(required) == 1:
                        payload = [{required[0]: value} for value in data]    
                else:
                    print('Требуется явно указать параметр(ы) запроса')
        elif data:
            payload = [{required[0]: value} for value in [data]]

        #TODO
        # Ищем параметры с Page,они не всегда обязательные
        #Инициализация движка тоже в конструктор
        self.RESTClient.init_dataLoader()
        result = []

        # разобрать под единичный вызов
        for i in payload:
            try:
                    _dbg = self.RESTClient.execute(i) 
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
    
    def Tokens_MOCK(self,filename):
        import json
            #Mock сервера ключей
        with open(filename, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
        token = tokens.get(self.entity_config.get('base_url'))
        return token


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

