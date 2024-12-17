import logging
from pathlib import Path


def init_logging(file_path: Path):
    logger = logging.getLogger('InfoExtract')
    logger.setLevel(logging.DEBUG)

    console_h = logging.StreamHandler()
    console_h.setLevel(logging.INFO)

    file_h = logging.FileHandler(file_path, encoding="utf-8")
    file_h.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_h.setFormatter(formatter)
    file_h.setFormatter(formatter)

    logger.addHandler(console_h)
    logger.addHandler(file_h)
    return logger
