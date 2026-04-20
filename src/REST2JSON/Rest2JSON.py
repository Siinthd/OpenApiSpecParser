import os
from urllib.parse import urlparse
from .utils.OASParser import OASParser
from .URESTClient import URESTClient


class ParserAdapter(OASParser):
    """
    Адаптер для парсера OpenAPI спецификации.
    Реализует ленивую инициализацию парсера для отложенного создания экземпляра.
    """
    
    def __init__(self, OpName, endpoint_url, method, schema_infer_fallback, spec):
        """
        Инициализация адаптера парсера.
        
        Args:
            OpName: Имя операции (OperationID) для поиска в спецификации
            endpoint_url: URL эндпоинта для запроса
            method: HTTP метод (GET, POST, PUT, DELETE и т.д.)
            schema_infer_fallback: Флаг, определяющий поведение при ошибках резолвинга ссылок
            spec: Текст OpenAPI спецификации в формате строки
        """
        self._parser = None
        self.spec = spec
        self.OpName = OpName
        self.endpoint_url = endpoint_url
        self.schema_infer_fallback = schema_infer_fallback
        self.method = method
    
    def get_parser(self):
        """
        Получение экземпляра парсера с ленивой инициализацией.
        Создает парсер при первом вызове и возвращает сохраненный экземпляр при последующих.
        
        Returns:
            OASParser: Экземпляр парсера OpenAPI спецификации
        """
        if self._parser is None:
            self._parser = OASParser(
                self.OpName, 
                self.endpoint_url, 
                self.method, 
                self.schema_infer_fallback, 
                self.spec
            )
        return self._parser


class ClientAdapter(URESTClient):
    """
    Адаптер для HTTP клиента.
    Наследует URESTClient и передает параметры для инициализации клиента.
    """
    
    def __init__(self, entity, extra_headers, base_url, timeout):
        """
        Инициализация адаптера клиента.
        
        Args:
            entity: Конфигурация сущности (эндпоинта) от парсера
            extra_headers: Дополнительные заголовки для запросов
            base_url: Базовый URL сервера
            timeout: Таймаут для HTTP запросов в секундах
        """
        super().__init__(entity, extra_headers, base_url, timeout)


