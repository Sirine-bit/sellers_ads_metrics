"""
Configuration du logger avec couleurs
"""
import logging
import colorlog

def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Configure un logger avec couleurs pour la console
    
    Args:
        name: Nom du logger
        
    Returns:
        Logger configuré
    """
    # Créer le logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Éviter la duplication des handlers
    if logger.handlers:
        return logger
    
    # Handler pour la console avec couleurs
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Format avec couleurs
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s - %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger