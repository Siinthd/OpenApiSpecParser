from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseAdapter(ABC):
    """
    Базовый абстрактный класс для конвертации REST API ответов в структурированные данные.
    Определяет минимальный контракт для наследников.
    """
    
    @abstractmethod
    def prepare(self, data: Any = None) -> List[Any]:
        """
        Подготовка адаптера к работе
        
        Args:
            data: Данные для отправки в запросе. Если None - используется 
                  payload из конфигурации
            
        Returns:
            List[Any]: Список результатов запросов к API
            
        Raises:
            RuntimeError: При ошибках выполнения запросов
            KeyError: При исчерпании попыток запроса
        """
        pass
    
    @abstractmethod
    def run(self, raw: bool = False) -> Dict[str, Any]:
        """
        Получение схемы данных ответа API.
        
        Args:
            raw: Если True - возвращает схему из спецификации без трансформаций,
                 если False - применяет трансформации согласно конфигурации 
                 (обработка заголовков, переопределение схемы)
            
        Returns:
            Dict[str, Any]: Схема данных в формате Spark StructType JSON
            
        Raises:
            ValueError: Если спецификация не содержит схемы данных
            TypeError: При некорректных параметрах или формате schema_override
        """
        pass