class REST2JSON:
    """
    Основной класс для преобразования REST API ответов в JSON формат.
    Объединяет функциональность парсера OpenAPI спецификации и HTTP клиента.
    Поддерживает контекстный менеджер для автоматического управления соединениями.
    """
    
    def __init__(self, config: dict = None):
        """
        Инициализация REST2JSON конвертера.
        
        Args:
            config: Словарь с конфигурацией подключения к API. Содержит секции:
                - proc: параметры процесса загрузки (src, conn_params)
                - env: параметры окружения (json, type_mapping)
                - auth: параметры аутентификации (header, body)
        """
        # Загружаем конфигурацию
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
        
        # Получаем спецификацию
        self.spec = self._load_specification_(self.OpenAPISpecYAML, self.OpenAPISpecYAMLURL)
        
        # Загрузка адаптера парсера
        self.__parser_adapter = ParserAdapter(
            self.OpName, 
            self.endpoint_override, 
            self.method_override, 
            self.schema_infer_fallback, 
            self.spec
        ).get_parser()

        self.entity_config = self.__parser_adapter.request
        self.override_header_list = self.get_header_keys_from_override()
        
        self.base_url = self.__getbase_url(self.entity_config)
        
        # Инициализация клиента
        self.__client_adapter = ClientAdapter(
            self.entity_config, 
            self.auth_header, 
            self.base_url, 
            self.timeout
        )
        self.__in_context = False  # Флаг состояния контекстного менеджера

    def __enter__(self):
        """
        Вход в контекстный менеджер.
        Инициализирует HTTP клиент и устанавливает соединение.
        
        Returns:
            REST2JSON: Экземпляр текущего объекта для использования в контексте
            
        Raises:
            RuntimeError: Если контекстный менеджер уже активен
        """
        if self.__in_context:
            raise RuntimeError("Объект клиента уже создан и используется.")
        self.__client_adapter.__enter__()
        self.__in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Выход из контекстного менеджера.
        Закрывает HTTP клиент и освобождает ресурсы.
        
        Args:
            exc_type: Тип исключения (если было)
            exc_val: Значение исключения
            exc_tb: Трассировка исключения
            
        Returns:
            bool: False для проброса исключений дальше
        """
        self.__in_context = False
        self.__client_adapter.__exit__(exc_type, exc_val, exc_tb)
        return False

    def _load_specification_(self, src, url):
        """
        Загрузка OpenAPI спецификации из различных источников.
        Приоритет: сначала URL, затем локальный файл (src).
        
        Args:
            src: Локальный путь к файлу спецификации или текст спецификации
            url: URL(ы) для загрузки спецификации (строка или список)
            
        Returns:
            str: Текст спецификации в формате строки
            
        Raises:
            ValueError: Если не удалось загрузить спецификацию ни из одного источника
        """
        if url:
            if isinstance(url, list):
                for position in url:
                    specification_text = self._get_specfromurl(position)
                    if specification_text:
                        return specification_text
            else:
                specification_text = self._get_specfromurl(url)
                if specification_text:
                    return specification_text
        if src:  # Если по ссылкам ничего получить не удалось
            print('Не указаны ссылки на файл спецификации, читаем spec_fallback')
            return src
        raise ValueError("В конфигурации не указан источик спецификации сервиса.")
        
    def _get_specfromurl(self, url):
        """
        Загрузка спецификации из указанного URL.
        Поддерживает протоколы HTTP, HTTPS и FILE.
        
        Args:
            url: URL для загрузки (http://, https://, file://)
            
        Returns:
            str: Текст спецификации, либо None если загрузка не удалась
        """
        import requests, yaml, re
        response = None
        attempts = 0
        try:
            if re.match(r'^\w+:(\/{2,3})\w', url):  # 2 или 3 /// после :
                parsed = urlparse(url)
                if parsed.scheme in ('http', 'https'):
                    for attempt in range(self.retries):
                        try:
                            print(f'Попытка чтения файла по ссылке {url}', end="")
                            response = requests.get(url, timeout=self.timeout)
                            response.raise_for_status()
                            response.encoding = response.apparent_encoding or 'utf-8'
                            response = response.text
                            break
                        except:
                            print(f" неудачна")
                        if attempt == self.retries - 1:
                            print(f"Все попытки получения файла по ссылке {url} провалились, перехожу к обработке следующего url.")
                            return None
                    if response:
                        print(' успешна')
                        return response
                elif parsed.scheme == 'file':
                    path_part = url.replace('file://', '', 1)
                    # Запрещенные символы в ссылке на файл
                    forbidden = ['..', '~', '$', ';', '|', '&', '`', '\\']
                    if any(x in path_part for x in forbidden):
                        raise ValueError("В ссылке на файл обнаружены потенциально опасные символы")
                    abs_path = os.path.abspath(path_part)  # Преобразование относительного пути в абсолютный
                    # Проверка существования и доступности файла
                    if os.path.isfile(abs_path) and os.access(abs_path, os.R_OK):
                        print(f'Попытка чтения файла по ссылке {abs_path}', end="")
                        response = open(abs_path, 'r', encoding='utf-8').read()
                    else:
                        print(f'Не удалось найти указанный файл: {abs_path}')
                        return None
                else:
                    print(f'Неподдерживаемый протокол: {url}')
                    return None
                if response:
                    print(' успешна')
                    return response
            else:
                print(f'Указан некорректный префикс: {url}')
                return None
            print(f'Не удалось прочитать файл по ссылке: {url}')
            return None
        except requests.exceptions.RequestException as e:
            print(f'Попытка чтения файла по ссылке окончилась ошибкой: {e}')
            return None
        except yaml.YAMLError as e:
            print(e)
            return None
        
    def __getbase_url(self, entity_config):
        """
        Определение базового URL для запросов.
        Приоритет: base_override из конфигурации > base_url из спецификации > пустая строка.
        
        Args:
            entity_config: Конфигурация сущности от парсера
            
        Returns:
            str: Базовый URL сервера
        """
        base_url = entity_config.get("base_url", None)
        if self.base_override:
            return self.base_override
        elif base_url:
            return base_url
        else:
            return ''

    def __load_configuration(self, config):
        """
        Загрузка и разбор конфигурации из переданного словаря.
        Извлекает все параметры для работы REST2JSON конвертера.
        
        Args:
            config: Словарь с конфигурацией
            
        Returns:
            tuple: Кортеж с параметрами конфигурации:
                - payload: Данные для отправки в запросе
                - base_override: Переопределение базового URL
                - spec_fallback: Локальная спецификация (фолбэк)
                - spec_url: URL(ы) спецификации
                - auth_header: Заголовки аутентификации
                - auth_body: Тело аутентификации
                - name: Имя операции
                - retries: Количество попыток запроса
                - endpoint_override: Переопределение эндпоинта
                - method_override: Переопределение метода
                - timeout: Таймаут запроса
                - pagination: Флаг пагинации
                - page_param: Параметр страницы для пагинации
                - type_mapping: Маппинг типов данных
                - schema_override: Переопределение схемы
                - keep_headers: Флаг сохранения заголовков
                - headers_fallback: Фолбэк заголовков
                - schema_infer_fallback: Флаг обработки ошибок схемы
        """
        try:
            proc = config.get('proc', {})
            env = config.get('env', {})
            auth = config.get('auth', {})
            src = proc.get('src', {})
            proc_conn_params = src.get('conn_params', {})
            auth_header, auth_body = auth.get('src', {}).get('header', {}), {}
            if not auth_header:
                auth_body = auth.get('src', {}).get('body', {})
            src_data = proc.get('src', {}).get('data', {})
            name = src.get('name', {})
            type_mapping = env.get('json', {}).get('type_mapping', {})
            headers_fallback = env.get('json', {}).get('headers_fallback', {})  # Задел для update
            type_mapping.update(src_data.get('type_mapping_override', {}))
            payload = src_data.get('payload', None)
            schema_override = src_data.get('schema_override', None)
            keep_headers = src_data.get('schema_keep_headers', None)
            schema_infer_fallback = src_data.get('schema_infer_fallback', None)
            
            if proc_conn_params:
                endpoint_override = proc_conn_params.get('endpoint_override', None)
                method_override = proc_conn_params.get('method_override', None)
                timeout = proc_conn_params.get('timeout', None) if proc_conn_params.get('timeout') is not None else 3 # WinError 10035 при timeout = 0
                retries = proc_conn_params.get('retries', None) if proc_conn_params.get('retries') is not None else 1
                pagination = proc_conn_params.get('pagination', {}).get('enabled', None)
                page_param = proc_conn_params.get('pagination', {}).get('page_param', None)
                spec_url = proc_conn_params.get('spec_url', None)
                spec_fallback = proc_conn_params.get('spec_fallback', None)
                base_override = proc_conn_params.get('base_override', None)
                
            return (payload, base_override, spec_fallback, spec_url, auth_header, 
                    auth_body, name, retries, endpoint_override, method_override, 
                    timeout, pagination, page_param, type_mapping, schema_override, 
                    keep_headers, headers_fallback, schema_infer_fallback)
        except Exception as e:
            print(e)
                
    def get_header_keys_from_override(self):
        """
        Парсинг schema_override из конфигурации для извлечения ключей заголовков.
        Ищет в схеме поле 'headers' и извлекает все имена полей из него.
        
        Ожидаемая структура schema_override:
        {
            "type": "struct",
            "fields": [
                {"name": "content", "type": {}},
                {"name": "headers", "type": "struct", "fields": [
                    {"name": "key1", ...},
                    {"name": "key2", ...}
                ]}
            ]
        }
        
        Returns:
            list: Список имен полей заголовков, извлеченных из схемы
            
        Raises:
            TypeError: Если schema_override не может быть преобразован в JSON
        """
        import json
        result = []
        try:
            if self.schema_override:
                schema = json.loads(self.schema_override)
                if schema.get('type') == 'struct':
                    main_field = schema.get('fields')
                    if main_field and isinstance(main_field, list):
                        header_struct = next((f for f in main_field if f.get("name") == "headers"), None)
                        if isinstance(header_struct, dict):
                            param_list = header_struct.get('type', {}).get('fields', [])
                            result = [j.get('name') for j in param_list]
        except:
            TypeError('Не удалось преобразовать schema_override в формат JSON')
        return result

    def _prepare_payload(self, data):
        """
        Подготовка payload для отправки в запросе.
        Преобразует данные в единый формат (список словарей) и добавляет данные аутентификации.
        
        Args:
            data: Исходные данные (dict, list или None)
            
        Returns:
            list: Подготовленный список словарей для отправки
            
        Raises:
            ValueError: Если payload имеет недопустимый тип или структуру
        """
        import copy
        payload = copy.deepcopy(data)  # На этот момент payload должен быть списком словарей
        datatype = type(payload).__name__
        if datatype not in ('list', 'dict', 'NoneType'):
            raise ValueError('payload: некорректный формат: ожидается dict/list/NoneType')
        if isinstance(payload, list):
            if len(payload) > 0:
                if not (len(set(map(type, payload))) <= 1 and type(payload[0]) == dict):
                    raise ValueError('payload: некорректный формат: ожидается list[dict]')
            else:
                payload = [{}]
        elif isinstance(payload, dict):
            payload = [payload]
        else:
            payload = [{}]
        
        # Добавляем аутентификацию (приоритет - header)
        if not self.auth_header and self.auth_body:
            payload = [{**value, **self.auth_body} for value in payload]
        return payload
    
    def __direct(self, payload):
        """
        Выполнение прямого запроса к API с использованием методов _get/_post.
        
        Args:
            payload: Данные для отправки (один словарь или список словарей)
            
        Returns:
            list: Список ответов от API
        """
        got_list = False
        result = []
        if isinstance(payload, list):
            data_list = self._prepare_payload(payload)
            got_list = True
        else:
            data_list = self._prepare_payload(payload)
        try:
            http_client = self.__client_adapter.client
            for data in data_list:
                # Определяем метод из конфига
                method = self.__client_adapter.config.get('method', 'GET').upper()
                
                # Формируем URL с подстановкой параметров из пути
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
                    if isinstance(response, dict):
                        return [response]
                    else:
                        return response
                result.append(response)
            return result
        except Exception as e:
            return None

    def get_data(self, data=None):
        """
        Основной метод для получения данных из API.
        
        Args:
            data: Данные для отправки (опционально, если не указан - используется payload из конфигурации)
            
        Returns:
            list: Результаты запросов к API
        """


        datatype = type(data).__name__  # Явная проверка на наличие аргумента в вызове метода
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
        
    def _execute(self, data):
        """
        Выполнение запросов к API с обработкой заголовков и retry логикой.
        
        Args:
            data: Список словарей с данными для отправки
            
        Returns:
            list: Список результатов запросов (содержимое или структура {content, headers})
        """
        results = []
        for item in data:
            for attempt in range(self.retries):
                try:
                    content, header = self.__client_adapter.execute(item)
                    if self.keep_headers:
                        answer = {'content': content}
                        headers = {}
                        custom_header_variables = self.entity_config.get('custom_header_variables', [])
                        if custom_header_variables and not self.override_header_list:
                            header_variables = custom_header_variables
                        elif self.override_header_list:
                            header_variables = self.override_header_list
                        else:
                            if isinstance(self.headers_fallback, dict):
                                header_variables = self.headers_fallback.keys()
                            else:
                                header_variables = []
                        for i in header_variables:
                            header_data = header.get(i, {})
                            if header_data:
                                headers.update({i: header_data})
                        answer['headers'] = headers
                        results.append(answer)
                    else:
                        results.append(content)
                    break #следующий элемент
                except RuntimeError as e: 
                    raise RuntimeError(e)
                except Exception as e:
                    print(f"Попытка {attempt + 1}/{self.retries} неудачна: {e}")
                    if attempt == self.retries - 1:
                        raise KeyError(f'SRC: все {self.retries} попытки запроса провалились')
        return results
    
    def close(self):
        """
        Закрытие соединения и освобождение ресурсов.
        Принудительно закрывает HTTP клиент и сбрасывает флаг контекста.
        """
        if self.__in_context:
            self.__in_context = False
            self.__client_adapter.close()
            
    def add_header_to_content(self, content, header):
        """
        Создание структуры данных, объединяющей заголовки и содержимое.
        Используется для кейса №6 (keep_headers = 1 + schema_override is null).
        
        Args:
            content: Схема содержимого ответа
            header: Схема заголовков ответа
            
        Returns:
            dict: Объединенная схема в формате:
                {
                    "type": "struct",
                    "fields": [
                        {"name": "headers", "type": {...}},
                        {"name": "content", "type": {...}}
                    ]
                }
        """
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
            fields = header.get('fields', [])
            fields += header_template.get('fields', [])
            header['fields'] = fields
        elif self.headers_fallback:
            for i, j in self.headers_fallback.items():
                if i not in self.override_header_list:
                    header_param = {
                        "name": i,
                        "nullable": True,
                        "type": self.type_mapping.get(j, 'string'),
                        "metadata": {}
                    }
                    header_template['fields'].append(header_param)
            header = header_template
        else:
            header = header_template
        
        result = TEMPLATE.format(json.dumps(header), json.dumps(content))
        return json.loads(result)

    def __check_schema_override(self, schema):
        """
        Проверка и дополнение переопределенной схемы.
        Добавляет отсутствующие секции headers и content в схему.
        
        Args:
            schema: Схема в формате Spark StructType JSON
            
        Returns:
            dict: Дополненная схема
            
        Raises:
            KeyError: Если schema имеет некорректный формат
        """
        if not isinstance(schema, dict) or 'fields' not in schema:
            raise TypeError('schema_override: некорректный формат параметра, ожидается схема DataFrame в json-формате')
        
        has_content, has_header = False, False
        for field in schema['fields']:
            if field.get('name') == 'headers':
                has_header = True
            if field.get('name') == 'content':
                has_content = True
        
        if has_header and has_content:
            return schema
        
        # Добавляем заголовки если их нет
        if not has_header:
            header_template = {
                "type": "struct",
                "fields": []
            }
            if self.headers_fallback:
                for i, j in self.headers_fallback.items():  # Конвертируем типы
                    header_param = {
                        "name": i,
                        "nullable": True,
                        "type": self.type_mapping.get(j, 'string'),
                        "metadata": {}
                    }
                    header_template['fields'].append(header_param)

            new_headers = header_template
            template = {
                "name": "headers",
                "nullable": True,
                "type": {},
                "metadata": {}
            }
            template["type"] = new_headers
            schema['fields'].append(template)
        
        # Добавляем содержимое если его нет
        if not has_content:
            template = {
                "name": "content",
                "nullable": True,
                "type": {},
                "metadata": {}
            }
            template["type"] = self.__resolve_override_schema(schema)
            # Очищаем первый уровень - оставляем только headers
            schema["fields"] = [f for f in schema["fields"] if f.get("name") == "headers"]
            # Добавляем к headers секцию content
            schema['fields'].append(template)
        
        return schema

    def __resolve_override_schema(self, schema):
        """
        Разрешение переопределенной схемы с распаковкой содержимого.
        Извлекает поля из секции content и поднимает их на верхний уровень,
        удаляя секцию headers при необходимости (keep_headers = 0).
        
        Args:
            schema: Схема в формате Spark StructType JSON
            
        Returns:
            dict: Обработанная схема с распакованным содержимым
            
        Raises:
            KeyError: При конфликте имен полей или некорректном формате схемы
        """
        if not isinstance(schema, dict) or 'fields' not in schema:
            raise TypeError('schema_override: некорректный формат параметра, ожидается схема DataFrame в json-формате')
        #TODO создается верхнеуровневая структра типа struct, на будущее проверить, как дела обстоят, если content начинается именно с array/возможны проблемы в будущем
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
        
        # Проверка на конфликт имен
        existing_names = [f['name'] for f in new_fields]
        unique = set(existing_names)
        if len(existing_names) != len(unique):
            raise KeyError("schema_override: после распаковки схема содержит дубликаты корневых полей")
        
        if len(new_fields) == 0:
            return {
                "type": "struct",
                "fields": []
            }
        
        return {
            "type": "struct",
            "fields": new_fields
        }

    def get_schema(self, raw: bool = False):
        """
        Получение схемы данных ответа API.
        Поддерживает различные кейсы обработки заголовков и содержимого.
        
        Кейсы:
        1. keep_headers=1 + schema_override not null - есть header и content, ничего не делаем
        2. keep_headers=1 + schema_override not null - добавляем content если нет
        3. keep_headers=1 + schema_override not null - добавляем header если нет
        4. keep_headers=0 + schema_override not null - удаляем header, распаковываем content
        5. keep_headers=0 + schema_override is null - возвращаем schema
        6. keep_headers=1 + schema_override is null - добавляем header из конфигурации
        7. keep_headers=1 + schema_override is null, raw=True
        8. keep_headers=0 + schema_override is null, raw=True
        
        Args:
            raw: Если True - возвращает сырую схему из спецификации, 
                 если False - применяет трансформации согласно конфигурации
                 
        Returns:
            dict: Схема данных в формате Spark StructType JSON
            
        Raises:
            ValueError: Если спецификация не содержит схемы данных
            TypeError: При некорректных параметрах
        """
        import json
        if not self.headers_fallback:
            headers_fallback = {}
        if not isinstance(raw, bool):
            raise TypeError('raw: некорректный тип входного параметра, ожидается bool')
        if self.__parser_adapter.get_response_map() is None:
            raise ValueError('spec_url, spec_fallback: спецификация сервиса не содержит схемы ответа')
        
        if raw:  # Без конфигурации, кейсы #7-8
            custom_header_variables = self.entity_config.get('custom_header_variables', [])
            properties = {}
            if self.keep_headers:
                import copy
                header = copy.deepcopy(self.__parser_adapter.get_headers_map())
                if header is not None:
                    for i, j in headers_fallback.items():
                        if custom_header_variables:
                            if i not in custom_header_variables:
                                header['properties'].update({i: {'schema': {'type': j}}})
                            else:
                                properties[i] = {'schema': {'type': j}}
                else:
                    header = {'type': 'object', 'properties': {}}
                    for i, j in self.headers_fallback.items():
                        if custom_header_variables:
                            if i not in custom_header_variables:
                                properties[i] = {'schema': {'type': j}}
                        else:
                            properties[i] = {'schema': {'type': j}}
                    header['properties'] = properties
                return {'content': self.__parser_adapter.get_response_map(), 'headers': header}
            else:
                return self.__parser_adapter.get_response_map()  # Кейс 8
        else:
            if not self.keep_headers:
                if self.schema_override:
                    try:
                        schema = json.loads(self.schema_override)
                        return self.__resolve_override_schema(schema)  # Кейс 4
                    except:
                        raise TypeError('schema_override: некорректный формат параметра, ожидается схема DataFrame в json-формате')
                return self.__parser_adapter.getStructTypeSchema(self.type_mapping)  # Кейс 5
            elif self.keep_headers:
                if self.schema_override:  # Кейсы 1-3
                    try:
                        schema = json.loads(self.schema_override)
                        return self.__check_schema_override(schema)
                    except:
                        raise TypeError('schema_override: некорректный формат параметра, ожидается схема DataFrame в json-формате')
                else:
                    return self.add_header_to_content(
                        self.__parser_adapter.getStructTypeSchema(self.type_mapping),
                        self.__parser_adapter.getStructTypeHeader(self.type_mapping)
                    )  # Кейс 6