from pprint import pprint
import json
from src.REST2JSON.Rest2JSON import REST2JSON
from src.REST2JSON.utils.OASParser import OASParser
from src.REST2JSON.utils.utils import has_data


if __name__ == "__main__":
    

    config_file = 'C:/Users/kdenis/Documents/Work/configs/config_dadata.yaml'

    import yaml 

    with open(config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        
    
    
    #payload = OmegaConf.to_object(OmegaConf.select(config, "proc.src.data.payload", default={}))

    rest = REST2JSON(config)
    print(rest.get_StructTypeFormatSchema())
    result = rest.get_data()
    pprint(result)
    
    
    with rest as requesting:
        rest_res = rest.get_data('HDCBRUMM')
        pprint(rest_res)
        result = result + rest_res
        
    pprint(result)

    #import json
    #with open('response.json','w',encoding='Utf-8') as f:
    #    json.dump(result,f,indent=1)

    #with open('schema_dadata.json','w',encoding='Utf-8') as f:
    #   json.dump(rest.get_StructTypeFormatSchema(),f,indent=1)


    '''
    import yaml
    with open('C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/inmobile.yaml', 'r', encoding='utf-8') as f:
        content = f.read()
        loaded_spec = yaml.safe_load(content)

        sch_pars = OASParser(OpName='Lists_GetAllLists',loaded_spec=loaded_spec)

        with open('schema_inmobile.json','w',encoding='Utf-8') as f:
            json.dump(sch_pars.response_sparkdf,f,indent=1)
    '''

