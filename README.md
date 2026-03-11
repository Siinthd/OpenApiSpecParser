# REST2JSON


Адаптер для преобразования REST API ответов в JSON с поддержкой OpenAPI (Swagger) спецификаций. 
Предоставляет удобный интерфейс для работы с API через контекстный менеджер, автоматическую загрузку токенов и валидацию ответов.

  
## Особенности

- Гибкая конфигурация через OmegaConf
- Загрузка OpenAPI спецификаций из файлов (YAML/JSON) или по URL
- Пакетная обработка запросов с подготовкой payload
- Поддержка контекстного менеджера для безопасного управления ресурсами
- Генерация JSON Schema из OpenAPI спецификации


## Установка

```bash
pip install git+https://github.com/Siinthd/OpenApiSpecParser.git
```


## Быстрый старт


### Простой запрос
```Python
from rest2json import REST2JSON
from omegaconf import DictConfig

  

config = DictConfig({
    "spec_data": "openapi.yaml",
    "spec_url": None,
    "Token_src": "tokens.json",
    "name": "getUser",
    "endpoint_url": "/users/{userId}",
    "method": "GET",
    "pagination": False,
    "page_param": None,
    "base_url": "https://api.example.com"
})


adapter = REST2JSON(config)
response = adapter.get_response({"userId": 123})
print(response)

  

```

### Использование с контекстным менеджером
```Python
with REST2JSON(config) as adapter:
	 # Работа с адаптером
    response = adapter.get_response({"userId": 123})
    print(response)
    # Автоматическое закрытие соединений
```

### Пакетная обработка
```Python
with REST2JSON(config) as adapter:
    users = [{"userId": 123}, {"userId": 456}, {"userId": 789}]
    results = adapter.get_response(users)
    for result in results:
        print(result)
```

  

## Конфигурация

### Структура конфигурации
```python
config = DictConfig({
    # OpenAPI спецификация
    "spec_data": "path/to/spec.yaml",  # или None если используется URL
    "spec_url": "https://api.example.com/openapi.yaml",  # или None если используется файл
    "Token_src": "tokens.json",  # путь к файлу с токенами
    "name": "operation_name",  # имя операции из OpenAPI
    "endpoint_url": "/endpoint/{param}",  # шаблон URL
    "method": "GET",  # HTTP метод (GET/POST)
    "pagination": False,  # включить пагинацию
    "page_param": "page",  # параметр страницы для пагинации
    "base_url": "https://api.example.com"  # базовый URL API
})
```

###  Файл токенов (tokens.json)
```json
    "base_url":
    {
    "Authorization":  "Token {Token}}",
    "X-Secret": "{X-Secret}}"
    }
```

## API Reference

### Класс `REST2JSON`

Основной класс для работы с API.

#### Методы

##### `get_response(data=None)`

Основной метод для выполнения запросов. Автоматически управляет контекстом.

**Параметры:**

- `data` - Данные для запроса. Может быть:
    
    - `None` - запрос без параметров
        
    - `dict` - одиночный запрос
        
    - `list[dict]` - пакет запросов
        
    - `str/int` - одиночное значение (будет преобразовано в параметр required)
        

**Возвращает:** JSON ответ от API или список ответов при пакетной обработке.

##### `get_StructTypeFormatSchema()`

Возвращает схему структуры данных из OpenAPI спецификации.

##### `get_JSONTypeschema()`

Возвращает JSON Schema ответа из спецификации.


## Обработка данных

### Подготовка payload
required должен быть определен в OpenAPI-спецификации и быть единственным обязательным параметром:
#### Пример 

```yaml
requestBody:
    content:
       application/json:
         schema:
			required:
				- query
			type: object
			properties:
				count:
					type: integer
					format: int32
					nullable: true
					default: 10
				locations:
					type: array
					nullable: true
					items:
						$ref: "#/components/schemas/LocationCode"
				locations_boost:
					type: array
					nullable: true
					items:
						$ref: "#/components/schemas/LocationCode"
				query:
					type: string
				status:
					type: array
					nullable: true
					items:
						type: string
						enum:
							- ACTIVE
							- LIQUIDATING
							- LIQUIDATED
							- REORGANIZING
							- BANKRUPT
				type:
					type: array
					nullable: true
					items:
						type: string
						enum:
							- BANK
							- NKO
							- BANK_BRANCH
							- NKO_BRANCH
							- RKC
							- CBR
							- TREASURY
							- OTHER
```

| Тип входных данных   | Результат                                          |
| -------------------- | -------------------------------------------------- |
| `dict`               | `[dict]` - одиночный запрос                        |
| `list[dict]`         | `list[dict]` - пакет запросов                      |
| `list` (не словарей) | Если required имеет 1 параметр: `[{query: value}]` |
| Одиночное значение   | Если required имеет 1 параметр: `[{query: value}]` |

### Примеры преобразования данных

```python
# Одиночный словарь
data = {"query": 123}
# → [{"userId": 123}]
# Список словарей
data = [{"query": 123}, {"query": 456}]
# → [{"userId": 123}, {"userId": 456}]
# Список значений (если required = ["id"])
data = [123, 456, 789]
# [{"query": 123}, {"query": 456}, {"query": 789}]
# Одиночное значение (если required = ["query"])
data = 123
# [{"query": 123}]
```

### TODO

- [ ] Проверка наличия ключей словаря в спецификации
- [ ] Формирование очереди загрузок
- [ ] Реализация пагинации
- [ ] Улучшенная валидация ответов
- [ ] Потокобезопасность
