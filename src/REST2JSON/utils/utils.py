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
        required = node.get("required", [])
        
        fields = []
        for prop_name, prop_schema in properties.items():
            # Определяем nullable
            nullable = prop_name not in required
            
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
    
    @staticmethod
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



#Отложено
def skeletonize(obj, is_schema=False):
    if obj is None:
        return "null"
    
    if isinstance(obj, dict):
        is_collection = False
        if not is_schema and len(obj) > 1:
            dict_values = [v for v in obj.values() if isinstance(v, dict)]
            if len(dict_values) > len(obj.values()) / 2:
                is_collection = True
        
        if is_collection:
            first_key = next(iter(obj))
            return {"collection": skeletonize(obj[first_key], is_schema)}
        
        result = {}
        for key, value in obj.items():
            if key in ['facets', 'geo_regions'] and isinstance(value, dict) and not value:
                continue
            result[key] = skeletonize(value, is_schema)
        return result if result else "object"
    
    elif isinstance(obj, list):
        if len(obj) > 0:
            return {"array": skeletonize(obj[0], is_schema)}
        else:
            return {"array": "empty"}
    
    else:
        if isinstance(obj, str):
            return "string"
        elif isinstance(obj, (int, float)):
            return "number"
        elif isinstance(obj, bool):
            return "boolean"
        else:
            return type(obj).__name__


def compare_skeletons(skel1, skel2, path=""):
    if skel1 is None and skel2 is None:
        return 1.0
    if skel1 is None or skel2 is None:
        return 0.0
    
    if isinstance(skel1, str) and isinstance(skel2, str):
        if skel1 == skel2:
            return 1.0
        if skel1 in ("int", "float", "number") and skel2 in ("int", "float", "number"):
            return 1.0
        if skel1 == "null" or skel2 == "null":
            return 0.5
        return 0.0
    
    if isinstance(skel1, str) or isinstance(skel2, str):
        return 0.3
    
    if isinstance(skel1, dict) and isinstance(skel2, dict):
        special_keys = {"array", "collection", "object"}
        
        keys1 = set(skel1.keys())
        keys2 = set(skel2.keys())
        
        for key in special_keys:
            if key in keys1 and key in keys2:
                return compare_skeletons(skel1[key], skel2[key])
        
        all_keys = keys1 | keys2
        
        if not all_keys:
            return 1.0
        
        total_score = 0.0
        matched_keys = 0
        
        for key in all_keys:
            if key in keys1 and key in keys2:
                score = compare_skeletons(skel1[key], skel2[key])
                total_score += score
                matched_keys += 1
            else:
                total_score += 0.2
                matched_keys += 1
        
        return total_score / matched_keys if matched_keys > 0 else 0.0
    
    return 0.0


def has_data(response, schema, threshold=0.6):
    data_skeleton = skeletonize(response)
    schema_skeleton = skeletonize(schema, is_schema=True)
    similarity = compare_skeletons(data_skeleton, schema_skeleton)
    
    def has_container(skel):
        if isinstance(skel, dict):
            if "array" in skel or "collection" in skel:
                return True
            for value in skel.values():
                if has_container(value):
                    return True
        return False
    
    return similarity >= threshold and has_container(data_skeleton)