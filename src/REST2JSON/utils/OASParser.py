import re
from .utils import OpenAPIToSparkConverter
import copy
from typing import Any


# Теперь мы не парсим всю спеку - мы перебираем /path на предмет OperationID
# В противном случае - мы ищем спецификацию конкретной операции по endpoint,method(в случае если в endpoint содержатся несколько методов) и 
# На Вход получаем только словарь


class OASParser:
    def __init__(self, OpName:str = None, endpoint_url:str= None, method:str= None, schema_infer_fallback:bool = True, loaded_spec:str = None):
        """
        Парсер OpenAPI-спецификации
        
        Args:
            OpName: OperationID конкретного эндпоинта
            endpoint_url: ссылка на эндпоинт
            method: метод эндпоинта (GET, POST, PUT, DELETE и т.д.)
            schema_infer_fallback: Флаг, определяющий качество парсинга -- True - ошибки резолвинга игнорируются, False - ошибки вызывают исключения
            loaded_spec: текст спецификации в формате str
        """
        self.operation_Name = copy.copy(OpName)
        self.target_endpoint = copy.copy(endpoint_url)
        self.target_method = copy.copy(method)
        self.schema_infer_fallback = copy.copy(schema_infer_fallback)
        self.spec = self.open_spec(copy.deepcopy(loaded_spec))
        self.endpoint_base_url = None
        self.post = self.__parse_specification(self.__getEndpoint(self.spec))
        self.base_url = self.__getbaseurl(self.spec)
        
        ### Формируется структура без добавления кастомных данных
        # json для content и header
        self.endpoint_section = self.__resolve_refs_in_operation(copy.deepcopy(self.post), self.__extract_schemas(copy.deepcopy(self.spec)))
        self.request = self.__transform_spec_to_requests(self.endpoint_section)
        self.response_map = self.endpoint_section.get('response', None)
        self.headers_map = self.form_header(self.endpoint_section.get('headers', None))

    def open_spec(self, src):
        """
        Загрузка текста спецификации из строкового формата в структуру данных Python.
        
        Args:
            src: текст спецификации в формате str (YAML или JSON)
            
        Returns:
            dict: спецификация в формате словаря Python
            
        Raises:
            ValueError: если формат спецификации некорректен или не может быть распарсен
        """
        import yaml
        try:
            data = yaml.safe_load(src)
        except:
            raise ValueError("Некорректный формат спецификации.")
        return data

    def form_header(self, header_raw: dict):
        """
        Метод построения структуры заголовков в формат схемы OpenAPI.
        Преобразует сырые данные заголовков в стандартизированную структуру с типом 'object'.
        
        Args:
            header_raw: словарь с описанием заголовков из спецификации
            
        Returns:
            dict: структура в формате {'type': 'object', 'properties': {header_data}}
            None: если header_raw пустой или None
        """
        if header_raw:
            result = {'type': 'object', 'properties': None}
            result['properties'] = header_raw
            return result
        return None

    def getStructTypeSchema(self, type_mapping):
        """
        Метод получения структуры ответа в StructType-формате для Spark.
        Преобразует OpenAPI схему ответа в структуру, понятную Spark.
        
        Args:
            type_mapping: маппинг типов данных из конфигурации (OpenAPI типы -> Spark типы)
            
        Returns:
            dict: структура ответа в формате StructType JSON
        """
        return self.__convert_schema_to_sprkfrm(copy.deepcopy(self.response_map), type_mapping)
    
    def getStructTypeHeader(self, type_mapping):
        """
        Метод получения структуры заголовков в StructType-формате для Spark.
        Преобразует OpenAPI схему заголовков в структуру, понятную Spark.
        
        Args:
            type_mapping: маппинг типов данных из конфигурации (OpenAPI типы -> Spark типы)
            
        Returns:
            dict: структура заголовков в формате StructType JSON, либо пустой словарь если заголовки отсутствуют
        """
        if self.headers_map:
            return self.__convert_schema_to_sprkfrm(copy.deepcopy(self.headers_map), type_mapping)
        return {}
    
    def getSpecification(self):
        """
        Функция получения исходного текста спецификации OpenAPI.
        
        Returns:
            dict: полная спецификация в формате словаря Python
        """
        return self.spec
    
    def __findendpointbypath(self, spec_dict: dict) -> dict:
        """
        Поиск подструктуры спецификации по URL эндпоинта и HTTP методу.
        
        Args:
            spec_dict: полная спецификация в формате json/dict
            
        Returns:
            dict: словарь с единственным эндпоинтом в формате {method: endpoint_details}
            None: если эндпоинт с указанным URL и методом не найден
        """
        endpoints = spec_dict.get('paths', {})
        endpoint = endpoints.get(self.target_endpoint, None)
        if endpoint:
            for method, value in endpoint.items():
                if method == self.target_method:
                    return {method: value}
        return None

    def __findendpointbyOpId(self, spec_dict: dict) -> dict:
        """
        Поиск подструктуры спецификации по имени операции OperationID.
        При нахождении также сохраняет URL эндпоинта в self.target_endpoint.
        
        Args:
            spec_dict: полная спецификация в формате json/dict
            
        Returns:
            dict: словарь с единственным эндпоинтом в формате {method: endpoint_details}
            None: если операция с указанным OperationID не найдена
        """
        for path, methods in spec_dict.get('paths', {}).items():
            for method_name, method_details in methods.items():
                operation_id = method_details.get('operationId', None)
                if operation_id == self.operation_Name:
                    self.target_endpoint = path
                    return {method_name: method_details}
        return None

    def __getEndpoint(self, spec: dict) -> dict:
        """
        Основной метод поиска эндпоинта в спецификации.
        Сначала пытается найти по URL+методу, затем по OperationID.
        
        Args:
            spec: полная спецификация в формате json/dict
            
        Returns:
            dict: найденный эндпоинт в формате {method: endpoint_details}
            
        Raises:
            ValueError: если не удалось найти эндпоинт или не указаны параметры поиска
        """
        endpoint = None
        # Сначала проверяем по endpoint_url и method
        if self.target_endpoint and self.target_method:
            endpoint = self.__findendpointbypath(spec)
            if endpoint:
                return endpoint
        elif self.operation_Name:  # не нашли по endpoint+method (или их нет) - ищем по name
            endpoint = self.__findendpointbyOpId(spec)
            if endpoint:
                return endpoint
        else:
            raise ValueError('В конфигурации не указаны необходимые параметры: name или endpoint_override + method override.')
        
        # Проверка наличия данных для эндпоинта
        if endpoint is None:
            raise ValueError('По спецификации не удалось определить адрес для отправки запроса.')
        
        return endpoint

    def __resolve_refs_in_operation(self, operation_spec: dict, ref_dict: dict) -> dict:
        """
        Рекурсивно заменяет все ссылки $ref в спецификации операции на их фактические определения.
        
        Args:
            operation_spec: спецификация конкретной операции (эндпоинта)
            ref_dict: словарь со всеми определениями компонентов по их путям
            
        Returns:
            dict: спецификация операции с разрешенными ссылками
            
        Raises:
            KeyError: если ссылка $ref не найдена в ref_dict и schema_infer_fallback=False
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
                        elif not self.schema_infer_fallback:
                            raise KeyError(f"Не удалось сформировать схему данных на основе спецификации: не описан '{ref_path}' ")
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
                        elif not self.schema_infer_fallback:
                            raise KeyError(f"Не удалось сформировать схему данных на основе спецификации: не описан '{ref_path}' ")
                    else:
                        self.__resolve_refs_in_operation(item, ref_dict)
                elif isinstance(item, list):
                    self.__resolve_refs_in_operation(item, ref_dict)
        
        return operation_spec

    def __getbaseurl(self, spec_dict: dict):
        """
        Извлекает базовый URL сервера из спецификации OpenAPI.
        Обрабатывает сервера с переменными, подставляя значения по умолчанию.
        
        Приоритеты выбора:
        1. Если установлен self.endpoint_base_url - возвращает его
        2. Берет первый  сервер с валидными значениями по умолчанию для всех эндпоинтами
        
        Args:
            spec_dict: полная спецификация OpenAPI
            
        Returns:
            str: базовый URL сервера (без завершающего слеша), или пустая строка если сервера не указаны
        """
        if self.endpoint_base_url:
            return self.endpoint_base_url
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
        
        # Fallback: берем первый сервер и подставляем пустые значения
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
        Обрабатывает заголовки ответа, извлекая схему из каждого заголовка и разрешая ссылки.
        
        Args:
            headers_dict: словарь заголовков из спецификации OpenAPI
            
        Returns:
            dict: обработанные заголовки с разрешенными схемами, либо None если заголовков нет
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
    
    def __find_endpoint_server(self, endpoint_dict: dict):
        """
        Ищет определение сервера на уровне эндпоинта (переопределение глобального сервера).
        
        Args:
            endpoint_dict: словарь с описанием эндпоинта
            
        Returns:
            str: URL сервера для данного эндпоинта, либо None если не указан
        """
        for method_name, method_details in endpoint_dict.items():
            if isinstance(method_details, dict):
                server = method_details.get('servers', None)
                if server:  # TODO: брать весь список, а не 1-й элемент
                    if isinstance(server, list):
                        if isinstance(server[0], dict):
                            firstserv = server[0].get('url', '').rstrip('/')
                            return firstserv
                        else:
                            return server[0]
                    if isinstance(server, dict):
                        return server.get('url', '')
                    else:
                        return server
        return None

    def __parse_specification(self, endpoint_dict: dict) -> dict:
        """
        Парсит спецификацию конкретного эндпоинта, извлекая все необходимые компоненты:
        - путь и метод
        - параметры запроса (path, query)
        - тело запроса (request body)
        - схему ответа (response)
        - заголовки ответа (headers)
        - security требования
        - параметры из пути (path parameters)
        
        Args:
            endpoint_dict: словарь с эндпоинтом в формате {method: details}
            
        Returns:
            dict: структурированное описание эндпоинта с ключами:
                - path: URL путь
                - method: HTTP метод
                - response: схема ответа
                - headers: заголовки ответа
                - request_body: схема тела запроса
                - content: Content-Type
                - parameters: параметры запроса
                - reqref_params: параметры из пути
                - operationId: идентификатор операции
                - security: требования безопасности
        """
        result = {}
        self.endpoint_base_url = self.__find_endpoint_server(endpoint_dict)
        path = self.target_endpoint
        
        for method_name, method_details in endpoint_dict.items():
            method_upper = method_name.upper()
            if isinstance(method_details, dict):
                parameters = method_details.get('parameters', None)
                endpoint_data = {}
                method_security = method_details.get('security')
                method_responses = method_details.get('responses')
                
                if method_responses is not None:
                    # Добавляем схему ответа
                    response = method_details.get('responses')
                    if response is not None:
                        endpoint_data['response'] = self.__find_response_schema(response)
                        headers = response.get('200', {}).get('headers', {})  # пока только для 200
                        if headers:
                            endpoint_data['headers'] = self.__process_headers(headers)
                
                if method_security is not None:
                    endpoint_data['security'] = method_security
                
                request_body = method_details.get('requestBody', {})
                if request_body:
                    content = request_body.get('content', {})
                    if content:
                        content_type = next(iter(content))
                        content_details = content[content_type]
                        schema = content_details.get('schema', {})
                        endpoint_data.update({
                            'content': content_type,
                            'request_body': schema
                        })
                
                # Извлекаем параметры из пути (например, /users/{id})
                req_params = re.findall(r'\{(\w+)\}', path)
                if req_params:
                    param_list = []
                    for req_par in req_params:
                        param_list.append(req_par)
                    endpoint_data['reqref_params'] = param_list
                
                operation_id = method_details.get('operationId', None)
                endpoint_data['operationId'] = operation_id
                
                if parameters:
                    endpoint_data['parameters'] = parameters
                
                endpoint_data['method'] = method_upper
                endpoint_data['path'] = path
                result.update(endpoint_data)
        
        return result
    
    def __find_response_schema(self, obj: Any, depth: int = 0, max_depth: int = 15) -> dict | str | None:
        """
        Рекурсивно ищет "наиболее вероятную" схему ответа в OpenAPI спецификации.
        Обходит структуру в поисках schema или $ref.
        
        Args:
            obj: объект для поиска (часть спецификации OpenAPI)
            depth: текущая глубина рекурсии
            max_depth: максимальная глубина рекурсии (предотвращает бесконечную рекурсию)
            
        Returns:
            dict: если найден inline-схема
            str: если найден $ref (строка вида "#/components/schemas/...")
            None: если ничего не найдено
        """
        if depth > max_depth:
            return None

        if not isinstance(obj, (dict, list)):
            return None

        # Проверяем schema или $ref на текущем уровне
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                if isinstance(ref, str) and ref.startswith("#/"):
                    return ref  # возвращаем ref как есть — дальше можно резолвить

            if "schema" in obj and isinstance(obj["schema"], (dict, str)):
                return obj["schema"]

        # Типичные пути в OpenAPI, где может находиться схема
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

        # Обрабатываем oneOf / allOf / anyOf комбинаторы
        if isinstance(obj, dict):
            for combinator in ["oneOf", "allOf", "anyOf"]:
                if combinator in obj and isinstance(obj[combinator], list):
                    for variant in obj[combinator]:
                        if isinstance(variant, dict):
                            found = self.__find_response_schema(variant, depth + 1, max_depth)
                            if found is not None:
                                return found  # возвращаем первый найденный рабочий вариант

        # Рекурсия по всем вложенным словарям и спискам
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
        """
        Преобразует внутреннее представление спецификации эндпоинта в формат,
        готовый для использования в HTTP-запросах.
        
        Args:
            spec: внутреннее представление эндпоинта от __parse_specification
            
        Returns:
            dict: конфигурация запроса с ключами:
                - base_url: базовый URL сервера
                - method: HTTP метод
                - url: путь эндпоинта
                - headers: заголовки запроса (Content-Type, Accept)
                - auth_types: типы аутентификации
                - custom_header_variables: список кастомных заголовков для подстановки
        """
        request = {}
        try:
            path = spec.get("path", '')
            # Получаем метод
            method = spec.get("method", "GET").upper()
            base_url = spec.get("base_url", "")
            # Получаем путь
            url = spec["path"]

            headers = spec.get('headers', {})
            headers_params = []
            if headers:
                headers_params = headers.keys()
            
            # Формируем финальную конфигурацию
            request = {
                "base_url": self.base_url,
                "method": method,
                "url": url,
                "headers": {
                    "Content-Type": spec.get("content", ""),  # application/json
                    "Accept": ""  # application/json
                },
                "auth_types": spec.get("security", None),
                "custom_header_variables": sorted(list(headers_params)) if headers_params else [],
            }
            
        except Exception as e:
            print(f"Предупреждение: Ошибка обработки endpoint: {e}")
            import traceback
            traceback.print_exc()
        
        return request

    def get_response_map(self, ID: str = None):
        """
        Возвращает карту (схему) ответа для эндпоинта.
        
        Args:
            ID: необязательный идентификатор (зарезервировано для будущего использования)
            
        Returns:
            dict: схема ответа в формате OpenAPI
        """
        return self.response_map
    
    def get_headers_map(self, ID: str = None):
        """
        Возвращает карту (схему) заголовков ответа для эндпоинта.
        
        Args:
            ID: необязательный идентификатор (зарезервировано для будущего использования)
            
        Returns:
            dict: схема заголовков в формате OpenAPI
        """
        return self.headers_map
        
    def _get_request_config(self):
        """
        Внутренний метод для получения конфигурации запроса.
        Используется внутри класса для доступа к данным запроса.
        
        Returns:
            dict: конфигурация HTTP-запроса
        """
        return self.request

    def __extract_schemas(self, openapi_spec: dict):
        """
        Извлекает и резолвит все компоненты из секции components OpenAPI спецификации.
        Обрабатывает вложенные ссылки и предотвращает бесконечную рекурсию.
        
        Args:
            openapi_spec: полная спецификация OpenAPI
            
        Returns:
            dict: словарь всех компонентов с их путями в качестве ключей и разрешенными ссылками
            
        Raises:
            KeyError: если ссылка не найдена и schema_infer_fallback=False
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
            """
            Разрешает ссылки в объекте с контролем стека для предотвращения рекурсии.
            
            Args:
                obj: объект для обработки
                stack: стек обрабатываемых ссылок (для обнаружения циклов)
                
            Returns:
                обработанный объект с разрешенными ссылками
            """
            if stack is None:
                stack = []
            
            if isinstance(obj, dict):
                # Если это словарь с одной ссылкой
                if "$ref" in obj and len(obj) == 1:
                    ref = obj["$ref"]
                    if ref in raw_components:
                        if ref in stack:
                            return {"type": "object"}  # обнаружена рекурсия - заменяем на object
                        stack.append(ref)
                        resolved = raw_components[ref]
                        result = __resolve_obj(resolved, stack)
                        stack.pop()
                        return result
                    elif not self.schema_infer_fallback:
                        raise KeyError(f"Не удалось сформировать схему данных на основе спецификации: Источника '{ref}' нет в компонентах спецификации") 
                
                result = {}
                for key, value in obj.items():
                    if key == "$ref" and isinstance(value, str):
                        # Обрабатываем ссылку внутри словаря
                        if value in raw_components:
                            if value in stack:
                                result[key] = {"type": "object"}  # обнаружена рекурсия - заменяем на object
                            else:
                                stack.append(value)
                                resolved = raw_components[value]
                                result[key] = __resolve_obj(resolved, stack)
                                stack.pop()
                        elif not self.schema_infer_fallback:
                            raise KeyError(f"Не удалось сформировать схему данных на основе спецификации: Источника '{value}' нет в компонентах спецификации") 
                    else:
                        result[key] = __resolve_obj(value, stack)
                return result
            
            elif isinstance(obj, list):
                return [__resolve_obj(item, stack) for item in obj]
            return obj
        
        for ref_key in raw_components.keys():
            resolved_components[ref_key] = __resolve_obj(raw_components[ref_key])
        
        return resolved_components
    
    def __convert_schema_to_sprkfrm(self, response_map, type_mapping):
        """
        Преобразует OpenAPI схему в Spark StructType формат.
        
        Args:
            response_map: OpenAPI схема ответа или заголовков
            type_mapping: маппинг типов данных для конвертации
            
        Returns:
            dict: схема в формате Spark StructType JSON
        """
        converter = OpenAPIToSparkConverter(type_mapping)
        spark_json_schema = converter.convert(response_map)
        return spark_json_schema