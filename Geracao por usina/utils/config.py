"""
Módulo para gerenciar configurações do projeto
"""
import os
import yaml
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
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega o arquivo de configuração"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtém um valor da configuração usando notação de ponto
        
        Args:
            key: Chave da configuração (ex: 'paths.data.geracao')
            default: Valor padrão se a chave não existir
            
        Returns:
            Valor da configuração
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_path(self, key: str) -> Path:
        """
        Obtém um caminho da configuração e resolve para Path absoluto
        
        Args:
            key: Chave do caminho (ex: 'paths.data.geracao')
            
        Returns:
            Path absoluto
        """
        base_dir = Path(self.get('paths.base_dir'))
        relative_path = self.get(key)
        
        if relative_path:
            return base_dir / relative_path
        return None
    
    def reload(self):
        """Recarrega a configuração do arquivo"""
        self._config = self._load_config()


# Instância global da configuração
config = Config()
