from pprint import pprint
import json
from src.REST2JSON.Rest2JSON import REST2JSON
from src.REST2JSON.utils.OASParser import OASParser
from src.REST2JSON.utils.utils import has_data


if __name__ == "__main__":
    

    config_file = 'C:/Users/kdenis/Documents/Work/configs/config_WorldBank.yaml'

    from omegaconf import OmegaConf


    config = OmegaConf.load(config_file)
    new_config = OmegaConf.create({
        "name": OmegaConf.select(config, "proc.src.name", default=None),
        "auth_header": OmegaConf.select(config, "auth.src.header", default={}),
        "auth_body" : OmegaConf.select(config, "auth.src.body", default={}),
        "endpoint_url": OmegaConf.select(config, "proc.src.conn_params.endpoint_url", default=None),
        "method": OmegaConf.select(config, "proc.src.conn_params.method", default=None),
        "timeout": OmegaConf.select(config, "proc.src.conn_params.timeout", default=None),
        "retries": OmegaConf.select(config, "proc.src.conn_params.retries", default=None),
        "pagination": OmegaConf.select(config, "proc.src.conn_params.pagination.enabled", default=None),
        "page_param" : OmegaConf.select(config, "proc.src.conn_params.pagination.page_param", default=None),
        "spec_url": OmegaConf.select(config, "proc.src.conn_params.spec_url", default=None),
        "spec_data": OmegaConf.select(config, "proc.src.conn_params.spec_data", default=None),
        "base_url": OmegaConf.select(config, "proc.src.conn_params.base_url", default=None),
        "type_mapping" :OmegaConf.select(config, "env.json.type_mapping", default={}),
        "json_mapping_override" :OmegaConf.select(config, "proc.src.data.json_mapping_override", default={}),
        })
    
    payload = OmegaConf.to_object(OmegaConf.select(config, "proc.src.data.payload", default={}))

    rest = REST2JSON(new_config)
    print(rest.get_StructTypeFormatSchema())
    result = rest.get_response(payload)
    pprint(result)
  
    #with rest as requesting:
    #    result = result + requesting.get_response('SABRRUMM')
    #    rest_res = rest.get_response(payload)
    #    result = result + rest_res


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

