import logging

def get_custom_logger(name: str) -> logging.Logger:
    """
    Creates and returns a logger with a predefined configuration.

    Args:
    name (str): The name of the logger used for identification.

    Returns:
    logging.Logger: The logger object with predefined configuration.
    """

    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter("[%(asctime)s +0000] [%(process)d] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # add formatter to handler
    handler.setFormatter(formatter)

    # add handler to logger
    logger.addHandler(handler)

    return logger

logger = get_custom_logger("app")