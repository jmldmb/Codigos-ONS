"""
Módulo de logging para o projeto Captura ENA
"""
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(name: str, log_file: str = None, level: str = "INFO") -> logging.Logger:
    """
    Configura e retorna um logger personalizado
    
    Args:
        name: Nome do logger
        log_file: Caminho para o arquivo de log
        level: Nível de logging
        
    Returns:
        Logger configurado
    """
    # Criar logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Evitar duplicação de handlers
    if logger.handlers:
        return logger
    
    # Formato do log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo (se especificado)
    if log_file:
        # Criar diretório de logs se não existir
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "captura_ena") -> logging.Logger:
    """
    Retorna um logger padrão para o projeto
    
    Args:
        name: Nome do logger
        
    Returns:
        Logger configurado
    """
    return setup_logger(name)


