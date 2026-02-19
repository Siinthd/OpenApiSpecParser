import yaml
import json
from pprint import pprint
from yaml.loader import SafeLoader
import re
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
'''
TODO:
добавить base_url в спеку
'''


logging.basicConfig(level=logging.ERROR) 
COUNTER = 0

class OASParser:

    def __init__(self, specs: any):
        self.spec = self._load_specification_(specs)
        self.schemas = self.extract_schemas_with_payloads(self.spec)
        self.post = self._parse_specification(self.spec)
        self.request = self._transform_spec_to_requests(self.post)
        self.api_version = self.spec.get('openapi')

    def _load_specification_(self,specs:any) ->dict:
        logging.info('_load_specification_')
        if isinstance(specs, dict):
            return specs
        content = specs
        #Если это строка
        if isinstance(specs, str) and specs.strip().startswith(('{', '[')):
            content = specs
        else:
            try:
                with open(specs, 'r', encoding='utf-8') as f:
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
    
    def _resolve_refs_in_operation(self, operation_spec: dict,ref_dict : dict) -> dict:
        logging.info('_resolve_refs_in_operation')
        """
        Заменяет $ref в параметрах операции.
        """
        if isinstance(operation_spec, dict):
            for key, value in list(operation_spec.items()):
                if isinstance(value, dict):
                    # Если нашли словарь с $ref
                    if "$ref" in value and isinstance(value["$ref"], str) and value["$ref"] in ref_dict:
                        # Заменяем весь словарь на содержимое схемы
                        operation_spec[key] = ref_dict[value["$ref"]]
                    else:
                        # Рекурсивно обрабатываем дальше
                        self._resolve_refs_in_operation(value, ref_dict)
                elif isinstance(value, list):
                    self._resolve_refs_in_operation(value, ref_dict)
        elif isinstance(operation_spec, list):
            for i, item in enumerate(operation_spec):
                if isinstance(item, dict):
                    if "$ref" in item and isinstance(item["$ref"], str) and item["$ref"] in ref_dict:
                        # Заменяем элемент списка на содержимое схемы
                        operation_spec[i] = ref_dict[item["$ref"]]
                    else:
                        self._resolve_refs_in_operation(item, ref_dict)
                elif isinstance(item, list):
                    self._resolve_refs_in_operation(item, ref_dict)
        
        return operation_spec

    def _parse_specification(self, spec_dict: dict) -> dict:
        logging.info('_parse_specification')
        result = {}
        servers = spec_dict.get('servers', [])
        server_list = []
        for path, methods in spec_dict.get('paths', {}).items():
            for server in servers:
                base_url = server.get('url', '').rstrip('/')
                full_path = f"{base_url}{path}" if base_url else path
                match = re.findall(r'\{(\w+)\}', base_url)
                if match:
                    for var in match:
                        server_vars = server.get('variables','').get(var,None)
                        server_list = server_vars.get('enum',[])
                        server_variable = var
                        if not server_list:
                            server_list = server_vars.get('default',None)

                for method_name, method_details in methods.items():
                    method_upper = method_name.upper()
                    if isinstance(method_details,dict):
                        parameters =  method_details.get('parameters',None)
                        endpoint_data = {
                            'path': full_path }
                        method_security = method_details.get('security')
                        method_responses = method_details.get('responses')
                        if method_responses is not None:
                            # Добавить схему ответа
                            response = self.__parse_response(method_responses)
                            if response is not None:
                                endpoint_data['response'] = response

                        if method_security is not None:
                            # Используем security из метода
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
                        req_params = re.findall(r'\{(\w+)\}', path)
                        if req_params :
                            param_list = []
                            for req_par in req_params:
                                param_list.append(req_par)
                            endpoint_data['reqref_params'] = param_list
                        if server_list:
                            endpoint_data[server_variable] = server_list
                        operation_id = method_details.get('operationId', '')
                        match =  re.search(r'https?://([^/\s]+)', server.get('url'))
                        server_id = ''
                        if match:
                            server_id = '_'.join(match.group(1).split('.')[:-1])

                        if operation_id:
                            endpoint_data['operationId'] = operation_id
                        else:
                            path_id = re.findall(r'\{(\w+)\}', path)
                            operation_id = f"{server_id}_{method_name}_by_{'_'.join(path_id)}" if path_id else path.split('/')[-1]
                            endpoint_data['operationId'] = operation_id    
                        
                        if operation_id not in result:
                            result[operation_id] = {}
                        if parameters:
                            endpoint_data['parameters'] = parameters
                        endpoint_data['method'] = method_upper
                        result[operation_id].update(endpoint_data)
        return self._resolve_refs_in_operation(result,self.schemas)

    def _transform_spec_to_requests(self, api_spec: dict) -> dict:
        logging.info('_transform_spec_to_requests')
        requests_map = {}
        
        for operation_id, spec in api_spec.items():
            try:
                path = spec.get("path", '')
                key = operation_id or (path.split('/')[-1] or "root")
                
                # Получаем метод
                method = spec.get("method", "GET").upper()
                
                # Получаем путь
                url = spec["path"]
                
                # Собираем все переменные
                all_variables = set()
                required_variables = set()
                
                # 1. Path параметры из parameters
                parameters = spec.get("parameters", [])
                for param in parameters:
                    if isinstance(param, dict):
                        param_name = param.get("name")
                        param_in = param.get("in")
                        param_required = param.get("required", False)
                        
                        if param_name and param_in in ("path","header"):
                            all_variables.add(param_name)
                            if param_required:
                                required_variables.add(param_name)
                
                # 2. Path параметры из reqref_params
                reqref_params = spec.get("reqref_params", [])
                for param in reqref_params:
                    if isinstance(param, str):
                        all_variables.add(param)
                        required_variables.add(param)
                    elif isinstance(param, dict):
                        param_name = param.get("name")
                        if param_name:
                            all_variables.add(param_name)
                            required_variables.add(param_name)
                
                # 3. Path переменные из URL
                import re
                path_vars = re.findall(r'\{([^}]+)\}', url)
                for var in path_vars:
                    all_variables.add(var)
                    required_variables.add(var)
                
                # 4. Query параметры из parameters
                for param in parameters:
                    if isinstance(param, dict):
                        param_name = param.get("name")
                        param_in = param.get("in")
                        param_required = param.get("required", False)
                        
                        if param_name and param_in == "query":
                            all_variables.add(param_name)
                            if param_required:
                                required_variables.add(param_name)
                
                # 5. Параметры из request_body
                request_body = spec.get("request_body", {})
                
                def extract_body_params(body_spec, parent_path="", skip_parent=False):
                    """
                    Извлекает имена параметров из body
                    skip_parent: True если нужно пропустить имя родительского контейнера
                    """
                    params = set()
                    required_params = set()
                    
                    if not body_spec or not isinstance(body_spec, dict):
                        return params, required_params
                    
                    # Проверяем наличие properties (для объектов)
                    if "properties" in body_spec:
                        properties = body_spec.get("properties", {})
                        required_fields = body_spec.get("required", [])
                        
                        for prop_name, prop_schema in properties.items():
                            # Формируем полное имя параметра
                            if skip_parent:
                                # Если нужно пропустить родителя, используем только имя свойства
                                full_name = prop_name
                            elif parent_path:
                                full_name = f"{parent_path}.{prop_name}"
                            else:
                                full_name = prop_name
                            
                            # Добавляем параметр
                            params.add(full_name)
                            
                            # Проверяем required
                            if prop_name in required_fields:
                                required_params.add(full_name)
                            
                            # Рекурсивно обрабатываем вложенные объекты
                            if isinstance(prop_schema, dict):
                                prop_type = prop_schema.get("type")
                                
                                # Если это объект с properties
                                if prop_type == "object" and "properties" in prop_schema:
                                    nested_params, nested_required = extract_body_params(
                                        prop_schema,
                                        parent_path=full_name,
                                        skip_parent=False
                                    )
                                    params.update(nested_params)
                                    required_params.update(nested_required)
                                
                                # Если это массив объектов
                                elif prop_type == "array" and "items" in prop_schema:
                                    items = prop_schema["items"]
                                    if isinstance(items, dict) and items.get("type") == "object" and "properties" in items:
                                        nested_params, nested_required = extract_body_params(
                                            items,
                                            parent_path=f"{full_name}[*]",
                                            skip_parent=False
                                        )
                                        params.update(nested_params)
                                        required_params.update(nested_required)
                    
                    # Если это не объект с properties, а просто словарь с полями
                    else:
                        for field_name, field_schema in body_spec.items():
                            if isinstance(field_schema, dict) and 'type' in field_schema:
                                # Формируем полное имя
                                if skip_parent:
                                    full_name = field_name
                                elif parent_path:
                                    full_name = f"{parent_path}.{field_name}"
                                else:
                                    full_name = field_name
                                
                                # Добавляем параметр
                                params.add(full_name)
                                
                                # Проверяем required
                                if field_schema.get("required", False):
                                    required_params.add(full_name)
                                
                                # Рекурсивно обрабатываем вложенные объекты
                                field_type = field_schema.get("type")
                                if field_type == "object" and "properties" in field_schema:
                                    nested_params, nested_required = extract_body_params(
                                        field_schema,
                                        parent_path=full_name,
                                        skip_parent=False
                                    )
                                    params.update(nested_params)
                                    required_params.update(nested_required)
                                elif field_type == "array" and "items" in field_schema:
                                    items = field_schema["items"]
                                    if isinstance(items, dict):
                                        if items.get("type") == "object" and "properties" in items:
                                            nested_params, nested_required = extract_body_params(
                                                items,
                                                parent_path=f"{full_name}[*]",
                                                skip_parent=False
                                            )
                                            params.update(nested_params)
                                            required_params.update(nested_required)
                    
                    return params, required_params
                
                # Извлекаем параметры из body
                if request_body:
                    body_params = set()
                    body_required = set()
                    
                    # Проверяем структуру request_body
                    if "properties" in request_body:
                        properties = request_body.get("properties", {})
                        
                        # Обрабатываем каждое поле верхнего уровня
                        for prop_name, prop_schema in properties.items():
                            # Проверяем, является ли это поле контейнером параметров (например, "params")
                            if (isinstance(prop_schema, dict) and 
                                prop_schema.get("type") == "object"):
                                
                                # Получаем все поля внутри этого объекта
                                if "properties" in prop_schema:
                                    # Это объект с properties - обрабатываем его поля как параметры верхнего уровня
                                    container_params, container_required = extract_body_params(
                                        prop_schema,
                                        skip_parent=True  # Пропускаем имя контейнера
                                    )
                                    body_params.update(container_params)
                                    body_required.update(container_required)
                                else:
                                    # Это объект без properties - возможно, поля на верхнем уровне
                                    for field_name, field_schema in prop_schema.items():
                                        if isinstance(field_schema, dict) and 'type' in field_schema:
                                            # Добавляем поле как параметр верхнего уровня
                                            body_params.add(field_name)
                                            if field_schema.get("required", False):
                                                body_required.add(field_name)
                            else:
                                # Обычное поле не-контейнер
                                field_params, field_required = extract_body_params(
                                    {prop_name: prop_schema}
                                )
                                body_params.update(field_params)
                                body_required.update(field_required)
                    else:
                        # Если нет properties, пробуем обработать как есть
                        body_params, body_required = extract_body_params(request_body)
                    
                    all_variables.update(body_params)
                    required_variables.update(body_required)
                    
                
                # Формируем финальную конфигурацию
                requests_map[key] = {
                    "operationalId": key,
                    "method": method,
                    "url": url,
                    "headers": {
                        "Content-Type": spec.get("content", "application/json"),
                        "Accept": "application/json"
                    },
                    "auth_types": spec.get("security", None),
                    "variables": sorted(list(all_variables)) if all_variables else [],
                    "required": sorted(list(required_variables)) if required_variables else []
                }
                
                # Отладка
                
            except Exception as e:
                print(f"Предупреждение: Ошибка обработки endpoint '{operation_id}': {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return requests_map

    def get_response(self,ID:str = None): 
        response = {}
        if ID:
            entity = self.post.get(ID)
            if not entity:
                raise ValueError(f"Endpoint '{entity}' не найден в конфигурации")
            response = entity.get('response',{})
        else:
            for key,entity in  self.post.items():
                response[key] = entity.get('response',{})
        return response

    def _get_request_config(self):
        return self.request
    
    def __parse_response(self,data:dict) -> dict:
        logging.info('__parse_response')
        result = {}
        for response_code,response_value in data.items():
            if isinstance(response_value,dict):
                result[response_code] = self.__find_schema(response_value)
        return result
            
    def __find_schema(self,data:dict):
        logging.info('__find_schema')
        if isinstance(data, dict):
            if 'schema' in data:
                return data['schema']
            for value in data.values():
                result = self.__find_schema(value)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self.__find_schema(item)
                if result is not None:
                    return result
        return None

    def _schema_to_payload(self, schema: dict) -> dict:
        """Преобразует одну схему в payload структуру"""
        payload = {}
        composite_types = ['oneOf', 'anyOf', 'allOf']
        
        # Определяем тип схемы
        schema_type = schema.get('type')
        
        # Если это объект
        if schema_type == 'object':
            properties = schema.get('properties', {})
            required_fields = schema.get('required', [])
            
            if properties:
                for prop_name, prop_schema in properties.items():
                    # Инициализируем базовую структуру для свойства
                    prop_payload = {
                        'name': prop_name,
                        'required': prop_name in required_fields,
                        'nullable': prop_schema.get('nullable', False),
                    }
                    
                    # Добавляем type, format, items если они есть
                    if 'type' in prop_schema:
                        prop_payload['type'] = prop_schema['type']
                    if 'format' in prop_schema:
                        prop_payload['format'] = prop_schema['format']
                    if 'items' in prop_schema:
                        prop_payload['items'] = prop_schema['items']
                    if '$ref' in prop_schema:
                        prop_payload['$ref'] = prop_schema['$ref']
                    
                    # Обрабатываем составные типы
                    for comp_type in composite_types:
                        if comp_type in prop_schema:
                            comp_value = prop_schema[comp_type]
                            if isinstance(comp_value, list):
                                # Сохраняем ссылки как есть, они будут разыменованы позже
                                prop_payload[comp_type] = [
                                    item.get('$ref', item) if isinstance(item, dict) else item 
                                    for item in comp_value
                                ]
                    
                    payload[prop_name] = prop_payload
            else:
                # Обработка случая, когда нет properties
                for key, value in schema.items():
                    if key in composite_types:
                        if isinstance(value, list):
                            payload[key] = [
                                item.get('$ref', item) if isinstance(item, dict) else item 
                                for item in value
                            ]
        
        # Если это параметр (имеет name и schema)
        elif 'name' in schema and 'schema' in schema and isinstance(schema['schema'], dict):
            param_name = schema['name']
            param_schema = schema['schema']
            param_required = schema.get('required',None)
            
            payload[param_name] = {
                'name': param_name,
                'required': param_required,
                'nullable': param_schema.get('nullable',None),
                'type': param_schema.get('type',None),
                'format': param_schema.get('format',None),
                'items': param_schema.get('items',None),
            }
            if '$ref' in param_schema:
                payload[param_name]['$ref'] = param_schema['$ref']
        
        # Если это другой тип данных (string, array и т.д.)
        elif schema_type:
            payload['value'] = {
                'name': 'value',
                'required': True,
                'nullable': schema.get('nullable', None),
                'type': schema_type,
                'format': schema.get('format', None),
                'items': schema.get('items', None),
            }
            if '$ref' in schema:
                payload['value']['$ref'] = schema['$ref']
        
        return payload

    def extract_schemas_with_payloads(self, spec_dict: dict) -> dict:
        logging.info('extract_schemas_with_payloads')
        """
        Извлекает все схемы из всех разделов components и преобразует их в payload
        Возвращает словарь {полный_ref: payload}
        """
        if 'components' not in spec_dict:
            return {}
        
        components = spec_dict['components']
        payloads = {}
        
        # Сначала собираем все схемы
        for section_name, section_content in components.items():
            if not isinstance(section_content, dict):
                continue
            for item_name, item_data in section_content.items():
                full_ref = f"#/components/{section_name}/{item_name}"
                if isinstance(item_data, dict):
                    payload = self._schema_to_payload(item_data)
                    if payload:
                        payloads[full_ref] = payload
        
        def __resolve_refs(obj, visited=None, path=""):
            if visited is None:
                visited = set()
            
            if isinstance(obj, dict):
                # Сохраняем метаданные текущего объекта
                metadata = {}
                if 'name' in obj:
                    metadata['name'] = obj['name']
                if 'required' in obj:
                    metadata['required'] = obj['required']
                if 'nullable' in obj:
                    metadata['nullable'] = obj['nullable']
                
                # Проверяем, есть ли ссылка для разыменования
                ref = obj.get('$ref')
                if ref and isinstance(ref, str) and ref in payloads and ref not in visited:
                    visited.add(ref)
                    resolved = payloads[ref]
                    
                    # Разыменовываем вложенные ссылки в resolved
                    resolved = __resolve_refs(resolved, visited, path + "->" + ref)
                    
                    # Если resolved - это словарь, объединяем с метаданными
                    if isinstance(resolved, dict):
                        result = resolved.copy()
                        # Добавляем метаданные на верхний уровень, если их нет в resolved
                        for key, value in metadata.items():
                            if key not in result:
                                result[key] = value
                        return result
                
                # Обрабатываем составные типы (oneOf, anyOf, allOf)
                result = {}
                for key, value in obj.items():
                    if key in ['oneOf', 'anyOf', 'allOf'] and isinstance(value, list):
                        # Для составных типов разыменовываем каждый элемент
                        resolved_list = []
                        for item in value:
                            if isinstance(item, str):
                                # Если это строка-ссылка
                                if item in payloads and item not in visited:
                                    visited_copy = visited.copy()
                                    visited_copy.add(item)
                                    resolved_item = payloads[item]
                                    resolved_item = __resolve_refs(resolved_item, visited_copy, path + "->" + item)
                                    resolved_list.append(resolved_item)
                                else:
                                    resolved_list.append(item)
                            elif isinstance(item, dict):
                                # Если это словарь с возможной ссылкой
                                resolved_item = __resolve_refs(item, visited.copy(), path)
                                resolved_list.append(resolved_item)
                            else:
                                resolved_list.append(item)
                        result[key] = resolved_list
                    elif key != '$ref':  # Не обрабатываем саму ссылку повторно
                        result[key] = __resolve_refs(value, visited.copy(), path)
                
                # Добавляем сохраненные метаданные, если их нет в результате
                for key, value in metadata.items():
                    if key not in result:
                        result[key] = value
                
                return result if result else metadata
            
            elif isinstance(obj, list):
                # Рекурсивно обрабатываем все элементы списка
                result = []
                for i, item in enumerate(obj):
                    if isinstance(item, str) and item.startswith('#/components/'):
                        # Если это строка-ссылка в списке
                        if item in payloads and item not in visited:
                            visited_copy = visited.copy()
                            visited_copy.add(item)
                            resolved_item = payloads[item]
                            resolved_item = __resolve_refs(resolved_item, visited_copy, path + "->" + item)
                            result.append(resolved_item)
                        else:
                            result.append(item)
                    else:
                        result.append(__resolve_refs(item, visited.copy(), path))
                return result
            
            else:
                return obj
        
        resolved_payloads = {}
        
        for ref, payload in payloads.items():
            resolved_payloads[ref] = __resolve_refs(payload)
        
        return resolved_payloads


if __name__ == "__main__":

    
    parser = OASParser('C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/accuweather.yaml')

    entity  = parser.request.get()
  