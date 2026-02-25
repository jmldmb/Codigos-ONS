"""
Módulo para processamento de dados de geração
"""
import os
import glob
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import config
from utils.logger import logger


class DataProcessor:
    """Classe para processamento de dados de geração"""
    
    def __init__(self):
        """Inicializa o processador"""
        self.anos_analise = config.get('processing.anos_analise', [2024, 2025])
    
    def load_parquet_files(self, data_dir: Path) -> pd.DataFrame:
        """
        Carrega e consolida arquivos parquet de um diretório
        
        Args:
            data_dir: Diretório com os arquivos parquet
            
        Returns:
            DataFrame consolidado
        """
        logger.info(f"Carregando arquivos parquet de: {data_dir}")
        
        # Lista todos os arquivos .parquet no diretório
        file_pattern = data_dir / "*.parquet"
        parquet_files = list(data_dir.glob("*.parquet"))
        
        if not parquet_files:
            logger.warning(f"Nenhum arquivo .parquet encontrado em: {data_dir}")
            return pd.DataFrame()
        
        # Lê cada arquivo e armazena os DataFrames em uma lista
        df_list = []
        for file in parquet_files:
            logger.info(f"Lendo: {file}")
            try:
                df = pd.read_parquet(file)
                df_list.append(df)
            except Exception as e:
                logger.error(f"Erro ao ler {file}: {str(e)}")
        
        if not df_list:
            logger.error("Nenhum arquivo foi carregado com sucesso")
            return pd.DataFrame()
        
        # Consolida todos os DataFrames em um único
        consolidated_df = pd.concat(df_list, ignore_index=True)
        logger.info(f"DataFrame consolidado com {len(consolidated_df)} registros")
        
        return consolidated_df
    
    def load_cadastro_data(self) -> Dict[str, pd.DataFrame]:
        """
        Carrega dados de cadastro
        
        Returns:
            Dicionário com os DataFrames de cadastro
        """
        logger.info("Carregando dados de cadastro")
        
        cadastro_dir = config.get_path('paths.data.cadastro')
        cadastros = {}
        
        # Arquivos de cadastro esperados
        cadastro_files = {
            'relacionamento_usina_empresa': 'RELACIONAMENTO_USINA_EMPRESA.xlsx',
            'relacionamento_usina_empresa_termo': 'RELACIONAMENTO_USINA_EMPRESA_TERMO.xlsx',
            'relacionamento_usina_conjunto': 'RELACIONAMENTO_USINA_CONJUNTO.xlsx',
            'classificacao_uhes': 'CLASSIFICACAO_UHES.xlsx',
            'geracao_certificada': 'GERACAO_CERTIFICADA.xlsx'
        }
        
        for key, filename in cadastro_files.items():
            file_path = cadastro_dir / filename
            if file_path.exists():
                try:
                    if key == 'geracao_certificada':
                        # Carrega as duas abas do arquivo de certificação
                        p90_df = pd.read_excel(file_path, sheet_name='P90')
                        p50_df = pd.read_excel(file_path, sheet_name='P50')
                        cadastros['p90'] = p90_df
                        cadastros['p50'] = p50_df
                    else:
                        cadastros[key] = pd.read_excel(file_path)
                    logger.info(f"Carregado: {filename}")
                except Exception as e:
                    logger.error(f"Erro ao carregar {filename}: {str(e)}")
            else:
                logger.warning(f"Arquivo não encontrado: {filename}")
        
        return cadastros
    
    def process_geracao_renovavel(self) -> pd.DataFrame:
        """
        Processa dados de geração renovável
        
        Returns:
            DataFrame processado
        """
        logger.info("Processando dados de geração renovável")
        
        # Carrega dados de geração
        geracao_dir = config.get_path('paths.data.geracao')
        consolidated_df = self.load_parquet_files(geracao_dir)
        
        if consolidated_df.empty:
            return pd.DataFrame()
        
        # Carrega dados de cadastro
        cadastros = self.load_cadastro_data()
        cadastro_df = cadastros.get('relacionamento_usina_empresa', pd.DataFrame())
        
        if cadastro_df.empty:
            logger.warning("Dados de cadastro não encontrados")
            return consolidated_df
        
        # Otimiza tipos de dados
        consolidated_df['ceg'] = consolidated_df['ceg'].astype('category')
        cadastro_df['ceg'] = cadastro_df['ceg'].astype('category')
        
        # Identifica CEGs ausentes
        cadastro_ceg = set(cadastro_df['ceg'].unique())
        consolidated_ceg = set(consolidated_df['ceg'].unique())
        missing_ceg = cadastro_ceg - consolidated_ceg
        
        if missing_ceg:
            logger.info(f"CEGs ausentes nos dados de geração: {len(missing_ceg)}")
        
        # Filtra dados para manter apenas CEGs do cadastro
        filtered_df = consolidated_df[consolidated_df['ceg'].isin(cadastro_df['ceg'])].copy()
        logger.info(f"Dados filtrados: {len(filtered_df)} registros")
        
        # Libera memória do dataframe consolidado
        del consolidated_df
        import gc
        gc.collect()
        
        # Merge com dados de cadastro
        merged_df = pd.merge(filtered_df, cadastro_df, on='ceg', how='left')
        
        # Processa timestamp
        merged_df['din_instante'] = pd.to_datetime(merged_df['din_instante'])
        merged_df['mes_ano'] = merged_df['din_instante'].dt.strftime('%Y-%m')
        
        # Filtra por anos de análise
        merged_df['ano'] = merged_df['din_instante'].dt.year
        merged_df = merged_df[merged_df['ano'].isin(self.anos_analise)]
        logger.info(f"Dados filtrados por anos de análise {self.anos_analise}: {len(merged_df)} registros")
        
        # Agrupa dados
        grouped_df = merged_df.groupby(
            ['Complexo', 'SPE', 'empresa', 'mes_ano'], 
            as_index=False
        )[['val_geracaoestimada', 'val_geracaoverificada']].mean()
        
        logger.info(f"Dados agrupados: {len(grouped_df)} registros")
        
        return grouped_df
    
    def process_geracao_termica(self) -> pd.DataFrame:
        """
        Processa dados de geração térmica seguindo a lógica do notebook original
        
        Returns:
            DataFrame processado
        """
        logger.info("Processando dados de geração térmica")
        
        # Carrega dados de geração horária
        geracao_dir = config.get_path('paths.data.geracao_base_horaria')
        consolidated_df = self.load_parquet_files(geracao_dir)
        
        if consolidated_df.empty:
            return pd.DataFrame()
        
        # Filtra apenas usinas térmicas (como no notebook original)
        geracao_usina_termo = consolidated_df.loc[consolidated_df['nom_tipousina'] == 'TÉRMICA']
        logger.info(f"Usinas térmicas encontradas: {len(geracao_usina_termo)} registros")
        
        # Carrega cadastro de usinas térmicas (usando o mesmo arquivo do notebook original)
        cadastros = self.load_cadastro_data()
        cadastro_df = cadastros.get('relacionamento_usina_empresa_termo', pd.DataFrame())
        
        if cadastro_df.empty:
            logger.warning("Cadastro de usinas térmicas não encontrado")
            return pd.DataFrame()
        
        # Filtra dados para manter apenas CEGs do cadastro (como no notebook original)
        df_filtrado = geracao_usina_termo[geracao_usina_termo['ceg'].isin(cadastro_df['ceg'])].copy()
        logger.info(f"Dados filtrados por cadastro: {len(df_filtrado)} registros")
        
        # Merge com dados de cadastro (como no notebook original)
        df_final = pd.merge(df_filtrado, cadastro_df[['empresa', 'ceg']], on='ceg', how='left')
        
        # Processa timestamp e valores (como no notebook original)
        df_final['din_instante'] = pd.to_datetime(df_final['din_instante'])
        df_final['val_geracao'] = pd.to_numeric(df_final['val_geracao'], errors='coerce')
        df_final['ano'] = df_final['din_instante'].dt.year
        df_final['mes'] = df_final['din_instante'].dt.month
        
        # Agrupa dados (como no notebook original - apenas média de val_geracao)
        resultado = df_final.groupby(['nom_usina', 'ceg', 'nom_tipocombustivel', 'ano', 'mes'])['val_geracao'].mean().reset_index()
        
        # Adiciona coluna empresa (que foi perdida no groupby)
        resultado = pd.merge(resultado, cadastro_df[['ceg', 'empresa']], on='ceg', how='left')
        
        # Reordena colunas para manter consistência
        resultado = resultado[['nom_usina', 'ceg', 'empresa', 'nom_tipocombustivel', 'ano', 'mes', 'val_geracao']]
        
        logger.info(f"Dados agrupados: {len(resultado)} registros")
        
        return resultado
    
    def process_certificacao_data(self) -> Dict[str, pd.DataFrame]:
        """
        Processa dados de certificação (P50 e P90)
        
        Returns:
            Dicionário com DataFrames de P50 e P90
        """
        logger.info("Processando dados de certificação")
        
        cadastros = self.load_cadastro_data()
        p50_df = cadastros.get('p50', pd.DataFrame())
        p90_df = cadastros.get('p90', pd.DataFrame())
        
        if p50_df.empty or p90_df.empty:
            logger.warning("Dados de certificação não encontrados")
            return {}
        
        def melt_cert(df_cert: pd.DataFrame, value_name: str) -> pd.DataFrame:
            """Converte colunas 1-12 para linhas, devolve empresa / mes / valor"""
            return (
                df_cert
                .melt(id_vars=["Empresa"], var_name="mes", value_name=value_name)
                .assign(mes=lambda d: d["mes"].astype(int))
            )
        
        p50_long = melt_cert(p50_df.copy(), "p50_mwm")
        p90_long = melt_cert(p90_df.copy(), "p90_mwm")
        
        logger.info(f"P50 processado: {len(p50_long)} registros")
        logger.info(f"P90 processado: {len(p90_long)} registros")
        
        return {'p50': p50_long, 'p90': p90_long}
    
    def save_processed_data(self, data: pd.DataFrame, filename: str) -> None:
        """
        Salva dados processados com verificação de tamanho
        
        Args:
            data: DataFrame a ser salvo
            filename: Nome do arquivo
        """
        output_dir = config.get_path('paths.output.data')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verifica se o DataFrame é muito grande para Excel
        max_excel_rows = 1000000  # Limite seguro do Excel
        max_excel_cols = 16384
        
        if len(data) > max_excel_rows or len(data.columns) > max_excel_cols:
            logger.warning(f"DataFrame muito grande para Excel: {len(data)} linhas x {len(data.columns)} colunas")
            
            # Salva como CSV (mais eficiente para grandes datasets)
            csv_path = output_dir / filename.replace('.xlsx', '.csv')
            data.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Dados salvos como CSV em: {csv_path}")
            
            # Salva uma amostra como Excel para visualização
            sample_size = min(10000, len(data))  # Máximo 10k linhas para Excel
            sample_data = data.sample(n=sample_size, random_state=42) if len(data) > sample_size else data
            
            excel_path = output_dir / filename.replace('.xlsx', '_sample.xlsx')
            sample_data.to_excel(excel_path, index=False)
            logger.info(f"Amostra salva como Excel em: {excel_path} ({sample_size} linhas)")
            
            # Salva estatísticas resumidas
            stats_path = output_dir / filename.replace('.xlsx', '_stats.txt')
            with open(stats_path, 'w', encoding='utf-8') as f:
                f.write(f"Estatísticas do Dataset: {filename}\n")
                f.write("=" * 50 + "\n")
                f.write(f"Total de linhas: {len(data):,}\n")
                f.write(f"Total de colunas: {len(data.columns)}\n")
                f.write(f"Tamanho em memória: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")
                f.write(f"Colunas: {', '.join(data.columns)}\n")
                if len(data) > 0:
                    f.write(f"\nPrimeiras 5 linhas:\n{data.head().to_string()}\n")
                    f.write(f"\nÚltimas 5 linhas:\n{data.tail().to_string()}\n")
                    f.write(f"\nTipos de dados:\n{data.dtypes.to_string()}\n")
            logger.info(f"Estatísticas salvas em: {stats_path}")
            
        else:
            # Salva normalmente como Excel
            file_path = output_dir / filename
            data.to_excel(file_path, index=False)
            logger.info(f"Dados salvos em: {file_path}")
    
    def process_all(self) -> Dict[str, pd.DataFrame]:
        """
        Processa todos os tipos de dados
        
        Returns:
            Dicionário com todos os dados processados
        """
        logger.info("Iniciando processamento de todos os dados")
        
        results = {}
        
        try:
            # Processa geração renovável
            results['geracao_renovavel'] = self.process_geracao_renovavel()
            
            # Processa geração térmica
            results['geracao_termica'] = self.process_geracao_termica()
            
            # Processa dados de certificação
            results['certificacao'] = self.process_certificacao_data()
            
            # Salva dados processados
            if not results['geracao_renovavel'].empty:
                self.save_processed_data(results['geracao_renovavel'], 'geracao_renovavel.xlsx')
            
            if not results['geracao_termica'].empty:
                self.save_processed_data(results['geracao_termica'], 'geracao_termica.xlsx')
            
            logger.info("Processamento de todos os dados concluído com sucesso")
            
        except Exception as e:
            logger.error(f"Erro durante o processamento: {str(e)}")
            raise
        
        return results
    
    def create_summary_datasets(self, results: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Cria datasets resumidos para análise mais eficiente
        
        Args:
            results: Dicionário com dados processados
            
        Returns:
            Dicionário com datasets resumidos
        """
        logger.info("Criando datasets resumidos")
        
        summary_datasets = {}
        
        # Resumo de geração renovável por empresa e mês
        if 'geracao_renovavel' in results and not results['geracao_renovavel'].empty:
            df_renovavel = results['geracao_renovavel'].copy()
            df_renovavel['mes_ano'] = pd.to_datetime(df_renovavel['mes_ano'])
            df_renovavel['ano'] = df_renovavel['mes_ano'].dt.year
            df_renovavel['mes'] = df_renovavel['mes_ano'].dt.month
            
            # Resumo mensal por empresa
            resumo_mensal = df_renovavel.groupby(['empresa', 'ano', 'mes']).agg({
                'val_geracaoverificada': ['sum', 'mean', 'count'],
                'val_geracaoestimada': ['sum', 'mean']
            }).reset_index()
            
            # Renomeia colunas
            resumo_mensal.columns = ['empresa', 'ano', 'mes', 
                                   'geracao_verificada_total', 'geracao_verificada_media', 'num_registros',
                                   'geracao_estimada_total', 'geracao_estimada_media']
            
            summary_datasets['resumo_renovavel_mensal'] = resumo_mensal
            
            # Resumo anual por empresa
            resumo_anual = df_renovavel.groupby(['empresa', 'ano']).agg({
                'val_geracaoverificada': ['sum', 'mean', 'count'],
                'val_geracaoestimada': ['sum', 'mean']
            }).reset_index()
            
            resumo_anual.columns = ['empresa', 'ano', 
                                  'geracao_verificada_total', 'geracao_verificada_media', 'num_registros',
                                  'geracao_estimada_total', 'geracao_estimada_media']
            
            summary_datasets['resumo_renovavel_anual'] = resumo_anual
        
        # Resumo de geração térmica por empresa e combustível
        if 'geracao_termica' in results and not results['geracao_termica'].empty:
            df_termica = results['geracao_termica'].copy()
            
            # Verifica se a coluna 'empresa' existe
            if 'empresa' in df_termica.columns:
                # Resumo mensal por empresa e combustível
                resumo_termica_mensal = df_termica.groupby(['empresa', 'nom_tipocombustivel', 'ano', 'mes']).agg({
                    'val_geracao_media': ['sum', 'mean'],
                    'val_geracao_total': 'sum',
                    'num_registros': 'sum'
                }).reset_index()
                
                resumo_termica_mensal.columns = ['empresa', 'combustivel', 'ano', 'mes',
                                               'geracao_media_total', 'geracao_media_media',
                                               'geracao_total', 'num_registros']
                
                summary_datasets['resumo_termica_mensal'] = resumo_termica_mensal
                
                # Resumo anual por empresa e combustível
                resumo_termica_anual = df_termica.groupby(['empresa', 'nom_tipocombustivel', 'ano']).agg({
                    'val_geracao_media': ['sum', 'mean'],
                    'val_geracao_total': 'sum',
                    'num_registros': 'sum'
                }).reset_index()
                
                resumo_termica_anual.columns = ['empresa', 'combustivel', 'ano',
                                              'geracao_media_total', 'geracao_media_media',
                                              'geracao_total', 'num_registros']
                
                summary_datasets['resumo_termica_anual'] = resumo_termica_anual
            else:
                # Resumo sem empresa (apenas por combustível)
                resumo_termica_mensal = df_termica.groupby(['nom_tipocombustivel', 'ano', 'mes']).agg({
                    'val_geracao_media': ['sum', 'mean'],
                    'val_geracao_total': 'sum',
                    'num_registros': 'sum'
                }).reset_index()
                
                resumo_termica_mensal.columns = ['combustivel', 'ano', 'mes',
                                               'geracao_media_total', 'geracao_media_media',
                                               'geracao_total', 'num_registros']
                
                summary_datasets['resumo_termica_mensal'] = resumo_termica_mensal
                
                # Resumo anual sem empresa
                resumo_termica_anual = df_termica.groupby(['nom_tipocombustivel', 'ano']).agg({
                    'val_geracao_media': ['sum', 'mean'],
                    'val_geracao_total': 'sum',
                    'num_registros': 'sum'
                }).reset_index()
                
                resumo_termica_anual.columns = ['combustivel', 'ano',
                                              'geracao_media_total', 'geracao_media_media',
                                              'geracao_total', 'num_registros']
                
                summary_datasets['resumo_termica_anual'] = resumo_termica_anual
        
        # Salva datasets resumidos
        for name, dataset in summary_datasets.items():
            if not dataset.empty:
                self.save_processed_data(dataset, f'{name}.xlsx')
        
        logger.info(f"Criados {len(summary_datasets)} datasets resumidos")
        return summary_datasets
