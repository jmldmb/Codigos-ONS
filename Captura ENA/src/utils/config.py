"""
Módulo de configuração para o projeto Captura ENA
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Classe para gerenciar configurações do projeto"""
    
    def __init__(self, config_path: str = None):
        """
        Inicializa a configuração
        
        Args:
            config_path: Caminho para o arquivo de configuração
        """
        if config_path is None:
            # Buscar o arquivo de configuração no diretório padrão
            current_dir = Path(__file__).parent.parent.parent
            config_path = current_dir / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Carrega as configurações do arquivo YAML
        
        Returns:
            Dicionário com as configurações
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtém um valor da configuração usando notação de ponto
        
        Args:
            key: Chave da configuração (ex: 'paths.raw_data')
            default: Valor padrão se a chave não existir
            
        Returns:
            Valor da configuração
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_path(self, key: str) -> Path:
        """
        Obtém um caminho da configuração e retorna como Path
        
        Args:
            key: Chave da configuração
            
        Returns:
            Path object
        """
        path_str = self.get(key)
        if path_str:
            return Path(path_str)
        return None
    
    def reload(self):
        """Recarrega as configurações do arquivo"""
        self.config = self._load_config()


# Instância global da configuração
config = Config()


