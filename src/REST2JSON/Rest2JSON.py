#Объединяет класс парсера и класс клиента

#на вход получает конфигурацию - разбивает ее,выбирает стратегию,по возможности - внешняя оценка результата для контроля загрузки
import os
from urllib.parse import urlparse
from .utils.OASParser import OASParser
from .URESTClient import URESTClient

class ParserAdapter(OASParser):
    def __init__(self,OpName,endpoint_url,method,schema_infer_fallback,spec):
        self._parser = None
        self.spec = spec
        self.OpName = OpName
        self.endpoint_url = endpoint_url
        self.schema_infer_fallback = schema_infer_fallback
        self.method = method
    
    def get_parser(self): 
        if self._parser is None:
            self._parser = OASParser(self.OpName,self.endpoint_url,self.method,self.schema_infer_fallback,self.spec)
        return self._parser

class ClientAdapter(URESTClient):
    def __init__(self, entity,extra_headers,base_url,timeout):
        super().__init__(entity, extra_headers,base_url,timeout)
    

class REST2JSON:
    def __init__(self,
                config: dict = None):
        #Загружаем конфигурацию
        (self.payload,
         self.base_override,
         self.OpenAPISpecYAML,
         self.OpenAPISpecYAMLURL,
         self.auth_header,
         self.auth_body,
         self.OpName,
         self.retries,
         self.endpoint_override,
         self.method_override,
         self.timeout,
         self.paginate,
         self.page_param,
         self.type_mapping,
         self.schema_override,
         self.keep_headers,
         self.headers_fallback,
         self.schema_infer_fallback) = self.__load_configuration(config)
        #Получаем спецификацию
        self.spec = self._load_specification_(self.OpenAPISpecYAML,self.OpenAPISpecYAMLURL)
        #Загрузка адаптера

        self.__parser_adapter = ParserAdapter(self.OpName,self.endpoint_override,self.method_override,self.schema_infer_fallback,self.spec).get_parser()

        self.entity_config = self.__parser_adapter.request
        self.override_header_list  = self.get_header_keys_from_override()
        
        self.base_url = self.__getbase_url(self.entity_config)
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

    def _load_specification_(self,src,url):
        #TODO: починить переход к fallback
        #TODO: проверка маски - не ок == исключение

        if url: 
            if isinstance(url,list):
                for position in url:
                    specification_text = self._get_specfromurl(position)
                    if specification_text:
                        return specification_text
            else:        
                specification_text = self._get_specfromurl(url)
                if specification_text:
                    return specification_text
        if src: #Если по ссылкам ничего получить не удалось
            print('Не указаны ссылки на файл спецификации,читаем spec_fallback')
            return src
        raise ValueError("Отсутствуют источники спецификаций.")
        
    def _get_specfromurl(self,url):
        import requests,yaml,re
        response = None
        attemts = 0
        try:
            if re.match(r'^\w+:(\/{2,3})\w',url): #2 или 3  /// после :
                parsed = urlparse(url)
                if parsed.scheme in ('http', 'https'): 
                    #TODO: Поставить ретрай и в случае 3 неудач == берем следующий элемент из списка
                    #      В случае падения скачать с файловой системы
                    for attempt in range(self.retries):
                        try:
                            print(f'Попытка чтения файла по ссылке {url}',end="")
                            response = requests.get(url,timeout=self.timeout)
                            response.raise_for_status()
                            response.encoding = response.apparent_encoding or 'utf-8'
                            response = response.text
                            break
                        except:
                            print(f" неудачна")
                        if attempt == self.retries - 1:  
                            print(f"Все попытки получения файла по ссылке {url} провалились, перехожу к обработке следующего url.")
                            return None
                elif parsed.scheme == 'file':  
                    path_part = url.replace('file://', '', 1)
                    #запрещенка в ссылке на файл,список возможных символов
                    forbidden = ['..', '~', '$', ';', '|', '&', '`', '\\']
                    if any(x in path_part for x in forbidden):
                        raise ValueError("Обнаружены потенциально опасные символы")
                    abs_path = os.path.abspath(path_part)  # преобразование относительный путь в абсолютный
                    # 4. Открытие файла
                    if os.path.isfile(abs_path) and os.access(abs_path, os.R_OK):
                        print(f'Попытка чтения файла по ссылке {abs_path}',end="")
                        response = open(abs_path, 'r', encoding='utf-8').read()
                    #TODO : расскометировать для исправления
                    else:
                        print(f'Не удалось найти указанный файл {abs_path}')
                        return None
                else:
                    print(f'Непподерживаемая протокол: {url}')
                    return None 
                #TODO: вывалится исключение
                if response:
                    print(' успешна')
                    return response   
            else:
                print(f'Указан неккоректный префикс: {url}')        
                return None                
            print(f'Не удалось прочитать файл по ссылке: {url}')        
            return None
        except requests.exceptions.RequestException as e: #
            print(f'попытка чтения файла по ссылка окончилась ошибкой: {e}')
            return None
        except yaml.YAMLError as e:
            print(e)
            return None
        
    def __getbase_url(self,entity_config):
        base_url = entity_config.get("base_url",None)
        if self.base_override:
            return self.base_override
        elif base_url:
            return base_url
        else:
            return ''

    def __load_configuration(self,config):
        try:
            proc = config.get('proc',{})
            env = config.get('env',{})
            auth = config.get('auth',{})
            src = proc.get('src',{})
            proc_conn_params = src.get('conn_params',{})
            conn_type = src.get('conn_type',{})
            auth_header,auth_body = auth.get('src',{}).get('header',{}),{}
            if not auth_header:
                auth_body = auth.get('src',{}).get('body',{})
            src_data = proc.get('src',{}).get('data',{})
            name = src.get('name',{})
            type_mapping = env.get('json',{}).get('type_mapping',{})
            headers_fallback = env.get('json',{}).get('headers_fallback',{}) #задел для update

            type_mapping.update(src_data.get('type_mapping_override',{}))
            payload = src_data.get('payload',None)
            schema_override = src_data.get('schema_override',None)
            keep_headers = src_data.get('schema_keep_headers',None)
            schema_infer_fallback = src_data.get('schema_infer_fallback',None)
            if proc_conn_params:
                endpoint_override = proc_conn_params.get('endpoint_override',None)
                method_override  = proc_conn_params.get('method_override',None)
                timeout = proc_conn_params.get('timeout',None)
                retries = proc_conn_params.get('retries',None)
                pagination  = proc_conn_params.get('pagination',{}).get('enabled',None)
                page_param  = proc_conn_params.get('pagination',{}).get('page_param',None)
                spec_url    = proc_conn_params.get('spec_url',None)
                spec_fallback   = proc_conn_params.get('spec_fallback',None)
                base_override    = proc_conn_params.get('base_override',None)
                #помечу на удаление
            return payload,base_override,spec_fallback,spec_url,auth_header,auth_body,name,retries,endpoint_override,method_override,timeout,pagination,page_param,type_mapping,schema_override,keep_headers,headers_fallback,schema_infer_fallback
        except Exception as e:
            print(e)
                
    def get_header_keys_from_override(self):
        '''
        Парсинг schema_override из конфигурации
        извлекаем все ключи из headers.type.fields если они есть
        {
            type:struct
            fields:[
                    {name:content,type:{}},
                    {name:header,type: struct,fields:[{name:key1},{name:key2}.....]}
                    ]
        }
        '''
        import json
        result = []
        try:
            if self.schema_override:
                schema = json.loads(self.schema_override)
                if schema.get('type') == 'struct':
                    main_field = schema.get('fields')
                    if main_field and (isinstance,list):
                        header_struct = next((f for f in main_field if f.get("name") == "header"), None)
                        if isinstance(header_struct,dict):
                            param_list = header_struct.get('type',{}).get('fields',[])
                            result = [j.get('name') for j in param_list]
        except:
            TypeError('Не удалось проебразовать schema_override в формат JSON')
        return result

    def _prepare_payload(self, data):
        import copy
        payload = copy.deepcopy(data) # на этот момент payload должен быть списком словарей 
        datatype = type(payload).__name__
        if datatype not in ('list','dict','NoneType'):
            raise ValueError(' payload должнен иметь тип `dict|list|NoneType`')
        if isinstance(payload,list):
            if not (len(set(map(type, payload))) <= 1 and type(payload[0]) == dict):
                raise ValueError('в списке payload все объекты должны быть типа `dict`')
        if isinstance(payload,dict):
            payload = [payload]
        
        
        if not self.auth_header and self.auth_body: #Добавляем пароль к сообщению , 1 приоритет - header
            if payload:
                payload = [{**value, **self.auth_body} for value in payload] 
            else: # в payload нет ничего - в сообщении будет только авторизация
                payload = self.auth_body
        return payload      
    
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

    def get_data(self,data = None):
        datatype = type(data).__name__ #Явная проверка на наличие аргумента в вызове метода
        if datatype == 'NoneType':
            data = self.payload
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
        if not data:
            try:
                for attempt in range(self.retries):
                    try:
                        content, headers = self.__client_adapter.execute()  # Вызов без данных
                        if self.keep_headers:
                            answer = {'content': content}
                            header = {}
                            custom_header_variables = self.entity_config.get('custom_header_variables', [])
                            if custom_header_variables and not self.override_header_list:
                                header_variables = custom_header_variables
                            elif self.override_header_list:
                                header_variables = self.override_header_list
                            else:
                                if isinstance(self.headers_fallback,dict):
                                    header_variables = self.headers_fallback.keys()
                                else:
                                    header_variables = []
                            for i in header_variables:
                                header_data = headers.get(i, {})
                                header.update(header_data)
                            answer['headers'] = header
                            results.append(answer)
                        else:
                            results.append(content)
                        return results  
                        
                    except Exception as e:
                        print(f"Попытка {attempt + 1}/{self.retries} неудачна: {e}")
                        if attempt == self.retries - 1:  
                            print(f"Все {self.retries} попытки запроса провалились")
                            return []
                return []  
            except Exception as e:
                print(f"Ошибка обработки: {e}")
                return []
            
        else:
            for item in data:
                for attempt in range(self.retries):
                    try:
                        content, header = self.__client_adapter.execute(item)
                        if True:  # вынести в контроль загрузки
                            if self.keep_headers:
                                answer = {'content': content}
                                headers = {}
                                custom_header_variables = self.entity_config.get('custom_header_variables', [])
                                if custom_header_variables and not self.override_header_list:
                                        header_variables = custom_header_variables
                                elif self.override_header_list:
                                    header_variables = self.override_header_list
                                else:
                                    if isinstance(self.headers_fallback,dict):
                                        header_variables = self.headers_fallback.keys()
                                    else:
                                        header_variables = []
                                for i in header_variables:
                                    header_data = header.get(i, {})
                                    if header_data:
                                        headers.update({i:header_data})
                                answer['headers'] = headers
                                results.append(answer)
                            else:
                                results.append(content)
                        break      
                    except Exception as e:
                        print(f"Попытка {attempt + 1}/{self.retries} неудачна: {e}")
                        if attempt == self.retries - 1: 
                             print(f"Все {self.retries} попытки запроса {item} провалились")
                             return results
            return results
    
    def close(self):
        if self.__in_context:
            self.__in_context = False
            self.__client_adapter.close()
            
    def add_header_to_content(self,content,header,headers_fallback,type_mapping):
        '''
        Работает когда:
        Надо собрать структуру из ничего - Кейс №6
        '''
        TEMPLATE = '''
                {{
                    "type": "struct",
                    "fields": [
                        {{
                            "name": "headers",
                            "nullable": true,
                            "type": {0},
                            "metadata": {{}}
                        }},
                        {{
                            "name": "content",
                            "nullable": true,
                            "type": {1},
                            "metadata": {{}}
                        }}
                    ]
                }}
                '''

        header_template = {
            "type": "struct",
            "fields": []
            }
        
        import json
        if header:
            fields = header.get('fields',[])
            fields += header_template.get('fields',[])
            header['fields'] = fields
        elif headers_fallback:
            for i,j in headers_fallback.items():
                if i not in self.override_header_list:
                    header_param = {
                                            "name": i,
                                            "nullable": True,
                                            "type": type_mapping.get(j,'string'),
                                            "metadata": {}
                                        }
                    header_template['fields'].append(header_param)
            header = header_template
        else:
            header = header_template
        
        result = TEMPLATE.format(json.dumps(header),json.dumps(content))
        return json.loads(result) 

    def __check_schema_override(self,schema,headers_fallback,type_mapping):
        if not isinstance(schema, dict) or 'fields' not in schema:
            raise KeyError('Неккоректная структура схемы.')
        has_content,has_header = False,False
        for field in schema['fields']:
            if field.get('name') == 'headers':
                has_header = True
            if field.get('name') == 'content':
                has_content = True
        if has_header and has_content:
            return schema 
    

        if not has_header:
            header_template = {
                "type": "struct",
                "fields": []
                }
            if headers_fallback: 
                for i,j in headers_fallback.items(): #сконвертировать
                    header_param = {
                                    "name": i,
                                    "nullable": True,
                                    "type": type_mapping.get(j,'string'),
                                    "metadata": {}
                                }
                    header_template['fields'].append(header_param)

            new_headers = header_template

            template =  {"name": "headers",
                                "nullable": True,
                                "type": {},
                                "metadata":{} }
            template["type"] = new_headers
            schema['fields'].append(template)
        if not has_content:
            template =  {"name": "content",
                            "nullable": True,
                            "type": {},
                            "metadata":{} }
            template["type"] = self.__resolve_override_schema(schema)
            #чистим первый уровень - оставляем только headers
            schema["fields"] = [f for f in schema["fields"] if f.get("name") == "headers"]
            #добавиляем к headers content
            schema['fields'].append(template)
            #остается еще поле вне content и header
        return schema

    def __resolve_override_schema(self, schema):
        #TEST: keep_header = 0 + schema_override not null, поле header дропаем, если есть,content распаковываем на первый уровень - уронить при конфликте имен
        if not isinstance(schema, dict) or 'fields' not in schema:
            raise KeyError('Некорректная структура схемы.')
        
        new_fields = []
        content_fields = []
        
        for field in schema['fields']:
            if field.get('name') == 'headers':
                continue
            
            if field.get('name') == 'content':
                field_type = field.get('type', {})
                type_name = field_type.get('type')
                
                if type_name == 'struct':
                    content_fields = field_type.get('fields', [])
                elif type_name == 'array':
                    element_type = field_type.get('elementType', {})
                    if element_type.get('type') == 'struct':
                        content_fields = element_type.get('fields', [])
                    else:
                        content_fields = [field] 
                else:
                    # Для других типов
                    content_fields = [field]
            else:
                new_fields.append(field)
        
        new_fields.extend(content_fields)

        existing_names = [f['name'] for f in new_fields]
        unique = set(existing_names)

        if len(existing_names) != len(unique):
            raise KeyError("Конфликт имен полей")
        
        if len(new_fields) == 0:
                  return {"type": "struct",
                         "fields":[]}
        return {
            "type": "struct",
            "fields": new_fields
        }

    def get_schema(self,raw:bool = False):
        import json
        if not self.headers_fallback:
            headers_fallback = {}
        if not isinstance(raw,bool):
            raise TypeError('Неподдерживаемый тип данных')
        if self.__parser_adapter.get_response_map() is None:
            raise ValueError('В предложенной спецификации отсутствует раздел response.')
        
            #+Кейс 1. keep_header = 1 + schema_override not null , есть header и content - ничего не делаем
            #+Кейс 2. keep_header = 1 + schema_override not null , добавить content если нет
            #+Кейс 3. keep_header = 1 + schema_override not null , добавить header  если нет
            #+Кейс 4. keep_header = 0 + schema_override not null, поле header дропаем, если есть,content распаковываем на первый уровень - уронить при конфликте имен
            #+Кейс 5. keep_header = 0 + schema_override is null , возвращаем schema
            #+Кейс 6. keep_header = 1 + schema_override is null, добавляем header в соотстветвие с конфигурацией + (реальный header из спеки - мб их не будет)
            #+Кейс 7. keep_header = 1 + schema_override is null, raw = True  
            #+Кейс 8. keep_header = 0 + schema_override is null, raw = True  
        if raw: #без конфигурации, кейс #7-8
            custom_header_variables = self.entity_config.get('custom_header_variables',[]) #получаем список атрибутов хидера из спеки / + при schema_override = 1 этот список должен заполнится из schema_override
            properties = {}
            if self.keep_headers:
                import copy
                header = copy.deepcopy(self.__parser_adapter.get_headers_map())
                if header is not None:
                    for i,j in headers_fallback.items():
                        if custom_header_variables:
                            if i not in custom_header_variables:
                                header['properties'].update({i:{'schema':{'type': j}}})
                            else:
                                properties[i] = {'schema':{'type': j}}
                else:
                    header = {'type': 'object','properties':{}}
                    for i,j in self.headers_fallback.items():
                        if custom_header_variables:
                            if i not in custom_header_variables:
                                properties[i] = {'schema':{'type': j}}
                        else:
                            properties[i] = {'schema':{'type': j}}
                    header['properties'] = properties
                return {'content':self.__parser_adapter.get_response_map(),'headers':header} 
            else:
                return self.__parser_adapter.get_response_map() #Кейс 8
        else:
            if not self.keep_headers:
                if self.schema_override:
                    return self.__resolve_override_schema(json.loads(self.schema_override)) # Кейс 4
                return self.__parser_adapter.getStructTypeSchema(self.type_mapping) # Кейс 5
            elif self.keep_headers:
                if self.schema_override: #Кейс 1-3
                    return self.__check_schema_override(json.loads(self.schema_override),headers_fallback,self.type_mapping)
                else:
                    return self.add_header_to_content(self.__parser_adapter.getStructTypeSchema(self.type_mapping),self.__parser_adapter.getStructTypeHeader(self.type_mapping),self.headers_fallback,self.type_mapping) #Кейс 6

