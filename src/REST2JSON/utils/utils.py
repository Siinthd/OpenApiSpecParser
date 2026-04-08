from typing import Any, List, Dict, Optional,Tuple,Union

class OpenAPIToSparkConverter:
    """Конвертер OpenAPI схем в Spark StructType JSON формат без зависимости от PySpark"""

    def __init__(self,mapping_type: Dict[str, Any]):
        self.type_mapping = mapping_type or {}

    def convert(self,schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Конвертирует OpenAPI схему в Spark StructType JSON формат
        
        Args:
            schema: JSON схема из OpenAPI спецификации
            
        Returns:
            Схема в формате Spark StructType JSON
        """
        return self._convert_node(schema, "$")
    
    def _convert_node(self, node: Any, path: str) -> Any:
        """Рекурсивно конвертирует узел схемы"""
        
        # Обработка null/None
        if node is None:
            return "null"
        
        # Если узел - строка, это может быть тип или ссылка
        if isinstance(node, str):
            if node.startswith("#/"):  # Это ссылка
                return "string"  # Заглушка для ссылок
            return self._map_type(node)
        
        # Если узел - список (enum или anyOf/oneOf)
        if isinstance(node, list):
            return self._handle_array_node(node, path)
        
        # Если узел - словарь
        if isinstance(node, dict):
            return self._handle_dict_node(node, path)
        
        # Для неизвестных типов
        return "string"
    
    def _map_type(self, json_type: str) -> str:
        """Маппинг JSON типов в Spark типы"""
        return self.type_mapping.get(json_type, "string")
    
    def _handle_array_node(self, node: List, path: str) -> str:
        """Обрабатывает узлы-массивы"""
        # Для enum или anyOf/oneOf берем первый тип
        if node and isinstance(node[0], dict):
            return self._convert_node(node[0], f"{path}[0]")
        return "string"
    
    def _merge_all_of(self, schemas: List[Dict]) -> Dict[str, Any]:
        """
        Объединяет несколько схем из allOf в одну.
        Все схемы уже должны быть разрешены (без $ref).
        """
        merged = {}
        for schema in schemas:
            # Если внутри allOf есть вложенный allOf, объединяем его рекурсивно
            if "allOf" in schema:
                schema = self._merge_all_of(schema["allOf"])
            
            # Объединяем properties
            if "properties" in schema:
                merged.setdefault("properties", {}).update(schema["properties"])
            
            # Объединяем required (убираем дубли)
            if "required" in schema:
                merged.setdefault("required", []).extend(schema["required"])
                merged["required"] = list(set(merged["required"]))
            
            # Копируем остальные поля (type, nullable, enum, format, и т.д.)
            # При конфликте последний встреченный имеет приоритет
            for key, value in schema.items():
                if key not in ["properties", "required", "allOf"]:
                    merged[key] = value
        
        return merged
    
    def _collect_schemas(self, schemas: List[Dict], path: str) -> List[Any]:
        """
        обработка кейса oneOf/anyOf в список .
        """
        result = []
        for i, schema in enumerate(schemas):
            # Если внутри есть allOf, сначала объединяем его
            #if "allOf" in schema:
            #    schema = self._merge_all_of(schema["allOf"])
            converted = self._convert_node(schema, f"{path}.union[{i}]")
            #место под если any/oneof внутри 
            result.append(converted)
        return result
    
    def _handle_dict_node(self, node: Dict, path: str) -> Any:
        """Обрабатывает узлы-словари"""

        # Получаем тип узла
        node_type = node.get("type")

        # Обработка ссылок
        if "$ref" in node:
            return "string"  # В реальном проекте нужно резолвить ссылки

        # Обработка комбинированных схем
        for combo in ["allOf", "anyOf", "oneOf"]:
            if combo in node and node[combo]:
                return self._convert_node(node[combo][0], f"{path}.{combo}[0]")
            

        # if "allOf" in node and node["allOf"]:
        # #merged = self._merge_all_of(node["allOf"])
        # #return self._convert_node(merged, path)
        #     return {"allOf" :self._collect_schemas(node["allOf"], path)}
        #  # anyOf / oneOf пока оставляем как было (берём первый вариант) пока что
        # if "anyOf" in node and node["anyOf"]:
        #     return {"anyOf" : self._collect_schemas(node["anyOf"], path)}
        # if "oneOf" in node and node["oneOf"]:
        #     return {"oneOf" : self._collect_schemas(node["oneOf"], path)}

        # Обработка в зависимости от типа
        if node_type == "array" or "items" in node:
            return self._handle_array_type(node, path)
        elif node_type == "object" or "properties" in node:
            return self._handle_object_type(node, path)
        else:
            # Примитивный тип
            return self._handle_primitive_type(node, path)
        
    
    def _handle_array_type(self, node: Dict, path: str) -> Dict[str, Any]:
        """Обрабатывает массив"""
        items = node.get("items", {})
        
        # Определяем тип элементов
        if isinstance(items, list):
            element_result = "string"
        else:
            element_result = self._convert_node(items, f"{path}[]")
        
        result = {
            "type": "array",
            "containsNull": node.get("nullable", False),
            "elementType": element_result  # element_result уже содержит правильную структуру
        }
        
        return result
    
    def _handle_object_type(self, node: Dict, path: str) -> Dict[str, Any]:
        """Обрабатывает объект"""
        properties = node.get("properties", {})
        required_fields = node.get("required", [])
        if not isinstance(required_fields,list):
            required_fields = []
        
        fields = []
        for prop_name, prop_schema in properties.items():
            # Определяем nullable
            nullable = prop_name not in required_fields
            
            # Конвертируем тип поля
            field_result = self._convert_node(prop_schema, f"{path}.{prop_name}")
            
            # Обрабатываем результат в зависимости от его типа
            field_type = field_result
            field_metadata = None
            # Если результат - словарь и содержит metadata с format
            if isinstance(field_result, dict) and "metadata" in field_result:
                field_type = field_result["type"]
                field_metadata = field_result.get("metadata",None)
            # Если результат - строка, просто используем её как тип
            
            field = {
                "name": prop_name,
                "nullable": nullable,
                "type": field_type,
                "metadata": {}
            }
            
            if field_metadata:
                field["metadata"] = field_metadata
            
            fields.append(field)
        
        # Сортируем поля для консистентности
        fields.sort(key=lambda x: x["name"])
        
        return {
            "type": "struct",
            "fields": fields
        }
    
    def _handle_primitive_type(self, node: Dict, path: str) -> Any:
        """Обрабатывает примитивный тип"""
        node_type = node.get("type", "string")
        node_format = node.get("format")
        
        spark_type = self._map_type(node_type)

        # Собираем все остальные поля в metadata
        metadata = {}
        for key, value in node.items():
            if key not in ["type", "nullable","name"]:  # Исключаем уже обработанные поля
                if value is not None:
                    metadata[key] = value
        
        # Если есть метаданные или формат, возвращаем словарь
        if metadata or node_format:
            return {
                "type": spark_type,
                "metadata": metadata
            }
        
        return spark_type
    
    def extract_response_schema(openapi_spec: Dict[str, Any], 
                               path: str, 
                               method: str,
                               status_code: str = "200") -> Optional[Dict[str, Any]]:
        """
        Извлекает схему ответа из OpenAPI спецификации
        
        Args:
            openapi_spec: OpenAPI спецификация
            path: путь эндпоинта
            method: HTTP метод
            status_code: код ответа
            
        Returns:
            JSON схема ответа или None
        """
        try:
            operation = openapi_spec.get("paths", {}).get(path, {}).get(method.lower(), {})
            responses = operation.get("responses", {})
            response = responses.get(status_code, {})
            content = response.get("content", {})
            
            # Ищем application/json или первый попавшийся content type
            for content_type, content_schema in content.items():
                if "application/json" in content_type or content_type.startswith("application/"):
                    schema = content_schema.get("schema", {})
                    return schema
            
            return None
        except Exception as e:
            print(f"Ошибка при извлечении схемы: {e}")
            return None


