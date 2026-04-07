from pprint import pprint
import json
from src.REST2JSON.Rest2JSON import REST2JSON
from src.REST2JSON.utils.OASParser import OASParser



if __name__ == "__main__":
    

    config_file = 'C:/Users/kdenis/Documents/Work/configs/config_IPinfo.yaml'

    import yaml 

    with open(config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)



    

    rest = REST2JSON(config)
    

    
    import json
    with open('schema_raw.json','w',encoding='Utf-8') as f:
        json.dump(rest.get_schema(True),f,indent=1)
    with open('schema.json','w',encoding='Utf-8') as f:
        json.dump(rest.get_schema(),f,indent=2)

    with open('answer.json','w',encoding='Utf-8') as f:
      json.dump(rest.get_data(),f,indent=1)


    
    # import yaml
    # with open('C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/inmobile.yaml', 'r', encoding='utf-8') as f:
    #     content = f.read()
    #     loaded_spec = yaml.safe_load(content)

    #     sch_pars = OASParser(OpName='Lists_GetAllLists',loaded_spec=loaded_spec)

    #     with open('schema_inmobile.json','w',encoding='Utf-8') as f:
    #         json.dump(sch_pars.response_sparkdf,f,indent=1)