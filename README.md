# REST2JSON


Конфигурируемый адаптер, способный выполнять чтение данных с использованием внешнего REST-сервиса без написания клиента под каждый конкретный API на основании описания метаданных этого сервиса.


  
## Особенности

- Гибкая конфигурация через OmegaConf
- Загрузка OpenAPI спецификаций из файлов (YAML/JSON) или по URL
- Пакетная обработка запросов с подготовкой payload(Возможно,придется отказаться в пользу явного построения запроса)
- Поддержка контекстного менеджера для безопасного управления ресурсами
- Генерация JSON Schema из OpenAPI спецификации


## Установка

```bash
pip install git+https://github.com/Siinthd/Rest2JSON.git
pip install REST2JSON --index-url {mirror}
```


## Быстрый старт


### Простой запрос
```Python
from rest2json import REST2JSON

config_file = 'C:/Users/kdenis/Documents/Work/configs/config_WorldBank.yaml'

import yaml 

with open(config_file) as stream:
    try:
         config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

#Иницализация адаптера, в этот момент происходит чтение/конфигурации,скачивание спецификации и ее парсинг
adapter = REST2JSON(config)
# get_schema() возвращает схему данных в <class 'dict'> - формате
#   по умолчанию (raw = False) вернет Spark dataframe ddl
#   (raw = True) возвращает структуру ответа без обработки (не подходит,чтобы создать dataframe)
schema = adapter.get_schema(raw = False)
# get_data() возвращает данные ответов с сервера в формате [<class 'dict'>]
#   по умолчанию (пустые скобки), payload берется из конфигурации
data = adapter.get_data()
#   При наличии payload (get_data(payload)) у сервера запрашиваются конкретные в payload данные.
payload = [{"query": 123}, {"query": 456}, {"query": 789}]
results = adapter.get_response(payload)

```


### Использование с контекстным менеджером
```Python
# возможность докачки данных вне конфигурации
with REST2JSON(config) as adapter:
	 # Работа с адаптером
    response = adapter.get_data({})
    print(response)
    # Автоматическое закрытие соединений
```

### Пакетная обработка
```Python
payload = [{"query": 123}, {"query": 456}, {"query": 789}] # API-сервис ожидает параметр c именем query

with REST2JSON(config) as adapter:
    results = adapter.get_response(payload)
    for result in results:
        print(result)

#или
adapter = REST2JSON(config)
response = adapter.get_response(payload)
for result in response:
        print(result)
```

  

## Конфигурация

### Структура конфигурации
```yaml
# обязательный: параметры процесса
# (основные настройки)
proc:
  # обязательный: конфиг источника

  src:
    # обязательный: наименование источника
    name: "getEverything" #
    # обязательный: тип подключения
    #   определяет, как мы читаем источник
    conn_type: 'rest2json' 
    # обязательный: список параметров подключения
    conn_params:
      # опциональный: количество ретраев и таймаут
      #   если не указать -- 1 ретрай и какой-нибудь таймаут
      retries: 3
      timeout: 30  

      # обязательный: спецификация сервиса
      # (хотя бы один из двух должен быть указан и заполнен) 
      #   отсюда берём схемы реплаев,
      #     + url для запроса, если возможно

      spec_url: 'https://dadata.ru/files/openapi/suggestions.yml'
      spec_data: 
      # опциональный: адрес для запроса 

      base_url: "https://suggestions.dadata.ru/suggestions"
      # опциональный: ep+method для случаев, когда сервис не использует operation_id
      endpoint_url: "/api/4_1/rs/suggest/bank"
      method: 'post'
      # опциональный: перебор страниц на сервере
      #   игнорим, если параметра нет,
      pagination:
        # обязательный: включение
        enabled: false
        # обязательный: название параметра с номером страницы
        page_param: 'page'
        # обязательный: название параметра с размером страницы
        pagesize_param: 'per_page'
        # обязательный: запрашиваемый размер страницы
        pagesize_val: 100
        # обязательный: название параметра с общим числом записей
        pagecnt_param: "total_results"

    # обязательный: конфиг данных (схема, фильтры, etc)
    data:
      #   TODO: использовать динамическую генерацию запросов по спеке,
      #     и как-то угадывать, куда какие параметры писать -- нецелесообразно
      payload: 
              ['SABRRUMM', 'VTBRRUMM',]
	# опциональный: свой маппинг типов
	  json_mapping_override:
	  	"null": "null"
      
# обязательный: данные для авторизации
# содержат только логины, токены, пароли
auth:
  # источник (extract)
  src:
    header: # авторизация через хедер (как в dadata)
      "Authorization":  "Token "
      "X-Secret": ""
      #X-Secret: "64545645"
    body: # авторизация через параметр в теле (как в random.org)  
      #- "API_KEY: 12434547985675"
env:
	# опциональный:  маппинг типов данных (при конвертация в StrucType-json)
  json:
    type_mapping:
      int32: integer
      int64: long
      float: float
      double: double
      date: string
      date-time: string
      binary: binary
```


