"""
Script para processamento de dados CVU de usinas térmicas
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import yaml
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

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

class DataProcessor:
    """Classe para processamento de dados CVU"""
    
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
        
        # Construir caminhos absolutos baseados no diretório raiz do projeto
        self.raw_data_path = self.project_root / self.config['paths']['raw_data']
        self.processed_data_path = self.project_root / self.config['paths']['processed_data']
        self.viz_data_path = self.project_root / self.config['paths']['viz_data']
        self.years = self.config['data']['years']
        
        # Criar diretórios se não existirem
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        self.viz_data_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Diretórios configurados:")
        logger.info(f"  Raw data: {self.raw_data_path}")
        logger.info(f"  Processed data: {self.processed_data_path}")
        logger.info(f"  Viz data: {self.viz_data_path}")
    
    def load_all_data(self):
        """Carrega todos os dados brutos"""
        logger.info("Carregando todos os dados...")
        
        all_data = []
        for year in self.years:
            filename = f"CVU_USINA_TERMICA_{year}.parquet"
            filepath = self.raw_data_path / filename
            
            if filepath.exists():
                try:
                    df = pd.read_parquet(filepath)
                    df['ano'] = year
                    all_data.append(df)
                    logger.info(f"Carregado {year}: {len(df)} registros")
                except Exception as e:
                    logger.error(f"Erro ao carregar {filename}: {e}")
            else:
                logger.warning(f"Arquivo {filename} não encontrado")
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Total de registros: {len(combined_df)}")
            return combined_df
        else:
            logger.error("Nenhum dado foi carregado")
            return None
    
    def clean_data(self, df):
        """Limpa e padroniza os dados"""
        logger.info("Iniciando limpeza dos dados...")
        
        # Verificar colunas
        logger.info(f"Colunas originais: {list(df.columns)}")
        
        # Mapear colunas para nomes padronizados
        column_mapping = {
            'dat_iniciosemana': 'data_inicio',
            'dat_fimsemana': 'data_fim',
            'ano_referencia': 'ano_referencia',
            'mes_referencia': 'mes',
            'nom_usina': 'usina',
            'val_cvu': 'cvu',
            'nom_subsistema': 'subsistema'
        }
        
        # Renomear colunas
        df = df.rename(columns=column_mapping)
        
        # Remover duplicatas
        initial_rows = len(df)
        df = df.drop_duplicates()
        logger.info(f"Removidas {initial_rows - len(df)} duplicatas")
        
        # Converter tipos de dados
        if 'data_inicio' in df.columns:
            df['data_inicio'] = pd.to_datetime(df['data_inicio'], errors='coerce')
        
        if 'data_fim' in df.columns:
            df['data_fim'] = pd.to_datetime(df['data_fim'], errors='coerce')
        
        if 'cvu' in df.columns:
            df['cvu'] = pd.to_numeric(df['cvu'], errors='coerce')
        
        # Remover valores nulos críticos
        if 'usina' in df.columns:
            df = df.dropna(subset=['usina'])
        
        # Filtrar valores absurdos de CVU
        if 'cvu' in df.columns:
            # Remover valores negativos e muito altos
            df = df[(df['cvu'] >= 0) & (df['cvu'] <= 10000)]
        
        logger.info(f"Dados limpos: {len(df)} registros")
        return df
    
    def add_features(self, df):
        """Adiciona features derivadas"""
        logger.info("Adicionando features derivadas...")
        
        if 'data_inicio' in df.columns:
            # Extrair componentes de data
            df['ano_feature'] = df['data_inicio'].dt.year
            df['mes_feature'] = df['data_inicio'].dt.month
            df['dia'] = df['data_inicio'].dt.day
            df['dia_semana'] = df['data_inicio'].dt.dayofweek
            df['trimestre'] = df['data_inicio'].dt.quarter
        
        if 'cvu' in df.columns:
            # Estatísticas por usina
            usina_stats = df.groupby('usina')['cvu'].agg([
                'mean', 'std', 'min', 'max', 'count'
            ]).reset_index()
            usina_stats.columns = ['usina', 'cvu_mean', 'cvu_std', 'cvu_min', 'cvu_max', 'cvu_count']
            
            # Merge com dados originais
            df = df.merge(usina_stats, on='usina', how='left')
        
        logger.info("Features derivadas adicionadas")
        return df
    
    def create_summary_tables(self, df):
        """Cria tabelas de resumo"""
        logger.info("Criando tabelas de resumo...")
        
        summaries = {}
        
        # Resumo por ano
        if 'ano_referencia' in df.columns and 'cvu' in df.columns:
            yearly_summary = df.groupby('ano_referencia')['cvu'].agg([
                'count', 'mean', 'std', 'min', 'max'
            ]).reset_index()
            yearly_summary.columns = ['ano', 'registros', 'cvu_medio', 'cvu_desvio', 'cvu_min', 'cvu_max']
            summaries['yearly'] = yearly_summary
        
        # Resumo por usina
        if 'usina' in df.columns and 'cvu' in df.columns:
            usina_summary = df.groupby('usina')['cvu'].agg([
                'count', 'mean', 'std', 'min', 'max'
            ]).reset_index()
            usina_summary.columns = ['usina', 'registros', 'cvu_medio', 'cvu_desvio', 'cvu_min', 'cvu_max']
            summaries['usina'] = usina_summary
        
        # Resumo mensal
        if 'mes' in df.columns and 'cvu' in df.columns:
            monthly_summary = df.groupby(['ano_referencia', 'mes'])['cvu'].agg([
                'count', 'mean', 'std', 'min', 'max'
            ]).reset_index()
            monthly_summary.columns = ['ano', 'mes', 'registros', 'cvu_medio', 'cvu_desvio', 'cvu_min', 'cvu_max']
            summaries['monthly'] = monthly_summary
        
        return summaries
    
    def save_processed_data(self, df, summaries):
        """Salva dados processados"""
        logger.info("Salvando dados processados...")
        
        # Salvar dados principais
        main_file = self.processed_data_path / "cvu_complete.parquet"
        df.to_parquet(main_file, index=False)
        logger.info(f"Dados principais salvos: {main_file}")
        
        # Salvar resumos
        for name, summary_df in summaries.items():
            summary_file = self.processed_data_path / f"summary_{name}.parquet"
            summary_df.to_parquet(summary_file, index=False)
            logger.info(f"Resumo {name} salvo: {summary_file}")
        
        # Salvar dados para visualização
        viz_file = self.viz_data_path / "cvu_viz.parquet"
        df.to_parquet(viz_file, index=False)
        logger.info(f"Dados para visualização salvos: {viz_file}")
    
    def process_all(self):
        """Executa todo o pipeline de processamento"""
        logger.info("Iniciando pipeline de processamento...")
        
        # Carregar dados
        df = self.load_all_data()
        if df is None:
            return False
        
        # Limpar dados
        df = self.clean_data(df)
        
        # Adicionar features
        df = self.add_features(df)
        
        # Criar resumos
        summaries = self.create_summary_tables(df)
        
        # Salvar dados
        self.save_processed_data(df, summaries)
        
        logger.info("Pipeline de processamento concluído")
        return True

def main():
    """Função principal"""
    processor = DataProcessor()
    success = processor.process_all()
    
    if success:
        logger.info("Processamento concluído com sucesso")
    else:
        logger.error("Falha no processamento")

if __name__ == "__main__":
    main() 