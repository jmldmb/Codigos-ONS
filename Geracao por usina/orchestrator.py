"""
Orquestrador principal para o projeto de Geração por Usina
"""
import argparse
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Adiciona o diretório raiz ao path para importar módulos
sys.path.append(str(Path(__file__).parent))

from utils.config import config
from utils.logger import logger
from scripts.data_downloader import DataDownloader
from scripts.data_processor import DataProcessor
from scripts.visualization import DataVisualizer


class GeracaoUsinaOrchestrator:
    """Orquestrador principal para o projeto de Geração por Usina"""
    
    def __init__(self):
        """Inicializa o orquestrador"""
        self.downloader = DataDownloader()
        self.processor = DataProcessor()
        self.visualizer = DataVisualizer()
        
        # Cria diretórios necessários
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Cria diretórios necessários para o projeto"""
        directories = [
            config.get_path('paths.output.charts'),
            config.get_path('paths.output.reports'),
            config.get_path('paths.output.data'),
            Path(config.get('logging.file')).parent
        ]
        
        for directory in directories:
            if directory:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Diretório criado/verificado: {directory}")
    
    def download_data(self) -> None:
        """Executa o download de dados"""
        logger.info("=== INICIANDO DOWNLOAD DE DADOS ===")
        
        try:
            self.downloader.download_all()
            logger.info("Download de dados concluído com sucesso")
        except Exception as e:
            logger.error(f"Erro durante o download: {str(e)}")
            raise
    
    def process_data(self) -> Dict:
        """Executa o processamento de dados"""
        logger.info("=== INICIANDO PROCESSAMENTO DE DADOS ===")
        
        try:
            processed_data = self.processor.process_all()
            logger.info("Processamento de dados concluído com sucesso")
            return processed_data
        except Exception as e:
            logger.error(f"Erro durante o processamento: {str(e)}")
            raise
    
    def generate_charts(self, processed_data: Dict) -> None:
        """Executa a geração de gráficos"""
        logger.info("=== INICIANDO GERAÇÃO DE GRÁFICOS ===")
        
        try:
            self.visualizer.generate_all_charts(processed_data)
            logger.info("Geração de gráficos concluída com sucesso")
        except Exception as e:
            logger.error(f"Erro durante a geração de gráficos: {str(e)}")
            raise
    
    def run_full_pipeline(self) -> None:
        """Executa o pipeline completo"""
        logger.info("=== INICIANDO PIPELINE COMPLETO ===")
        
        start_time = datetime.now()
        
        try:
            # 1. Download de dados
            self.download_data()
            
            # 2. Processamento de dados
            processed_data = self.process_data()
            
            # 3. Geração de gráficos
            self.generate_charts(processed_data)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"=== PIPELINE CONCLUÍDO COM SUCESSO ===")
            logger.info(f"Duração total: {duration}")
            
        except Exception as e:
            logger.error(f"Erro durante o pipeline: {str(e)}")
            raise
    
    def run_download_only(self) -> None:
        """Executa apenas o download de dados"""
        logger.info("=== EXECUTANDO APENAS DOWNLOAD ===")
        self.download_data()
    
    def run_process_only(self) -> None:
        """Executa apenas o processamento de dados"""
        logger.info("=== EXECUTANDO APENAS PROCESSAMENTO ===")
        processed_data = self.process_data()
        logger.info(f"Dados processados: {list(processed_data.keys())}")
    
    def run_charts_only(self) -> None:
        """Executa apenas a geração de gráficos"""
        logger.info("=== EXECUTANDO APENAS GERAÇÃO DE GRÁFICOS ===")
        
        # Tenta carregar dados processados existentes
        output_dir = config.get_path('paths.output.data')
        processed_data = {}
        
        # Carrega dados de geração renovável
        renovavel_file = output_dir / 'geracao_renovavel.xlsx'
        if renovavel_file.exists():
            processed_data['geracao_renovavel'] = pd.read_excel(renovavel_file)
            logger.info("Dados de geração renovável carregados")
        
        # Carrega dados de geração térmica
        termica_file = output_dir / 'geracao_termica.xlsx'
        if termica_file.exists():
            processed_data['geracao_termica'] = pd.read_excel(termica_file)
            logger.info("Dados de geração térmica carregados")
        
        # Carrega dados de certificação
        cadastros = self.processor.load_cadastro_data()
        if 'p50' in cadastros and 'p90' in cadastros:
            processed_data['certificacao'] = {
                'p50': cadastros['p50'],
                'p90': cadastros['p90']
            }
            logger.info("Dados de certificação carregados")
        
        if not processed_data:
            logger.error("Nenhum dado processado encontrado. Execute o processamento primeiro.")
            return
        
        self.generate_charts(processed_data)


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Orquestrador de Geração por Usina')
    parser.add_argument('--mode', 
                       choices=['full', 'download', 'process', 'charts'],
                       default='full',
                       help='Modo de execução (default: full)')
    parser.add_argument('--config', 
                       type=str,
                       help='Caminho para arquivo de configuração personalizado')
    
    args = parser.parse_args()
    
    try:
        # Inicializa orquestrador
        orchestrator = GeracaoUsinaOrchestrator()
        
        # Executa baseado no modo
        if args.mode == 'full':
            orchestrator.run_full_pipeline()
        elif args.mode == 'download':
            orchestrator.run_download_only()
        elif args.mode == 'process':
            orchestrator.run_process_only()
        elif args.mode == 'charts':
            orchestrator.run_charts_only()
        
    except Exception as e:
        logger.error(f"Erro na execução: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
