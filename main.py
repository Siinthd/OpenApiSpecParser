from pprint import pprint
import json
from src.Rest2JSON import REST2JSON


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
    rest = REST2JSON(config_file = 'C:/Users/kdenis/Documents/Work/OpenApiSpecParser/src/config.yaml')
    import json
    with open('schema.json','w',encoding='Utf-8') as f:
        json.dump(rest.get_response(payload),f,indent=1)
