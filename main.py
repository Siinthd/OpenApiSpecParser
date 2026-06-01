from pprint import pprint
import json
from src.REST2JSON.Rest2JSON import REST2JSON
from src.REST2JSON.utils import HTTPTransport
from ..StagingManager.src.STAGINGMANAGER import STAGINGMANAGER


if __name__ == "__main__":
    

    config_file = 'C:/Users/kdenis/Documents/Work/configs/config_IPInfo_demo.yaml'
    config_file = 'C:/Users/kdenis/Documents/Work/configs/config_dadata_demo.yaml'
    #config_file = 'C:/Users/kdenis/Documents/Work/configs/config_WorldBank.yaml'

    import yaml 

    with open(config_file) as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


    context = STAGINGMANAGER()
    transport = HTTPTransport()
    rest = REST2JSON(transport = transport,config = config,context = context)
    rest.prepare()
    rest.run()

