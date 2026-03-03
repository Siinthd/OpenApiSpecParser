from pprint import pprint
import json
from src.REST2JSON.Rest2JSON import REST2JSON
from src.REST2JSON.utils.OASParser import OASParser


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

    config_file = 'C:/Users/kdenis/Documents/Work/OpenApiSpecParser/src/config.yaml'
    from omegaconf import OmegaConf


    config = OmegaConf.load(config_file)
    config.get
    new_config = OmegaConf.create({
        "name": OmegaConf.select(config, "src.name", default=None),
        "Token_src": OmegaConf.select(config, "src.conn_params.Token_src", default=None),
        "endpoint_url": OmegaConf.select(config, "src.conn_params.endpoint_url", default=None),
        "method": OmegaConf.select(config, "src.conn_params.method", default=None),
        "timeout": OmegaConf.select(config, "src.conn_params.timeout", default=None),
        "retries": OmegaConf.select(config, "src.conn_params.retries", default=None),
        "pagination": OmegaConf.select(config, "src.conn_params.pagination", default=None),
        "spec_url": OmegaConf.select(config, "src.conn_params.spec_url", default=None),
        "spec_data": OmegaConf.select(config, "src.conn_params.spec_data", default=None),
        "base_url": OmegaConf.select(config, "src.conn_params.base_url", default=None),
        "user_input" :OmegaConf.select(config, "src.conn_params.user_input", default=None),
        })

    rest = REST2JSON(new_config)
    import json
    with open('schema.json','w',encoding='Utf-8') as f:
        json.dump(rest.get_response(payload),f,indent=1)


