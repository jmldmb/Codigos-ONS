"""
Script para captura de dados CVU de usinas térmicas do ONS
"""

import os
import requests
import pandas as pd
import logging
from pathlib import Path
from tqdm import tqdm
import yaml
from datetime import datetime
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_project_root():
    """Encontra o diretório raiz do projeto dinamicamente"""
    current_path = Path.cwd()
    
    # Procurar pelo arquivo config.yaml ou outros marcadores do projeto
    while current_path != current_path.parent:
        if (current_path / "config.yaml").exists() or \
           (current_path / "requirements.txt").exists() or \
           (current_path / "README.md").exists():
            return current_path
        current_path = current_path.parent
    
    # Se não encontrar, procurar pelo diretório CVU termicas em qualquer nível
    current_path = Path.cwd()
    while current_path != current_path.parent:
        # Procurar em subdiretórios
        for subdir in current_path.iterdir():
            if subdir.is_dir():
                cvu_dir = subdir / "CVU termicas"
                if cvu_dir.exists() and (cvu_dir / "config.yaml").exists():
                    return cvu_dir
        current_path = current_path.parent
    
    # Se não encontrar, usar o diretório atual
    return Path.cwd()

class DataIngest:
    """Classe para captura de dados CVU"""
    
    def __init__(self, config_path="config.yaml"):
        """Inicializa com configurações"""
        # Encontrar o diretório raiz do projeto
        self.project_root = find_project_root()
        logger.info(f"Diretório raiz do projeto: {self.project_root}")
        
        # Construir caminho absoluto para o config
        if not Path(config_path).is_absolute():
            config_path = self.project_root / config_path
        
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.base_url = self.config['data']['base_url']
        self.filename_pattern = self.config['data']['filename_pattern']
        self.years = self.config['data']['years']
        
        # Construir caminho absoluto baseado no diretório raiz do projeto
        self.raw_data_path = self.project_root / self.config['paths']['raw_data']
        
        # Criar diretórios se não existirem
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Diretório de dados raw: {self.raw_data_path}")
    
    def download_file(self, url, filepath, chunk_size=8192):
        """Download de arquivo com barra de progresso"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as file:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=filepath.name) as pbar:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            file.write(chunk)
                            pbar.update(len(chunk))
            
            return True
        except Exception as e:
            logger.error(f"Erro ao baixar {url}: {e}")
            return False
    
    def download_historical_data(self):
        """Download de todos os dados históricos (2020-2024)"""
        logger.info("Iniciando download de dados históricos...")
        
        for year in self.years[:-1]:  # Exclui 2025
            filename = self.filename_pattern.format(year=year)
            url = self.base_url + filename
            filepath = self.raw_data_path / filename
            
            if filepath.exists():
                logger.info(f"Arquivo {filename} já existe, pulando...")
                continue
            
            logger.info(f"Baixando dados de {year}...")
            success = self.download_file(url, filepath)
            
            if success:
                logger.info(f"Dados de {year} baixados com sucesso")
            else:
                logger.error(f"Falha ao baixar dados de {year}")
            
            # Pausa entre downloads para não sobrecarregar o servidor
            time.sleep(1)
    
    def download_current_year(self):
        """Download apenas dos dados do ano atual (2025)"""
        logger.info("Baixando dados do ano atual (2025)...")
        
        year = 2025
        filename = self.filename_pattern.format(year=year)
        url = self.base_url + filename
        filepath = self.raw_data_path / filename
        
        # Sempre baixa o arquivo de 2025 (substitui se existir)
        success = self.download_file(url, filepath)
        
        if success:
            logger.info(f"Dados de {year} atualizados com sucesso")
            return True
        else:
            logger.error(f"Falha ao baixar dados de {year}")
            return False
    
    def verify_downloads(self):
        """Verifica se todos os arquivos foram baixados corretamente"""
        logger.info("Verificando downloads...")
        
        missing_files = []
        for year in self.years:
            filename = self.filename_pattern.format(year=year)
            filepath = self.raw_data_path / filename
            
            if not filepath.exists():
                missing_files.append(filename)
            else:
                # Verifica se o arquivo pode ser lido
                try:
                    df = pd.read_parquet(filepath)
                    logger.info(f"{filename}: {len(df)} registros")
                except Exception as e:
                    logger.error(f"Erro ao ler {filename}: {e}")
                    missing_files.append(filename)
        
        if missing_files:
            logger.warning(f"Arquivos faltando: {missing_files}")
        else:
            logger.info("Todos os arquivos foram baixados e verificados com sucesso")
        
        return len(missing_files) == 0
    
    def get_data_summary(self):
        """Retorna resumo dos dados baixados"""
        summary = {}
        
        for year in self.years:
            filename = self.filename_pattern.format(year=year)
            filepath = self.raw_data_path / filename
            
            if filepath.exists():
                try:
                    df = pd.read_parquet(filepath)
                    summary[year] = {
                        'registros': len(df),
                        'colunas': list(df.columns),
                        'tamanho_arquivo': filepath.stat().st_size / (1024 * 1024)  # MB
                    }
                except Exception as e:
                    logger.error(f"Erro ao ler {filename}: {e}")
        
        return summary

def main():
    """Função principal"""
    ingest = DataIngest()
    
    # Download de dados históricos
    ingest.download_historical_data()
    
    # Download do ano atual
    ingest.download_current_year()
    
    # Verificação
    ingest.verify_downloads()
    
    # Resumo
    summary = ingest.get_data_summary()
    logger.info("Resumo dos dados:")
    for year, info in summary.items():
        logger.info(f"{year}: {info['registros']} registros, {info['tamanho_arquivo']:.2f} MB")

if __name__ == "__main__":
    main() 