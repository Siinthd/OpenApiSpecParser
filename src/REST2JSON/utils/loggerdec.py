import functools
import time
from typing import Optional, Callable
import logging
import os
from pathlib import Path

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# Настройка базового логгера
def setup_logger(name: str = "app", log_file: str = None, level=logging.CRITICAL):

    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def log_this(logger=None, log_args: bool = True, log_result: bool = False, log_exceptions: bool = True):
    if logger is None:
        logger = setup_logger(name="URESTParser", log_file= os.path.join(LOG_DIR, "URESTParser.log"), level=logging.DEBUG)

    def log(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            start_time = time.time()
            
            if log_args:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                logger.debug(f"Вызов {func_name} с аргументами: {signature}")
            else:
                logger.debug(f"Вызов {func_name}")
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                if log_result:
                    logger.debug(f"{func_name} вернула {result!r} за {elapsed:.3f} сек")
                else:
                    logger.debug(f"{func_name} выполнена за {elapsed:.3f} сек")
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                if log_exceptions:
                    logger.exception(f"Исключение в {func_name} через {elapsed:.3f} сек: {e}")
                raise  
        return wrapper
    return log