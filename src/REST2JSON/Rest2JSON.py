#Объединяет класс парсера и класс клиента

#на вход получает конфигурацию - разбивает ее,выбирает стратегию,по возможности - внешняя оценка результата для контроля загрузки
from omegaconf import DictConfig, OmegaConf
from .utils.OASParser import OASParser
from .utils.utils import has_data
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
    def __init__(self, entity,extra_headers,base_url,timeout):
        super().__init__(entity, extra_headers,base_url,timeout)
    
    

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
        self.OpenAPISpecYAML,self.OpenAPISpecYAMLURL,self.auth_header,self.auth_body,self.OpName,self.endpoint_url,self.method,self.timeout,self.paginate,self.page_param,self.type_mapping = self.__load_configuration(Omegaconfig_stream)
        #Получаем спецификацию
        self.spec = self._load_specification_(self.OpenAPISpecYAML,self.OpenAPISpecYAMLURL)
        #Загрузка адаптера

        self.__parser_adapter = ParserAdapter(self.OpName,self.endpoint_url,self.method,self.spec).get_parser()
        self.entity_config = self.__parser_adapter.request
        
        self.base_url = self.__getbase_url(Omegaconfig_stream,self.entity_config)
        #self.Tokens = self.Tokens_MOCK(self.TokensFilename,self.base_url)
        self.__client_adapter = ClientAdapter(self.entity_config,self.auth_header,self.base_url,self.timeout)
        self.__in_context = False  # доп флаг

    def __enter__(self):
        if self.__in_context:
            raise RuntimeError("Объект уже используется.")
        self.__client_adapter.__enter__()
        self.__in_context = True
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__in_context = False
        self.__client_adapter.__exit__(exc_type, exc_val, exc_tb)
        return False

    def _load_specification_(self,src,url) ->dict:
        import yaml 
        if url:
            return self._get_specfromrequest(url)
        elif src:
            try:
                return yaml.safe_load(src)
            except:
                raise ValueError("Невалидный OpenAPI spec")
        else:
            raise ValueError("Отсутствуют источники спецификаций в конфигурационном файле.")


    def _get_specfromrequest(self,url):
        import requests,yaml
        try:
            response = requests.get(url)
            response.raise_for_status() 
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

    def __load_configuration(self,config_input):
        auth_header,auth_body = {},{}
        if isinstance(config_input, DictConfig):
            if config_input.auth_header:
                auth_header = OmegaConf.to_object(config_input.auth_header)
            if config_input.auth_body:
                auth_body = OmegaConf.to_object(config_input.auth_body)
            #############обработка маппинга типов
            type_mapping = OmegaConf.merge(config_input.type_mapping, config_input.json_mapping_override)
            return config_input.spec_data,config_input.spec_url,auth_header,auth_body,config_input.name,config_input.endpoint_url,config_input.method,config_input.timeout,config_input.pagination,config_input.page_param,type_mapping
        else:
            return None    
    
    def get_StructTypeFormatSchema(self):
        if self.__parser_adapter is None:
            return None
        return self.__parser_adapter.getStructTypeSchema(self.type_mapping)
    
    def get_JSONTypeschema(self):
        if self.__parser_adapter is None:
            return None
        return self.__parser_adapter.get_response_map()
    
    def _prepare_payload(self, data):
        #TODO 
        #добавить вставку ApiKey в каждый запрос,
        #по условию если нет хидера и есть боди
        payload = []
        required = self.entity_config.get('required',[])
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
        else: # Если запрос - это просто обращение по ссылке
            payload = data     
        if not self.auth_header and self.auth_body: #Добавляем пароль к сообщению , 1 приоритет - header
            if payload:
                payload = [value.update(self.auth_body) for value in [data]] # на этот момент payload уже список словарей
            else:
                payload = self.auth_body
        return payload
        
    def _is_valid_response(self, response=None,entity_schema=None,debug=True):

        """
        Проверка валидности ответа от API
        добавить оценку если это массив структур,иначе результат ложноположительный

        стратегия: заинферить схему из ответа и столкнуть с схемой ответа из специ,похожесть
        еще пандас
        Отложено: всегда обрывает пагинацию
        """
        return False 
    
    def __direct(self, payload):
        """
        Прямой запрос к API используя _get/_post
        """
        got_list = False
        result = []
        if isinstance(payload,list):
            data_list = self._prepare_payload(payload)
            got_list = True
        else:
            data_list = self._prepare_payload(payload) 
        try:
            http_client = self.__client_adapter.client
            for data in data_list:
            # Определяем метод из конфига
                method = self.__client_adapter.config.get('method', 'GET').upper()
                
                # Формируем URL
                url_template = f"{self.base_url}{self.__client_adapter.config.get('url', '')}"
                if data:
                    try:
                        url = url_template.format(**data)
                    except KeyError:
                        url = url_template
                else:
                    url = url_template
                
                # Выполняем прямой запрос
                if method == 'GET':
                    response = http_client._get(url, data)
                else:  # POST
                    response = http_client._post(url, data)
                
                # Валидируем ответ
                if not got_list:
                    if isinstance(response,dict):
                        return [response]
                    else:
                        return response
                result.append(response)
            return result
        except Exception as e:
            return None

    def get_response(self, data=None):
        if self.__in_context:
            return self.__direct(data)
        else:
            payload = self._prepare_payload(data)
            self.__enter__()
            try:
                results = self._execute(payload)
            finally:
                self.__exit__(None, None, None)
    
        return results
        
    def _execute(self,data):
        results = []
        #разделить на два процесса в зависимости от пагинации
        '''
        #Отложено 11/03/2026

        if self.paginate:
            for item in data:
                page = 1   
                while True:
                    try:
                        print(f'proccess page {page}')
                        item[self.page_param] = page
                        response = self.client_adapter.execute(item)
                        if self._is_valid_response(response = response,debug=True): #вынести в контроль загрузки
                            results.append(response)
                        else:
                            break
                        page += 1
                    except Exception as e:
                        print(f"Error processing {item}: {e}")
                        break   
        '''
        if not data:
            try:
                response = self.__client_adapter.execute()  # Вызов без данных
                if self._is_valid_response(response = response,debug=True):
                    results.append(response)
                    return results
                return []
            except Exception as e:
                print(f"Error processing empty payload: {e}")
                return []
            
        else:
            for item in data:
                try:
                    response = self.__client_adapter.execute(item)
                    if self._is_valid_response(response = response,debug=True) or True: #вынести в контроль загрузки
                         results.append(response)
                except Exception as e:
                    print(f"Error processing {item}: {e}")        
        return results


    def Tokens_MOCK(self,filename,base_url):
        import json
            #Mock сервера ключей
        with open(filename, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
        token = tokens.get(base_url,None)
        return token
    
    def close(self):
        if self.__in_context:
            self.__in_context = False
            self.__client_adapter.close()
            