## Class Reference

### Класс `REST2JSON`

Основной класс для работы с API.

#### Методы

##### `get_data(data=None)`

Основной метод для выполнения запросов. Автоматически управляет контекстом.

**Параметры:**

- `data` - Данные для запроса. Может быть:
    
    - `None` - запрос без параметров,в таком случае данные для запроса берутся из конфигурации (раздел proc.src.data.payload)
    - `dict` - одиночный запрос (может быть пустым - {})
    - `list[dict]` - пакет запросов (может быть пустым - [])
    - `str/int` - одиночное значение (будет преобразовано в параметр required)(может быть пустым - '')
        

**Возвращает:** JSON ответ от API или список ответов при пакетной обработке.

##### `get_schema(raw = False)`

**Возвращает:**  схема структуры данных из OpenAPI спецификации при raw = False возвращает схему в Spark-формате.


## Обработка payload

Для получения ответа от API сервиса необходимо передать в запрос параметры, которые он ожидает — обычно это идентификаторы, фильтры или данные для создания/обновления объектов.
Они могут быть переданы как часть URL (например, /users/123), в строке запроса (?page=2) или в теле запроса (JSON с полями).

Такие параметры указаны в разделе "requestBody". Часто, это один required-параметр и можно передать в REST2JSON список значения без указания имени параметра - Сервис сам подставить имя параметра.

В противном случае, требуется указать все параметры явно:

```python
data = {"query": 123,"status":["ACTIVE"],"type":["BANK","BANK_BRANCH","OTHER"]}
```

#### Пример requestBody в спецификации

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
| `{}`,`[]`,`''`       | `[dict]` - одиночный запрос(сервер не ждет данных) |
| `dict`               | `[dict]` - одиночный запрос                        |
| `list[dict]`         | `list[dict]` - пакет запросов                      |
| `list` (не словарей) | Если required имеет n параметров: `[{query: value_1}...{query: value_n}]` |
| Одиночное значение   | Если required имеет 1 параметр: `[{query: value}]` |

### Примеры преобразования данных

```python
# Одиночный словарь
data = {"query": 123}
# → [{"query": 123}]
# Список словарей
data = [{"query": 123}, {"query": 456}]
# → [{"query": 123}, {"query": 456}]
# Список значений (если required = ["id"])
data = [123, 456, 789]
# [{"query": 123}, {"query": 456}, {"query": 789}]
# Одиночное значение (если required = ["query"])
data = 123
# [{"query": 123}]
data = {"query": 123,"status":["ACTIVE"],"type":["BANK","BANK_BRANCH","OTHER"]}
#Явное указание дополнительных фильтров
```

### TODO

- [ ] Проверка наличия ключей словаря в спецификации
- [ ] Формирование очереди загрузок
- [ ] Реализация пагинации
- [ ] Улучшенная валидация ответов
- [ ] Потокобезопасность
