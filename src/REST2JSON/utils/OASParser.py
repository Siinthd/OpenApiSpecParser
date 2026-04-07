import re
from .utils import OpenAPIToSparkConverter
import copy
from typing import Any


# Теперь мы не парсим всю спеку - мы перебираем /path на предмет OperationID
# В противном случае - мы ищем спецификацию конкретной операции по endpoint,method(в случае если в endpoint содержатся несколько методов) и 
# На Вход получаем только словарь


class OASParser:
    def __init__(self, OpName:str = None,endpoint_url:str= None,method:str= None,schema_infer_fallback:bool = True,loaded_spec:dict = None):
        self.operation_Name = copy.copy(OpName)
        self.target_endpoint = copy.copy(endpoint_url)
        self.target_method = copy.copy(method)
        self.schema_infer_fallback = copy.copy(schema_infer_fallback)
        self.spec = copy.deepcopy(loaded_spec)
        self.base_url = self.__getbaseurl(self.spec) #выполнять если
        self.post = self.__parse_specification(self.__getEndpoint(self.spec))
        
        
        ###Формируется структура без добавления кастомных данных
        #json для content и header
        self.endpoint_section = self.__resolve_refs_in_operation(copy.deepcopy(self.post),self.__extract_schemas(copy.deepcopy(self.spec)))
        self.request = self.__transform_spec_to_requests(self.endpoint_section)
        self.response_map = self.endpoint_section.get('response',None)
        self.headers_map = self.form_header(self.endpoint_section.get('headers',None))


    def form_header(self, header_raw: dict): #
        if header_raw:
            result = {'type': 'object', 'properties': None}
            result['properties'] = header_raw
            return result
        return None


    def getStructTypeSchema(self,type_mapping):
        return self.__convert_schema_to_sprkfrm(copy.deepcopy(self.response_map),type_mapping)
    
    def getStructTypeHeader(self,type_mapping):
        if self.headers_map:
            return self.__convert_schema_to_sprkfrm(copy.deepcopy(self.headers_map),type_mapping)
        return {}
    
    def getSpecification(self):
        return self.spec
    
    def __findendpointbypath(self,spec_dict: dict) -> dict:
        endpoints = spec_dict.get('paths', {})
        endpoint =  endpoints.get(self.target_endpoint,None)
        if endpoint:
            for metod,value in endpoint.items():
                if metod == self.target_method:
                    return {metod:value}#берем нужный метод
        return None
        

    def __findendpointbyOpId(self,spec_dict: dict) -> dict:
        for path, methods in spec_dict.get('paths', {}).items():
            for method_name, method_details in methods.items():
                operation_id = method_details.get('operationId',None)
                if operation_id == self.operation_Name:
                    self.target_endpoint = path
                    return {method_name:method_details} #возвращается весь эндпоинт
        return None

    def __getEndpoint(self,spec:dict) -> dict: 
        endpoint = None
        #Сначала проверяем по override endpoint_url
        if self.target_endpoint and self.target_method:
            endpoint = self.__findendpointbypath(spec)
            if endpoint:
                return endpoint
        elif self.operation_Name: #не нашли по endpoint+method(или их нет)- ищем  по name
                endpoint =  self.__findendpointbyOpId(spec)
                if endpoint:
                    return endpoint
        else:
            raise 'параметры endpoint_override/method_override/name не описаны в конфигурации. Дальнейшая работа невозможна.'

        if endpoint is None:
            raise f'endpoint_url:{self.target_endpoint} или OperationID:{self.operation_Name} отсутствуют в спецификации. Дальнейшая работа невозможна.'

    def __resolve_refs_in_operation(self, operation_spec: dict, ref_dict: dict) -> dict:
        """
        Заменяет $ref в параметрах операции.
        
        Raises:
            KeyError: Если ссылка $ref не найдена в ref_dict
        """
        if isinstance(operation_spec, dict):
            for key, value in list(operation_spec.items()):
                if isinstance(value, dict):
                    # Если нашли словарь с $ref
                    if "$ref" in value and isinstance(value["$ref"], str):
                        ref_path = value["$ref"]
                        if ref_path in ref_dict:
                            # Заменяем весь словарь на содержимое схемы
                            operation_spec[key] = ref_dict[ref_path]
                        elif self.schema_infer_fallback:
                            raise KeyError(f"Источника '{ref_path}' нет в разделе #/components")
                    else:
                        # Рекурсивно обрабатываем дальше
                        self.__resolve_refs_in_operation(value, ref_dict)
                elif isinstance(value, list):
                    self.__resolve_refs_in_operation(value, ref_dict)
        elif isinstance(operation_spec, list):
            for i, item in enumerate(operation_spec):
                if isinstance(item, dict):
                    if "$ref" in item and isinstance(item["$ref"], str):
                        ref_path = item["$ref"]
                        if ref_path in ref_dict:
                            # Заменяем элемент списка на содержимое схемы
                            operation_spec[i] = ref_dict[ref_path]
                        elif self.schema_infer_fallback:
                            raise KeyError(f"Источника '{ref_path}' нет в разделе #/components")
                    else:
                        self.__resolve_refs_in_operation(item, ref_dict)
                elif isinstance(item, list):
                    self.__resolve_refs_in_operation(item, ref_dict)
        
        return operation_spec

    def __getbaseurl(self, spec_dict: dict):
        '''
            __getbaseurl
            возвращает первый элемент списка,
            если сервер в формате переменной то (раскрыть из enum) - 
            взять сначала default потом первый из enum
        '''
        servers = spec_dict.get('servers', [])
        if not servers:
            return ''
        
        # Сначала ищем сервер с default значениями
        for server in servers:
            url_template = server.get('url', '').rstrip('/')
            variables = re.findall(r'\{(\w+)\}', url_template)
            
            if not variables:
                return url_template
            
            var_configs = server.get('variables', {})
            values = {}
            
            for var in variables:
                default_val = var_configs.get(var, {}).get('default')
                if not default_val:
                    break
                values[var] = default_val
            else:
                try:
                    return url_template.format(**values)
                except KeyError:
                    continue
        
        if servers:
            first_server = servers[0]
            first_url = first_server.get('url', '').rstrip('/')
            first_vars = re.findall(r'\{(\w+)\}', first_url)
            
            if not first_vars:
                return first_url
            
            values = {}
            var_configs = first_server.get('variables', {})
            
            for var in first_vars:
                values[var] = var_configs.get(var, {}).get('default', '')
            
            try:
                return first_url.format(**values)
            except KeyError:
                return first_url
        
        return ''
    
    
    def __process_headers(self, headers_dict: dict) -> dict:
        """
        Обрабатывает заголовки, извлекая schema из каждого заголовка
        и резолвя ссылки
        """
        if not headers_dict:
            return None
        
        processed_headers = {}
        ref_dict = self.__extract_schemas(copy.deepcopy(self.spec))
        
        for header_name, header_details in headers_dict.items():
            if isinstance(header_details, dict) and 'schema' in header_details:
                schema_content = header_details['schema']
                
                # Если schema содержит ссылку - резолвим
                if isinstance(schema_content, dict) and "$ref" in schema_content:
                    ref_path = schema_content["$ref"]
                    if ref_path in ref_dict:
                        schema_content = ref_dict[ref_path]
                
                # Сохраняем метаданные заголовка + содержимое schema
                processed_header = {
                    "description": header_details.get("description"),
                    "required": header_details.get("required", False)
                }
                
                # Переносим свойства из schema
                if isinstance(schema_content, dict):
                    processed_header.update(schema_content)
                else:
                    processed_header["type"] = schema_content
                
                processed_headers[header_name] = processed_header
            else:
                processed_headers[header_name] = header_details
        
        return processed_headers
    


    def __parse_specification(self, spec_dict: dict) -> dict:
            result = {}
            path = self.target_endpoint
            for method_name, method_details in spec_dict.items():
                method_upper = method_name.upper()
                if isinstance(method_details,dict):
                    parameters =  method_details.get('parameters',None)
                    endpoint_data = {}
                    method_security = method_details.get('security')
                    method_responses = method_details.get('responses')
                    if method_responses is not None:
                        # Добавить схему ответа
                        response = method_details.get('responses')                       
                        if response is not None:                    
                            endpoint_data['response'] = self.__find_response_schema(response)
                            headers = response.get('200',{}).get('headers',{}) #пока только для 200
                            if headers:
                                endpoint_data['headers'] = self.__process_headers(headers)
                    if method_security is not None:
                        # Используем security из метода - выкинуть
                        endpoint_data['security'] = method_security
                            
                    request_body = method_details.get('requestBody', {}) 
                    if request_body:
                        content = request_body.get('content', {}) #Тут возможная проблема, мы берем контент из request,а надо response
                        if content:
                            content_type = next(iter(content))
                            content_details = content[content_type]
                            schema = content_details.get('schema', {})
                            endpoint_data.update({
                                    'content': content_type,
                                    'request_body': schema
                                })
                    req_params = re.findall(r'\{(\w+)\}', path)
                    if req_params :
                        param_list = []
                        for req_par in req_params:
                            param_list.append(req_par)
                        endpoint_data['reqref_params'] = param_list
                    operation_id = method_details.get('operationId',None)
                    endpoint_data['operationId'] = operation_id
                    if parameters:
                        endpoint_data['parameters'] = parameters
                    endpoint_data['method'] = method_upper
                    endpoint_data['path'] = path
                    result.update(endpoint_data)
            return result
    
    def __find_response_schema(self, obj: Any, depth: int = 0, max_depth: int = 15) -> dict | str | None:
        """
        Рекурсивно ищет "наиболее вероятную" схему ответа.
        Возвращает:
        - dict — если нашёл inline-схему
        - str  — если нашёл $ref (строку вида "#/components/schemas/...")
        - None — если ничего не нашёл
        """
        if depth > max_depth:
            return None

        if not isinstance(obj, (dict, list)):
            return None

        # schema или $ref на текущем уровне
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                if isinstance(ref, str) and ref.startswith("#/"):
                    return ref  # возвращаем ref как есть — дальше можно резолвить

            if "schema" in obj and isinstance(obj["schema"], (dict, str)):
                return obj["schema"]

        #  Типичные пути в OpenAPI
        common_paths = [
            ("content", "application/json", "schema"),
            ("content", "application/json", "$ref"),
            ("content", "application/vnd.api+json", "schema"),
            ("schema",),
            ("$ref",),
            ("responses", "200", "content", "application/json", "schema"),
            ("responses", "200", "schema"),
        ]

        for path in common_paths:
            current = obj
            try:
                for key in path:
                    current = current[key]
                if isinstance(current, (dict, str)):
                    return current
            except (KeyError, TypeError):
                continue

        #  oneOf / allOf / anyOf 
        if isinstance(obj, dict):
            for combinator in ["oneOf", "allOf", "anyOf"]:
                if combinator in obj and isinstance(obj[combinator], list):
                    for variant in obj[combinator]:
                        if isinstance(variant, dict):
                            found = self.__find_response_schema(variant, depth + 1, max_depth)
                            if found is not None:
                                return found  # возвращаем первый найденный рабочий вариант

        #  Рекурсия по всем вложенным словарям и спискам
        if isinstance(obj, dict):
            for v in obj.values():
                found = self.__find_response_schema(v, depth + 1, max_depth)
                if found is not None:
                    return found

        elif isinstance(obj, list):
            for item in obj:
                found = self.__find_response_schema(item, depth + 1, max_depth)
                if found is not None:
                    return found

        return None
    

    def __transform_spec_to_requests(self, spec: dict) -> dict:
        request = {}
        try:
            path = spec.get("path", '')            
            # Получаем метод
            method = spec.get("method", "GET").upper()
            base_url = spec.get("base_url", "")
            # Получаем путь
            url = spec["path"]

            headers = spec.get('headers',{})
            headers_params = []
            if headers:
                headers_params = headers.keys()
            
            # Формируем финальную конфигурацию
            request = {
                "base_url":self.base_url,
                "method": method,
                "url": url,
                "headers": {
                    "Content-Type": spec.get("content", ""),#application/json
                    "Accept": ""#application/json
                },
                "auth_types": spec.get("security", None),
                "custom_header_variables" : sorted(list(headers_params)) if headers_params else [], 
            }
            
            
        except Exception as e:
            print(f"Предупреждение: Ошибка обработки endpoint '': {e}")
            import traceback
            traceback.print_exc()
        
        return request

    def get_response_map(self,ID:str = None): 
        return self.response_map
    
    def get_headers_map(self,ID:str = None): 
        return self.headers_map
        
    def _get_request_config(self):
        return self.request

    def __extract_schemas(self, openapi_spec: dict):
        """
        Загружает все компоненты OpenAPI спецификации.
        
        out:
            dict: Словарь всех компонентов с их путями в качестве ключей
        """
        raw_components = {}
        if 'components' in openapi_spec and isinstance(openapi_spec['components'], dict):
            components = openapi_spec['components']
            
            for component_type, component_dict in components.items():
                if isinstance(component_dict, dict):
                    for component_name, component_content in component_dict.items():
                        ref_key = f"#/components/{component_type}/{component_name}"
                        raw_components[ref_key] = copy.deepcopy(component_content)
        
        resolved_components = {}
        
        def __resolve_obj(obj, stack=None):
            """Разрешает ссылки в объекте с контролем стека"""
            if stack is None:
                stack = []
            
            if isinstance(obj, dict):
                # Если это словарь с одной ссылкой
                if "$ref" in obj and len(obj) == 1:
                    ref = obj["$ref"]
                    if ref in raw_components:
                        if ref in stack:
                            return {"type": "object"}  # рекурсия - заменяем на object
                        stack.append(ref)
                        resolved = raw_components[ref]
                        result = __resolve_obj(resolved, stack)
                        stack.pop()
                        return result
                    elif self.schema_infer_fallback:
                        raise KeyError(f"Источника '{ref}' нет в компонентах спецификации")
                
                result = {}
                for key, value in obj.items():
                    if key == "$ref" and isinstance(value, str):
                        # Обрабатываем ссылку внутри словаря
                        if value in raw_components:
                            if value in stack:
                                result[key] = {"type": "object"}  # рекурсия - заменяем на object
                            else:
                                stack.append(value)
                                resolved = raw_components[value]
                                result[key] = __resolve_obj(resolved, stack)
                                stack.pop()
                        elif self.schema_infer_fallback:
                            raise KeyError(f"Источника '{value}' нет в компонентах спецификации")
                    else:
                        result[key] = __resolve_obj(value, stack)
                return result
            
            elif isinstance(obj, list):
                return [__resolve_obj(item, stack) for item in obj]
            return obj
        
        for ref_key in raw_components.keys():
            resolved_components[ref_key] = __resolve_obj(raw_components[ref_key])
        
        return resolved_components

    

    def __convert_schema_to_sprkfrm(self,response_map,type_mapping):
        converter = OpenAPIToSparkConverter(type_mapping)
        spark_json_schema = converter.convert(response_map)
        return spark_json_schema
        

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
                            "name": "header",
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
                if i not in self.request.get('custom_header_variables'):
                    header_param = {
                                            "name": i,
                                            "nullable": True,
                                            "type": type_mapping.get(j,'string'),
                                            "metadata": {}
                                        }
                    header_template['fields'].append(header_param)
        else:
            header = header_template
        
        result = TEMPLATE.format(json.dumps(header),json.dumps(content))
        return json.loads(result) 

    def __check_schema_override(self,data,headers_fallback,type_mapping):
        if not isinstance(data, dict) or 'fields' not in data:
            raise('Неккоректная структура схемы.')
        has_content,has_header = False,False
        for field in data['fields']:
            if field.get('name') == 'header':
                has_header = True
            if field.get('name') == 'content':
                has_content = True
        if has_header and has_content:
            return data 
    

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

            template =  {"name": "header",
                                "nullable": True,
                                "type": {},
                                "metadata":{} }
            template["type"] = new_headers
            data['fields'].append(template)
        if not has_content:
            template =  {"name": "content",
                            "nullable": True,
                            "type": {},
                            "metadata":{} }
            template["type"] = self.__resolve_override_schema(data)
            #чистим первый уровень
            data["fields"] = [f for f in data["fields"] if f.get("name") == "header"]
            data['fields'].append(template)
            #остается еще поле вне content и header
        return data


    def __resolve_override_schema(self, data):
        #TEST: keep_header = 0 + schema_override not null, поле header дропаем, если есть,content распаковываем на первый уровень - уронить при конфликте имен
        if not isinstance(data, dict) or 'fields' not in data:
            raise Exception('Некорректная структура схемы.')
        
        new_fields = []
        content_fields = []
        
        for field in data['fields']:
            if field.get('name') == 'header':
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
            raise Exception("Конфликт имен полей")
        
        if len(new_fields) == 0:
                  return {"type": "struct",
                         "fields":[]}
        return {
            "type": "struct",
            "fields": new_fields
        }

    def get_schema(self,keep_headers,schema_override,headers_fallback,type_mapping,raw:bool = False):
        import json
        if not headers_fallback:
            headers_fallback = {}
        custom_header_variables = self.request.get('custom_header_variables',[]) #получаем список атрибутов хидера из спеки / + при schema_override = 1 этот список должен заполнится из schema_override
        if not isinstance(raw,bool):
            raise TypeError('Неподдерживаемый тип данных')
        if self.response_map is None:
            raise('В предложенной спецификации отсутствует раздел response.')
        
            #+Кейс 1. keep_header = 1 + schema_override not null , есть header и content - ничего не делаем
            #+Кейс 2. keep_header = 1 + schema_override not null , добавить content если нет
            #+Кейс 3. keep_header = 1 + schema_override not null , добавить header  если нет
            #+Кейс 4. keep_header = 0 + schema_override not null, поле header дропаем, если есть,content распаковываем на первый уровень - уронить при конфликте имен
            #+Кейс 5. keep_header = 0 + schema_override is null , возвращаем schema
            #+Кейс 6. keep_header = 1 + schema_override is null, добавляем header в соотстветвие с конфигурацией + (реальный header из спеки - мб их не будет)
            #+Кейс 7. keep_header = 1 + schema_override is null, raw = True  
            #+Кейс 8. keep_header = 0 + schema_override is null, raw = True  
        if raw: #без конфигурации, кейс #7-8
            if keep_headers:
                import copy
                header = copy.deepcopy(self.get_headers_map())
                if header is not None:
                    for i,j in headers_fallback.items():
                        if custom_header_variables:
                            if i not in custom_header_variables:
                                header['properties'].update({i:{'schema':{'type': j}}})
                            else:
                                properties[i] = {'schema':{'type': j}}
                else:
                    properties = {}
                    header = {'type': 'object','properties':{}}
                    for i,j in headers_fallback.items():
                        if custom_header_variables:
                            if i not in custom_header_variables:
                                properties[i] = {'schema':{'type': j}}
                        else:
                            properties[i] = {'schema':{'type': j}}
                    header['properties'] = properties
                return {'content':self.get_response_map(),'headers':header} 
            else:
                return self.get_response_map() #Кейс 8
        else:
            if not keep_headers:
                if schema_override:
                    return self.__resolve_override_schema(json.loads(schema_override)) # Кейс 4
                return self.getStructTypeSchema(type_mapping) # Кейс 5
            elif keep_headers:
                if schema_override: #Кейс 1-3
                    return self.__check_schema_override(json.loads(schema_override),headers_fallback,type_mapping)
                else:
                    return self.add_header_to_content(self.getStructTypeSchema(type_mapping),self.getStructTypeHeader(type_mapping),headers_fallback,type_mapping) #Кейс 6