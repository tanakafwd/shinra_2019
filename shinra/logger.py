import logging
import os


def get_logger(level=None):
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            '[%(asctime)s][%(levelname)s](%(filename)s:%(lineno)s) %(message)s'
        ))
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagete = False
    return logger
