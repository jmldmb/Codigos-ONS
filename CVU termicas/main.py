"""
Script principal do projeto CVU Termicas
Orquestra todo o pipeline de captura, processamento, visualização e geração de relatórios
"""

import logging
import sys
from pathlib import Path
import yaml
from datetime import datetime
import argparse

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

# Encontrar o diretório raiz do projeto
project_root = find_project_root()

# Adicionar scripts ao path
scripts_path = project_root / "scripts"
sys.path.append(str(scripts_path))

from scripts.data_ingest import DataIngest
from scripts.data_process import DataProcessor
from scripts.data_viz import DataVisualizer
from scripts.report_gen import ReportGenerator
from scripts.merit_order import MeritOrderGenerator

# Configurar logging
logs_path = project_root / "logs"
logs_path.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_path / 'cvu_termicas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CVUTermicasPipeline:
    """Classe principal que orquestra todo o pipeline"""
    
    def __init__(self, config_path="config.yaml"):
        """Inicializa o pipeline"""
        # Construir caminho absoluto para o config
        if not Path(config_path).is_absolute():
            config_path = project_root / config_path
        
        self.config_path = config_path
        logger.info(f"Usando arquivo de configuração: {config_path}")
        
        # Carregar configurações
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Criar diretório de logs
        logs_path = project_root / self.config['paths']['logs']
        logs_path.mkdir(parents=True, exist_ok=True)
        
        # Inicializar componentes
        self.data_ingest = DataIngest(config_path)
        self.data_processor = DataProcessor(config_path)
        self.data_visualizer = DataVisualizer(config_path)
        self.report_generator = ReportGenerator(config_path)
        self.merit_order_generator = MeritOrderGenerator(config_path)
    
    def _get_available_weeks(self):
        """Identifica as semanas disponíveis nos dados CVU"""
        try:
            import pandas as pd
            from pathlib import Path
            
            # Carregar dados CVU do ano atual
            current_year = datetime.now().year
            project_root = find_project_root()
            cvu_file = project_root / self.config['paths']['raw_data'] / f"CVU_USINA_TERMICA_{current_year}.parquet"
            
            if not cvu_file.exists():
                logger.warning(f"Arquivo CVU não encontrado: {cvu_file}")
                return []
            
            df = pd.read_parquet(cvu_file)
            
            # Identificar combinações únicas de ano, mês e semana
            available_combinations = df[['ano_referencia', 'mes_referencia', 'num_revisao']].drop_duplicates()
            available_combinations = available_combinations.sort_values(['ano_referencia', 'mes_referencia', 'num_revisao'])
            
            # Converter para lista de tuplas (year, month, week)
            available_weeks = []
            for _, row in available_combinations.iterrows():
                year = int(row['ano_referencia'])
                month = int(row['mes_referencia'])
                week = int(row['num_revisao'])
                available_weeks.append((year, month, week))
            
            logger.info(f"Semanas disponíveis encontradas: {len(available_weeks)}")
            if available_weeks:
                logger.info(f"Primeira: {available_weeks[0]}")
                logger.info(f"Última: {available_weeks[-1]}")
            
            return available_weeks
            
        except Exception as e:
            logger.error(f"Erro ao identificar semanas disponíveis: {e}")
            return []
    
    def run_full_pipeline(self):
        """Executa o pipeline completo"""
        logger.info("=" * 60)
        logger.info("INICIANDO PIPELINE CVU TERMICAS")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Etapa 1: Captura de dados
            logger.info("\n" + "=" * 40)
            logger.info("ETAPA 1: CAPTURA DE DADOS")
            logger.info("=" * 40)
            
            # Download de dados históricos
            self.data_ingest.download_historical_data()
            
            # Download do ano atual
            self.data_ingest.download_current_year()
            
            # Verificação
            if not self.data_ingest.verify_downloads():
                logger.error("Falha na verificação dos downloads")
                return False
            
            # Etapa 2: Processamento
            logger.info("\n" + "=" * 40)
            logger.info("ETAPA 2: PROCESSAMENTO DE DADOS")
            logger.info("=" * 40)
            
            if not self.data_processor.process_all():
                logger.error("Falha no processamento de dados")
                return False
            
            # Etapa 3: Visualização
            logger.info("\n" + "=" * 40)
            logger.info("ETAPA 3: GERAÇÃO DE VISUALIZAÇÕES")
            logger.info("=" * 40)
            
            if not self.data_visualizer.generate_all_visualizations():
                logger.error("Falha na geração de visualizações")
                return False
            
            # Etapa 4: Geração de curva de mérito (semana atual)
            logger.info("\n" + "=" * 40)
            logger.info("ETAPA 4: GERAÇÃO DE CURVA DE MÉRITO")
            logger.info("=" * 40)
            
            try:
                # Identificar as últimas semanas disponíveis para comparação
                available_weeks = self._get_available_weeks()
                
                if len(available_weeks) >= 1:
                    # Usar a última semana disponível
                    latest_week = available_weeks[-1]  # Última semana
                    
                    logger.info(f"Gerando curva de mérito para semana atual: {latest_week[0]}/{latest_week[1]:02d} - semana {latest_week[2]}")
                    
                    # Gerar curva de mérito para a última semana
                    merit_result = self.merit_order_generator.generate_merit_order(latest_week[0], latest_week[1], latest_week[2])
                    if merit_result:
                        logger.info("Curva de mérito gerada com sucesso")
                    else:
                        logger.warning("Falha na geração da curva de mérito")
                    
                    # Gerar comparação histórica (atual vs 2 meses atrás vs 1 ano atrás)
                    logger.info(f"Gerando comparação histórica da semana atual com 2 meses atrás e 1 ano atrás")
                    
                    historical_comparison = self.merit_order_generator.compare_with_historical_data(latest_week)
                    if historical_comparison:
                        logger.info("Comparação histórica de curvas de mérito gerada com sucesso")
                    else:
                        logger.warning("Falha na geração da comparação histórica de curvas de mérito")
                        
                else:
                    # Fallback: gerar apenas para a semana atual se não há dados suficientes
                    now = datetime.now()
                    current_year = now.year
                    current_month = now.month
                    week_of_month = (now.day - 1) // 7 + 1
                    if week_of_month > 4:
                        week_of_month = 4
                    
                    logger.info(f"Dados insuficientes para comparação. Gerando apenas para {current_year}/{current_month:02d} - semana {week_of_month}")
                    merit_result = self.merit_order_generator.generate_merit_order(current_year, current_month, week_of_month)
                    if merit_result:
                        logger.info("Curva de mérito gerada com sucesso")
                    else:
                        logger.warning("Falha na geração da curva de mérito")
                    
                    # Tentar comparação histórica mesmo assim
                    logger.info("Tentando comparação histórica com a semana atual do sistema")
                    historical_comparison = self.merit_order_generator.compare_with_historical_data((current_year, current_month, week_of_month))
                    if historical_comparison:
                        logger.info("Comparação histórica gerada com sucesso")
                    else:
                        logger.warning("Falha na geração da comparação histórica")
                    
            except Exception as e:
                logger.warning(f"Erro na geração da curva de mérito: {e} (continuando com o pipeline)")
            
            # Etapa 5: Geração de relatório
            logger.info("\n" + "=" * 40)
            logger.info("ETAPA 5: GERAÇÃO DE RELATÓRIO")
            logger.info("=" * 40)
            
            if not self.report_generator.generate_report():
                logger.error("Falha na geração do relatório")
                return False
            
            # Resumo final
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE CONCLUÍDO COM SUCESSO!")
            logger.info(f"Tempo total de execução: {duration}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro durante a execução do pipeline: {e}")
            return False
    
    def run_data_update_only(self):
        """Executa apenas a atualização de dados (2025)"""
        logger.info("Executando apenas atualização de dados...")
        
        try:
            # Download apenas do ano atual
            success = self.data_ingest.download_current_year()
            
            if success:
                # Reprocessar dados
                self.data_processor.process_all()
                logger.info("Atualização de dados concluída com sucesso")
                return True
            else:
                logger.error("Falha na atualização de dados")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante atualização: {e}")
            return False
    
    def run_visualization_only(self):
        """Executa apenas a geração de visualizações"""
        logger.info("Executando apenas geração de visualizações...")
        
        try:
            success = self.data_visualizer.generate_all_visualizations()
            
            if success:
                logger.info("Visualizações geradas com sucesso")
                return True
            else:
                logger.error("Falha na geração de visualizações")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante geração de visualizações: {e}")
            return False
    
    def run_report_only(self):
        """Executa apenas a geração de relatório"""
        logger.info("Executando apenas geração de relatório...")
        
        try:
            success = self.report_generator.generate_report()
            
            if success:
                logger.info("Relatório gerado com sucesso")
                return True
            else:
                logger.error("Falha na geração do relatório")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante geração do relatório: {e}")
            return False
    
    def run_merit_order(self, year, month, week):
        """Executa geração da curva de mérito para uma semana específica"""
        logger.info(f"Executando geração da curva de mérito para {year}/{month:02d} - semana {week}...")
        
        try:
            success = self.merit_order_generator.generate_merit_order(year, month, week)
            
            if success:
                logger.info("Curva de mérito gerada com sucesso")
                return True
            else:
                logger.error("Falha na geração da curva de mérito")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante geração da curva de mérito: {e}")
            return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Pipeline CVU Termicas')
    parser.add_argument('--mode', choices=['full', 'update', 'viz', 'report', 'merit'], 
                       default='full', help='Modo de execução')
    parser.add_argument('--config', default='config.yaml', 
                       help='Caminho para arquivo de configuração')
    parser.add_argument('--year', type=int, help='Ano para curva de mérito')
    parser.add_argument('--month', type=int, help='Mês para curva de mérito')
    parser.add_argument('--week', type=int, help='Semana para curva de mérito')
    
    args = parser.parse_args()
    
    # Inicializar pipeline
    pipeline = CVUTermicasPipeline(args.config)
    
    # Executar conforme modo selecionado
    if args.mode == 'full':
        success = pipeline.run_full_pipeline()
    elif args.mode == 'update':
        success = pipeline.run_data_update_only()
    elif args.mode == 'viz':
        success = pipeline.run_visualization_only()
    elif args.mode == 'report':
        success = pipeline.run_report_only()
    elif args.mode == 'merit':
        if args.year and args.month and args.week:
            success = pipeline.run_merit_order(args.year, args.month, args.week)
        else:
            logger.error("Para o modo 'merit', especifique --year, --month e --week")
            sys.exit(1)
    
    if success:
        logger.info("Execução concluída com sucesso")
        sys.exit(0)
    else:
        logger.error("Execução falhou")
        sys.exit(1)

if __name__ == "__main__":
    main() 