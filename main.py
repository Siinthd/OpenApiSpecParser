from pprint import pprint
import json
from src.URESTAdapter import URESTAdapter
from src.utils.OASParser import OASParser
from src.utils.utils import convertdicttoXSD
from src.utils.utils import collect_xml_response

if __name__ == "__main__":

    TOPIC_NAME = 'post_api_4_1_rs_suggest_bank'
    #  forecast - Яндекс Погода
    #  getTopHeadlines - API новостной с пагинацей
    #  getEverything - API новостной с пагинацей
    #  suggestions_dadata_suggestBank - Dadata - сервис API

    src_dict = {'get_everything':'C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/NewsAPI.yaml'
                ,'post_api_4_1_rs_suggest_bank':'C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/suggestions.yml'
                ,'get_top-headlines':'C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/NewsAPI.yaml'
                ,'get_currentconditions_v1__locationKey_':'C:/Users/kdenis/Documents/Work/OpenApiSpecParser/examples/accuweather.yaml'}
    
    input_data = {
    'get_everything':{'q':'RUSSIA'},
    'post_api_4_1_rs_suggest_bank':[
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
    ],
    'get_top-headlines':{'q':'RUSSIA'},
    'get_currentconditions_v1__locationKey_':[1,2,3,45,66666,77777,9999,88]
}

    parser = OASParser(src_dict[TOPIC_NAME])
    entity  = parser.request.get(TOPIC_NAME)

    resp_schema  = parser.get_response(TOPIC_NAME)
    

    #Mock сервера ключей
    with open('C:/Users/kdenis/mu_code/keys.json', 'r', encoding='utf-8') as f:
        tokens = json.load(f)
    token = tokens.get(entity.get('base_url'))
      

    test = URESTAdapter(entity,token)
    result = test.execute(input_data.get(TOPIC_NAME))

    with open('schema.json','w',encoding='Utf-8') as f:
        json.dump(resp_schema,f,indent=1)

    with open('test.xsd','w',encoding='Utf-8') as f:
        f.write(convertdicttoXSD(resp_schema))