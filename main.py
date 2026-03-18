from pprint import pprint
import json
from src.REST2JSON.Rest2JSON import REST2JSON
from src.REST2JSON.utils.OASParser import OASParser
from src.REST2JSON.utils.utils import has_data


if __name__ == "__main__":
    
    payload = [
        'SABRRUMM', 'VTBRRUMM', 'GAZPRUMM', 'ALFARUMM', 'MOSCRUMM',
        'RSBNRUMM', 'RUWCRUMM', 'ICBKRUMM', 'KOSKRUMM', 'PARNRUMM',
        'ABNYRUMM', 'CRYPRUMM', 'TICSRUMM', 'PSBZRUMM', 'TKRBRUMM',
        'JSNMRUMM', 'MIRBRUMM', 'ELSRUMMXXX', 'RNGBRUMM', 'IRONRUMM',
        'AVJSRUMM', 'ARESRUMM', 'ALILRUMM', 'ITRORU8Y', 'BOCSRUMM',
        'DOMRRUMM', 'FORTRUMM', 'GLBKRUMM', 'HDCBRUMM', 'KBKTRUMM',
        'KREMRUMM', 'LBRURUMM', 'MDMBRUMM', 'MEZHRUMM', 'MOPARUMM',
        'OLMDRUMM', 'ROYCRUMM', 'RZCBRUMM', 'SBERRUMM', 'SGBZRUMM',
        'SLAVRUMM', 'SOGZRUMM', 'TATKRUMM', 'TKBKRUMM', 'TKZLRUMM',
        'TKZVRUMM', 'TRNVRUMM', 'VEFKRUMM', 'VTBKRUMM', 'ZENIRUMM'
    ]
    '''
    payload = [
    # Москва и область
    {'locationKey': '294021', 'language': 'ru-ru', 'city': 'Москва','details':True},
    {'locationKey': '295212', 'language': 'ru-ru', 'city': 'Химки','details':True},
    {'locationKey': '295554', 'language': 'ru-ru', 'city': 'Мытищи','details':True},
    {'locationKey': '295837', 'language': 'ru-ru', 'city': 'Королёв','details':True},
    {'locationKey': '295986', 'language': 'ru-ru', 'city': 'Подольск','details':True},
    {'locationKey': '296319', 'language': 'ru-ru', 'city': 'Люберцы','details':True},
    {'locationKey': '296443', 'language': 'ru-ru', 'city': 'Красногорск','details':True},]


    '''
    #payload =  {'display_title': 'Moscow','format': 'json',}
    #payload =  {"q": "Pskov","pageSize":"4","page": "1"}
    #payload =  {'market': 'binance','instrument': 'BTC-USDT-VANILLA-PERPETUAL','limit': '100'}
    #payload =  {'asset': 'ETH','limit': '100'}
    
    #conf_WorldBank
    #config_newsApi

    config_file = 'C:/Users/kdenis/Documents/Work/configs/config_upd.yaml'

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

    rest = REST2JSON(new_config)
    pprint(rest.get_StructTypeFormatSchema())
    #result = rest.get_response(payload)
    #pprint(result)
  
    #with rest as requesting:
    #    result = result + requesting.get_response('SABRRUMM')
    #    rest_res = rest.get_response(payload)
    #    result = result + rest_res


    #import json
    #with open('response.json','w',encoding='Utf-8') as f:
    #    json.dump(result,f,indent=1)

    with open('schema_dadata.json','w',encoding='Utf-8') as f:
       json.dump(rest.get_StructTypeFormatSchema(),f,indent=1)


    '''
    import yaml
    with open('C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/inmobile.yaml', 'r', encoding='utf-8') as f:
        content = f.read()
        loaded_spec = yaml.safe_load(content)

        sch_pars = OASParser(OpName='Lists_GetAllLists',loaded_spec=loaded_spec)

        with open('schema_inmobile.json','w',encoding='Utf-8') as f:
            json.dump(sch_pars.response_sparkdf,f,indent=1)
    '''

    #from src.REST2JSON.utils.OASParser import OASParser,compare_shapes,build_shape,validate_batch_structurally



   # schema_shape = build_shape(response)  
    #pprint(schema_shape)
   # response_shape = build_shape(rest.entity_schema)
   # pprint(response_shape)


    # При каждом полученном батче
    #analysis = validate_batch_structurally(
    #    batch=response,          # List[dict]
    #    schema_shape=response_shape,
    #    debug=True
    #)

    #pprint(analysis)

