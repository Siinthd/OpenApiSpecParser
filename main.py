from pprint import pprint
import json
from src.REST2JSON.Rest2JSON import REST2JSON
from src.REST2JSON.utils.OASParser import OASParser
from src.REST2JSON.utils.utils import has_data


if __name__ == "__main__":
    

    config_file = 'C:/Users/kdenis/Documents/Work/configs/config_coindesk.yaml'

    import yaml 

    with open(config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        
    

    rest = REST2JSON(config)
    

    pprint(rest.get_schema())
    
    
    #import json
    #with open('response.json','w',encoding='Utf-8') as f:
    #    json.dump(result,f,indent=1)

    with open('answer.json','w',encoding='Utf-8') as f:
      json.dump(rest.get_data(),f,indent=1)


    
    # import yaml
    # with open('C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/inmobile.yaml', 'r', encoding='utf-8') as f:
    #     content = f.read()
    #     loaded_spec = yaml.safe_load(content)

    #     sch_pars = OASParser(OpName='Lists_GetAllLists',loaded_spec=loaded_spec)

    #     with open('schema_inmobile.json','w',encoding='Utf-8') as f:
    #         json.dump(sch_pars.response_sparkdf,f,indent=1)
    

    # def cached(n):
    #     def cached_multiplier(x):
    #         return x * n
    #     return cached_multiplier

    # def slow_function(x, y=2):
    #     print("Вычисляю...")
    #     return x * y

    # cached_slow = cached(slow_function)
    # print(cached_slow(3))      # Вычисляю... 6
    # print(cached_slow(3))      # 6 (без "Вычисляю...")
    # print(cached_slow(3, y=3)) # Вычисляю... 9
    # print(cached_slow(3, y=2)) # 6 (из кэша)


       
        