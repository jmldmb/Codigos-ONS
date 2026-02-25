"""
Módulo para download de dados do ONS
"""
import os
import requests
import urllib3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import config
from utils.logger import logger

# Desabilita warnings de SSL para requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DataDownloader:
    """Classe para download de dados do ONS"""
    
    def __init__(self):
        """Inicializa o downloader"""
        self.verify_ssl = config.get('download.verify_ssl', False)
        self.meses_para_baixar = config.get('download.meses_para_baixar', 2)
    
    def get_previous_month(self, year: int, month: int, n: int = 1) -> Tuple[int, int]:
        """
        Retorna o ano e mês subtraindo n meses da data informada
        
        Args:
            year: Ano
            month: Mês
            n: Número de meses para subtrair
            
        Returns:
            Tupla (ano, mês)
        """
        month -= n
        while month <= 0:
            month += 12
            year -= 1
        return year, month
    
    def download_geracao_renovavel(self) -> None:
        """Download de dados de geração renovável (eólica e fotovoltaica)"""
        logger.info("Iniciando download de dados de geração renovável")
        
        # URLs e padrões de arquivo
        base_urls = {
            "fotovoltaica": config.get('urls.fotovoltaica'),
            "eolica": config.get('urls.eolica')
        }
        
        filename_patterns = {
            "fotovoltaica": "RESTRICAO_COFF_FOTOVOLTAICA_DETAIL_{year}_{month:02d}.parquet",
            "eolica": "RESTRICAO_COFF_EOLICA_DETAIL_{year}_{month:02d}.parquet"
        }
        
        # Diretório de destino
        dest_dir = config.get_path('paths.data.geracao')
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Obtém a data atual
        now = datetime.now()
        current_year, current_month = now.year, now.month
        
        # Lista de meses para baixar
        months_to_download = []
        for i in range(self.meses_para_baixar):
            year, month = self.get_previous_month(current_year, current_month, i)
            months_to_download.append((year, month))
        
        # Download para cada categoria e mês
        for category in ["fotovoltaica", "eolica"]:
            for year, month in months_to_download:
                file_name = filename_patterns[category].format(year=year, month=month)
                url = f"{base_urls[category]}{file_name}"
                
                logger.info(f"Baixando [{category}] - {year}/{month:02d}: {url}")
                
                try:
                    response = requests.get(url, verify=self.verify_ssl)
                    if response.status_code == 200:
                        file_path = dest_dir / file_name
                        with open(file_path, "wb") as f:
                            f.write(response.content)
                        logger.info(f"Arquivo salvo em: {file_path}")
                    else:
                        logger.warning(f"Falha ao baixar {url} (status code: {response.status_code})")
                except Exception as e:
                    logger.error(f"Erro ao baixar {url}: {str(e)}")
    
    def download_geracao_horaria(self) -> None:
        """Download de dados de geração horária"""
        logger.info("Iniciando download de dados de geração horária")
        
        # URL base e padrão de arquivo
        base_url = config.get('urls.geracao_horaria')
        file_template = "GERACAO_USINA-2_{year}_{month:02d}.parquet"
        
        # Diretório de destino
        dest_dir = config.get_path('paths.data.geracao_base_horaria')
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Obtém a data atual
        hoje = datetime.today()
        
        # Loop para baixar os meses
        for i in range(self.meses_para_baixar):
            ano, mes = self.get_previous_month(hoje.year, hoje.month, i)
            file_name = file_template.format(year=ano, month=mes)
            url = base_url + file_name
            
            logger.info(f"Tentando baixar: {url}")
            
            try:
                response = requests.get(url, verify=self.verify_ssl)
                if response.status_code == 200:
                    file_path = dest_dir / file_name
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Arquivo {file_name} baixado com sucesso em {file_path}")
                else:
                    logger.warning(f"Falha ao baixar {file_name}. Status: {response.status_code}")
            except Exception as e:
                logger.error(f"Erro ao baixar {url}: {str(e)}")
    
    def download_all(self) -> None:
        """Executa todos os downloads"""
        logger.info("Iniciando download de todos os dados")
        
        try:
            self.download_geracao_renovavel()
            self.download_geracao_horaria()
            logger.info("Download de todos os dados concluído com sucesso")
        except Exception as e:
            logger.error(f"Erro durante o download: {str(e)}")
            raise
