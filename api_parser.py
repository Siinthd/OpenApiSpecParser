import yaml
import json
from pprint import pprint
from yaml.loader import SafeLoader
import requests
import re

def get_headers() -> dict:
        """Возвращает заголовки для запроса"""
        return {
            "accept": "text/plain",
            "Content-Type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
        }


class OpenAPIParser:

    def __init__(self, specs: any):
        #self.spec = self._proccess(self.__load__(specs))
        self.spec = self.__load__(specs)
        self.schemas = self.extract_schemas_with_payloads(self.spec)
        self.post = self._parse_post(self.spec)
        self.api_version = None
        self.api_description = None

    def __load__(self,specs:any) ->dict:
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
    
    def get_raw(self) -> dict:
        return self.spec
    
    def get_post(self) -> dict:
        return self.post
    
    def get_endpoints(self):
        return self.schemas
    
    def _parse_post(self, spec_dict: dict) -> dict:
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
                        if not server_list:
                            server_list = server_vars.get('default',None)

                for method_name, method_details in methods.items():
                    method_upper = method_name.upper()
                    # Используем полный путь как ключ
                    endpoint_data = {
                        'path': full_path  # Используем полный путь с базовым URL
                    }
                    if isinstance(method_details,dict):
                        method_security = method_details.get('security')
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
                                if schema.get('$ref'):
                                    schema = self.schemas[schema.get('$ref')]
                                endpoint_data.update({
                                    'content': content_type,
                                    'schema': schema
                                })
                        if re.findall(r'\{(\w+)\}', path) :
                            param_list = []
                            parameters = method_details.get('parameters', [])
                            for parameter in parameters:
                                    parameter_name = parameter.get('name')
                                    if parameter_name:
                                        param_list.append(parameter_name)
                            endpoint_data['requirement_parameters'] = param_list
                        if server_list:
                            endpoint_data['servers'] = server_list
                        operation_id = method_details.get('operationId', '')
                        if operation_id:
                            endpoint_data['operationId'] = operation_id
                        
                        if full_path not in result:
                            result[full_path] = {}
                        endpoint_data['method'] = method_upper
                        result[full_path].update(endpoint_data)
        
        return result


    def _schema_to_payload(self, schema: dict) -> dict:
        """Преобразует одну схему в payload структуру"""
        if schema.get('type') != 'object':
            return {}
        
        payload = {}
        properties = schema.get('properties', {})
        required_fields = schema.get('required', [])
        
        for prop_name in properties.items():
            # Добавляем только required поля
            if prop_name in required_fields:
                # Всегда пустая строка для всех полей
                payload[prop_name] = ""
        
        return payload

    def extract_schemas_with_payloads(self, spec_dict: dict) -> dict:
        """
        Извлекает все схемы из components.schemas и преобразует их в payload
        Возвращает словарь {полный_ref: payload}
        """
        if 'components' not in spec_dict:
            return {}
        
        if 'schemas' not in spec_dict['components']:
            return {}
        
        schemas = spec_dict['components']['schemas']
        payloads = {}
        
        for schema_name, schema in schemas.items():
            full_ref = f"#/components/schemas/{schema_name}"           
            payload = self._schema_to_payload(schema)
            payloads[full_ref] = payload
        
        return payloads
    


class UniversalRESTAdapter:
    """
    Docstring for UniversalRESTAdapter
    На вход подается (пока имя файла) со спеками openapi,
    внутри есть парсер, который выдает словарь с точкой,хидером и нагрузкой

    !!!Есть API с пагинацией,
    !!!есть API с заданием конкретного параметра - надо их определять и разделять
    """
    def __init__(self,filename:str):
        self.filename = filename
        self.data = ''
        self._read_metadata()
        
    def __str__(self):
        return f"OpenAPI version: {self.rawdata['openapi']}" 
        
    def __repr__(self):
        return str(type(self.data))

    
    def _handle_error(self):
        pass

    "валидация"
    def _validate_metadata(self,data):

        """
        Docstring for _validate_metadata
        
        :param self: Description
        :param data: dictionary with openapi specs
        validate OpenAPI dict with openapi_spec_validator module
        """
       # return(validate(data))
        return data

    def _read_metadata(self):

        """
        Docstring for _read_metadata
        
        :param self: Description
        
        """
        self.data = OpenAPIParser(self.filename)
        self.post = self.data.get_post()
        self.rawdata = self.data.get_raw()
        self._validate_metadata(self.data)

    def _print(self):
        pprint(self.data.get_post())

    def formatted_print(self):
        pprint(self.data.get)

if __name__ == "__main__":
    test = UniversalRESTAdapter('C:/Users/kdenis/mu_code/ex4.yaml')
    test._print()
    with open("C:/Users/kdenis/mu_code/output.json", "w", encoding="utf-8") as f:
        json.dump(test.data.get_post(), f, indent=4, ensure_ascii=False)

    '''
    ex3.yaml
    Untitled-2.json
    pagi.yaml
    ex4.yaml
    ex4.yaml
    '''
