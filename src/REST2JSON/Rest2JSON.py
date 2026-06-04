import os
import mimetypes
import io, base64
import copy 
import fsspec
import hashlib
import json
from urllib.parse import urlparse
from .utils.OASParser import OASParser
from .utils.BaseAdapter import BaseAdapter



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

class REST2JSON(BaseAdapter):
    """
    Основной класс для преобразования REST API ответов в JSON формат.
    Объединяет функциональность парсера OpenAPI спецификации и HTTP клиента.
    Тестируемый билд - функциональность изменена, подогнан для MVP

    
    """
    
    def __init__(self,transport, config: dict = None, stgman:any = None):
        """
        Инициализация REST2JSON конвертера.
        
        Args:
            config: Словарь с конфигурацией подключения к API. Содержит секции:
                - proc: параметры процесса загрузки (src, conn_params)
                - env: параметры окружения (json, type_mapping)
                - auth: параметры аутентификации (header, body)
        """
        # Инициализация транспорта
        if transport is None:
            raise ValueError("transport cannot be None")
        self.__transport = transport

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
        self.spec = None
        # Загрузка адаптера парсера
        self.__parser_adapter = None
        self.entity_config = None
        self.override_header_list = None
        self.base_url = None
        self.ready = False
        self.StypeSchema = None
        self.stgman = stgman


    def get_file(self, url):
        """
        используем транспорт чтобы получить файл
        """

        content = None
        try:
            with fsspec.open(url) as f:
                content = f.read()
            print(" Успешно")
        except Exception as e:
            print('')
            print("Ошибка:", repr(e))
            print("Тип ошибки:", type(e).__name__)
        return content

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
        try:
            if re.match(r'^\w+:(\/{2,3})\w', url):  # 2 или 3 /// после :
                parsed = urlparse(url)
                if parsed.scheme in ('http', 'https'):
                    for attempt in range(self.retries):
                        try:
                            print(f'Попытка чтения файла по ссылке {url}', end="")
                            response = self.get_file(url)
                            break
                        except:
                            print(f" неудачна")
                        if attempt == self.retries - 1:
                            print(f"Все попытки получения файла по ссылке {url} провалились, перехожу к обработке следующего url.")
                            return None
                    if response:
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
            auth_header, auth_body = auth.get('src', {}).get('header', {}) if auth.get('src', {}).get('header', {}) is not None else {}, {}
            if not auth_header:
                auth_body = auth.get('src', {}).get('body', {}) if auth.get('src', {}).get('body', {}) else {} 
            src_data = proc.get('src', {}).get('data', {})
            name = src.get('name', {})
            env_json=env.get('json', {}) if env.get('json') is not None else {}
            type_mapping = env_json.get('type_mapping', {})  if env.get('type_mapping') is not None else {}
            headers_fallback = env_json.get('headers_fallback', {})  if env.get('headers_fallback') is not None else {} # Задел для update
            type_mapping.update(src_data.get('type_mapping_override', {}))
            payload = src_data.get('payload', None)
            schema_override = src_data.get('schema_override', None)
            keep_headers = src_data.get('schema_keep_header', None)
            schema_infer_fallback = src_data.get('schema_infer_fallback', None)

            if proc_conn_params:
                endpoint_override = proc_conn_params.get('endpoint_override', None)
                method_override = proc_conn_params.get('method_override', None)
                timeout = proc_conn_params.get('timeout', None) if proc_conn_params.get('timeout') is not None else 3 # WinError 10035 при timeout = 0
                retries = proc_conn_params.get('retries', None) if proc_conn_params.get('retries') is not None else 1
                pagination = proc_conn_params.get('pagination', {}).get('enabled', None) if proc_conn_params.get('pagination') is not None else None
                page_param = proc_conn_params.get('pagination', {}).get('page_param', None) if proc_conn_params.get('pagination') is not None else None
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
       
    def add_header_to_content(self, content):
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
                            "name": "header",
                            "nullable": true,
                            "type": "string",
                            "metadata": {{}}
                        }},
                        {{
                            "name": "content",
                            "nullable": true,
                            "type": {0},
                            "metadata": {{}}
                        }}
                    ]
                }}
                '''
        
        result = TEMPLATE.format(json.dumps(content))
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

    def get_schema(self):
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
                 
        Returns:
            dict: Схема данных в формате Spark StructType JSON
            
        Raises:
            ValueError: Если спецификация не содержит схемы данных
            TypeError: При некорректных параметрах
        """
        import json
        if not self.headers_fallback:
            headers_fallback = {}
        if self.__parser_adapter.get_response_map() is None:
            raise ValueError('spec_url, spec_fallback: спецификация сервиса не содержит схемы ответа')
        
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
                    self.__parser_adapter.getStructTypeSchema(self.type_mapping)) 

    def prepare(self):
        """Подготовка адаптера к работе,
        пилот - просто запускаем парсер
        в планах сделать зависимость от полноты конфига
        Кроме того поместить получение спеки
        """
        #TODO: спеку получаем только тогда,когда соблюдены все условия
        # Получаем спецификацию
        self.spec = self._load_specification_(self.OpenAPISpecYAML, self.OpenAPISpecYAMLURL)
        #TODO: спеку парсим только тогда,когда соблюдены все условия
        # Загрузка адаптера парсера
        self.__parser_adapter = ParserAdapter(
            self.OpName, 
            self.endpoint_override, 
            self.method_override, 
            self.schema_infer_fallback, 
            self.spec
        )
        #TODO: Нужна вилка для источник-спека/источник-файл конфигурации
        self.__parser_adapter = self.__parser_adapter.get_parser()
        self.entity_config = self.__parser_adapter.request
        #TODO: все овверайд методы резолвить здесь же

        self.override_header_list = self.get_header_keys_from_override()
        self.base_url = self.__getbase_url(self.entity_config)


        self.StypeSchema = self.get_schema()
        #защита от запуска run без prepare()
        self.ready = True

    def run(self, ext_payload=None):
        '''
        Для теста contex эта функция пока не возвращает датафрейм
        '''
        if not self.ready:
            raise RuntimeError('Вы пытаетесь начать загрузку данных без подготовки адаптера.')
        #1 получаем данные,приземляем файлы
        self.get_data(ext_payload)
        #2 получаем StructType- схему из специ/конфигурации
        self.stgman.set_schema(self.StypeSchema)
        #TODO createDF() - заглушка для  формирования Датафрейма из JSON в Менеджере Контекста - Использует спарк из контекста
        return self.createDataFrame()
    
    def createDataFrame(self):
        from pyspark.sql.types import StructType
        #TODO Два адаптера на текущем этапе обрабатывают полученные данные по-своему, нужен свой динамический парсер-обработчик.
        #Архитектурно, stgman должен прочесть файлы и дать их адаптеру, но сейчас это memory_storage
        if not self.stgman.memory_storage:
            raise ValueError("Нет данных в staging для преобразования в DataFrame")
        if not self.stgman.spark:
            raise RuntimeError("В StagingManager не передана активная сессия Spark!")

        listval = [json.loads(value.decode('utf-8')) for value in self.stgman.memory_storage.values()]

        if self.stgman.schema:
            return self.stgman.spark.createDataFrame(listval, StructType.fromJson(self.stgman.schema))
        return self.stgman.spark.createDataFrame(listval)
    
    
    def get_data(self, ext_payload=None):
        """
        Основной метод для получения данных из API.
        
        Args:
            ext_payload: Данные для отправки (опционально, если не указан - используется payload из конфигурации)
            
        Returns:
           
        """
        #Когда попытались что-нибудь передать - обрабатываем именно то что передали (ext_payload)
        datatype = type(ext_payload).__name__  
        if datatype == 'NoneType':
            payload = self.payload
        else:
            payload = ext_payload
        # Строим обширный справочников для подключения и передачи данных в REST
        payload = self._prepare_payload(payload)
        #Запуск процесса приземления файлов в fs.
        self._execute(payload)
        
    def _prepare_payload(self, srcpayload):
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
        method = self.entity_config.get('method', 'GET').upper()
        url_template = f"{self.base_url}{self.entity_config.get('url', '')}"
        raw = copy.deepcopy(srcpayload) if srcpayload is not None else self.payload
        if raw is None:
            raw = [{}]
        # Приведение к списку словарей
        if isinstance(raw, dict):
            items = [raw]
        elif isinstance(raw, list):
            if len(raw) == 0:
                items = [{}]
            elif not all(isinstance(i, dict) for i in raw):
                raise ValueError('payload: ожидается list[dict]')
            else:
                items = raw
        else:
            raise ValueError('payload: некорректный формат: ожидается dict/list/NoneType')
        # Аутентификация через тело, если нет заголовков
        if not self.auth_header and self.auth_body:
            items = [{**item, **self.auth_body} for item in items]
        # Базовые заголовки
        headers = {**self.entity_config.get('headers', {}), **self.auth_header}
        # Формируем итоговый список запросов
        payload = []
        for item in items:
            try:
                url = url_template.format(**item)
            except KeyError:
                url = url_template
            request_info = {
                'method': method,
                'url': url,
            }
            if method in ('GET', 'DELETE'):
                request_info['params'] = item
            else:
                request_info['json'] = item
            if headers:
                request_info['headers'] = headers
            payload.append(request_info)
        return payload

    def _execute(self, payload_list):
        
        with self.__transport as tr:
            for item in payload_list:
                idx = hashlib.md5(json.dumps(item, sort_keys=True).encode()).hexdigest()
                for attempt in range(self.retries):
                    try:
                        resp = tr.request(**item)
                        resp.raise_for_status()
                        content_type = tr.get_header().get('Content-Type', '')
                        ext = mimetypes.guess_extension(content_type.split(';')[0]) or '.bin'
                        filename = f"{idx}{ext}"
                        with self.stgman.open_file(filename) as f:
                            if self.keep_headers: # временное решение в случае keep_headers,т.к чтобы сформировать нужную структуру нужно получить контент целико
                                buffer = io.BytesIO()
                                for chunk in resp.iter_content(chunk_size=8192):
                                    buffer.write(chunk)
                                content_bytes = buffer.getvalue() 
                                #TODO Нет решения. b'' не сериализуется,требуется ответ преобразовать в json(в строку,hex - неважно), далее снова в b'' с предварительным чтением всего тела
                                #такое решение не подходит для продакшена,сделана была загушка для MVP
                                content_bytes = json.loads(content_bytes.decode('utf-8'))
                                package = {
                                    "header": dict(tr.get_header()),
                                    "content": content_bytes
                                }
                                json_str = json.dumps(package).encode('utf-8')
                                f.write(json_str)
                            else:
                                for chunk in resp.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        break
                    except Exception as e:
                        print(f"Попытка {attempt + 1}/{self.retries} неудачна по причине: {e}")
                        if attempt == self.retries - 1:
                            raise KeyError(f'SRC: все {self.retries} попытки запроса провалились')
        return True
 