"""
Módulo para configuração de logging
"""
import logging
import sys
from pathlib import Path
from .config import config


def setup_logger(name: str = "geracao_usina") -> logging.Logger:
    """
    Configura e retorna um logger
    
    Args:
        name: Nome do logger
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Evita duplicação de handlers
    if logger.handlers:
        return logger
    
    # Configuração do logger
    logger.setLevel(config.get('logging.level', 'INFO'))
    
    # Formato das mensagens
    formatter = logging.Formatter(
        config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo
    log_file = config.get_path('logging.file')
    if log_file:
        # Cria o diretório se não existir
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Logger global
logger = setup_logger()
