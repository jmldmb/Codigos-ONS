"""
Orquestrador principal do projeto Captura ENA
"""
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .data.ena_processor import ENAProcessor
from .data.pmo_processor import PMOProcessor
from .data.ena_diario_processor import ENADiarioProcessor
from .data.ena_mensal_processor import ENAMensalProcessor
from .data.downloader import ENADownloader
from .visualization.plotter import ENAPlotter
from .utils.logger import get_logger
from .utils.config import config

logger = get_logger(__name__)


class ENAOrchestrator:
    """Orquestrador principal para o processamento de dados ENA"""
    
    def __init__(self):
        """Inicializa o orquestrador"""
        self.config = config
        self.logger = logger
        
        # Inicializar processadores
        self.ena_processor = ENAProcessor()
        self.pmo_processor = PMOProcessor()
        self.ena_diario_processor = ENADiarioProcessor()
        self.ena_mensal_processor = ENAMensalProcessor()
        self.downloader = ENADownloader()
        self.plotter = ENAPlotter()
        
        # Dados processados
        self.final_combined_data = None
        self.grouped_data = None
        self.grouped_data_pmo = None
        self.grouped_ena_data = None
        self.ena_mensal_data = None
    
    def setup_directories(self):
        """Cria os diretórios necessários se não existirem"""
        directories = [
            self.config.get_path('paths.raw_data'),
            self.config.get_path('paths.processed_data'),
            self.config.get_path('paths.outputs'),
            self.config.get_path('paths.logs'),
            self.config.get_path('paths.reports')
        ]
        
        for directory in directories:
            if directory:
                directory.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Diretório criado/verificado: {directory}")
    
    def download_ena_data(self, year: int = None) -> bool:
        """
        Baixa dados ENA diários
        
        Args:
            year: Ano para download (padrão: ano atual)
            
        Returns:
            True se o download foi bem-sucedido
        """
        self.logger.info("Iniciando download de dados ENA diários")
        return self.downloader.download_ena_diario(year)
    
    def process_ena_pdp_files(self, folder_path: str = None) -> pd.DataFrame:
        """
        Processa arquivos ENA PDP (projeções diárias)
        
        Args:
            folder_path: Caminho da pasta com os arquivos (padrão: pasta configurada)
            
        Returns:
            DataFrame com os dados processados
        """
        if folder_path is None:
            folder_path = (self.config.get_path('paths.raw_data') / 
                          self.config.get('data.ena_pdp_folder'))
        
        self.logger.info(f"Processando arquivos ENA PDP em: {folder_path}")
        
        # Processar todos os arquivos
        self.final_combined_data = self.ena_processor.process_all_files(str(folder_path))
        
        if not self.final_combined_data.empty:
            # Agrupar dados
            self.grouped_data = self.ena_processor.group_data(self.final_combined_data)
            self.logger.info(f"Processamento ENA PDP concluído. Registros: {len(self.final_combined_data)}")
        else:
            self.logger.warning("Nenhum dado ENA PDP foi processado")
        
        return self.final_combined_data
    
    def process_pmo_data(self, folder_path: str = None) -> pd.DataFrame:
        """
        Processa dados PMO
        
        Args:
            folder_path: Caminho da pasta com o arquivo PMO (padrão: pasta configurada)
            
        Returns:
            DataFrame com os dados PMO processados
        """
        if folder_path is None:
            folder_path = (self.config.get_path('paths.raw_data') / 
                          self.config.get('data.ena_pdp_folder'))
        
        self.logger.info(f"Processando dados PMO em: {folder_path}")
        
        # Ler arquivo PMO
        df_pmo = self.pmo_processor.read_pmo_mensal_file(str(folder_path))
        
        if df_pmo is not None:
            # Processar dados PMO
            self.grouped_data_pmo = self.pmo_processor.process_pmo_data(df_pmo)
            self.logger.info(f"Processamento PMO concluído. Registros: {len(self.grouped_data_pmo)}")
        else:
            self.logger.warning("Nenhum dado PMO foi processado")
            self.grouped_data_pmo = pd.DataFrame()
        
        return self.grouped_data_pmo
    
    def process_ena_diario_data(self, year: int = None) -> pd.DataFrame:
        """
        Processa dados ENA diários
        
        Args:
            year: Ano dos dados (padrão: ano atual)
            
        Returns:
            DataFrame com os dados ENA diários processados
        """
        if year is None:
            year = datetime.now().year
        
        self.logger.info(f"Processando dados ENA diários para o ano {year}")
        
        # Processar dados ENA diários
        self.grouped_ena_data = self.ena_diario_processor.get_ena_diario_by_year(year)
        
        if not self.grouped_ena_data.empty:
            self.logger.info(f"Processamento ENA diário concluído. Registros: {len(self.grouped_ena_data)}")
        else:
            self.logger.warning("Nenhum dado ENA diário foi processado")
        
        return self.grouped_ena_data
    
    def process_ena_mensal_data(self) -> pd.DataFrame:
        """
        Processa dados ENA diários para calcular médias mensais consolidadas
        
        Returns:
            DataFrame com dados ENA mensais
        """
        self.logger.info("Processando dados ENA para cálculo de médias mensais...")
        
        # Ler todos os arquivos ENA diários disponíveis (dados completos, não filtrados)
        all_ena_data = self.ena_diario_processor.read_all_ena_diario_files()
        
        if all_ena_data.empty:
            self.logger.warning("Nenhum dado ENA diário disponível para processamento mensal")
            return pd.DataFrame()
        
        # Processar dados ENA mensais usando dados completos
        self.ena_mensal_data = self.ena_mensal_processor.process_ena_mensal_data(all_ena_data)
        
        if not self.ena_mensal_data.empty:
            self.logger.info(f"Processamento ENA mensal concluído. Registros: {len(self.ena_mensal_data)}")
        else:
            self.logger.warning("Nenhum dado ENA mensal foi processado")
        
        return self.ena_mensal_data
    
    def create_visualizations(self, save_reports: bool = True) -> Dict[str, str]:
        """
        Cria visualizações dos dados
        
        Args:
            save_reports: Se deve salvar os relatórios
            
        Returns:
            Dicionário com os caminhos dos arquivos gerados
        """
        reports = {}
        
        if save_reports:
            reports_dir = self.config.get_path('paths.reports')
            reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar gráfico hairy chart
        if self.grouped_data is not None and not self.grouped_data.empty:
            hairy_chart_path = None
            if save_reports:
                hairy_chart_path = reports_dir / "hairy_chart.png"
            
            fig = self.plotter.create_hairy_chart(
                self.grouped_data, 
                self.grouped_data_pmo,
                self.grouped_ena_data,
                str(hairy_chart_path) if hairy_chart_path else None
            )
            
            if hairy_chart_path:
                reports['hairy_chart'] = str(hairy_chart_path)
                self.logger.info(f"Gráfico hairy chart salvo em: {hairy_chart_path}")
        
        # Criar gráfico comparativo
        if (self.grouped_ena_data is not None and not self.grouped_ena_data.empty and
            self.grouped_data is not None and not self.grouped_data.empty):
            
            comparison_chart_path = None
            if save_reports:
                comparison_chart_path = reports_dir / "comparison_chart.png"
            
            fig = self.plotter.create_comparison_chart(
                self.grouped_ena_data,
                self.grouped_data,
                self.grouped_data_pmo,
                str(comparison_chart_path) if comparison_chart_path else None
            )
            
            if comparison_chart_path:
                reports['comparison_chart'] = str(comparison_chart_path)
                self.logger.info(f"Gráfico comparativo salvo em: {comparison_chart_path}")
        
        # Criar gráfico de ranking mensal (mês atual)
        if self.ena_mensal_data is not None and not self.ena_mensal_data.empty:
            from datetime import datetime
            from dateutil.relativedelta import relativedelta
            
            current_date = datetime.now()
            
            # Gráfico para o mês atual
            monthly_ranking_current_path = None
            if save_reports:
                monthly_ranking_current_path = reports_dir / "monthly_ranking_current.png"
            
            fig_current = self.plotter.create_monthly_ranking_chart(
                self.ena_mensal_data,
                str(monthly_ranking_current_path) if monthly_ranking_current_path else None,
                target_month=current_date.month,
                target_year=current_date.year
            )
            
            if monthly_ranking_current_path:
                reports['monthly_ranking_current'] = str(monthly_ranking_current_path)
                self.logger.info(f"Gráfico de ranking mensal (atual) salvo em: {monthly_ranking_current_path}")
            
            # Gráfico para o mês anterior
            previous_date = current_date - relativedelta(months=1)
            monthly_ranking_previous_path = None
            if save_reports:
                monthly_ranking_previous_path = reports_dir / "monthly_ranking_previous.png"
            
            fig_previous = self.plotter.create_monthly_ranking_chart(
                self.ena_mensal_data,
                str(monthly_ranking_previous_path) if monthly_ranking_previous_path else None,
                target_month=previous_date.month,
                target_year=previous_date.year
            )
            
            if monthly_ranking_previous_path:
                reports['monthly_ranking_previous'] = str(monthly_ranking_previous_path)
                self.logger.info(f"Gráfico de ranking mensal (anterior) salvo em: {monthly_ranking_previous_path}")
        
        return reports
    
    def save_processed_data(self) -> Dict[str, str]:
        """
        Salva os dados processados em arquivos
        
        Returns:
            Dicionário com os caminhos dos arquivos salvos
        """
        saved_files = {}
        outputs_dir = self.config.get_path('paths.outputs')
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Salvar dados ENA PDP
        if self.final_combined_data is not None and not self.final_combined_data.empty:
            ena_pdp_path = outputs_dir / "final_combined_data.xlsx"
            self.final_combined_data.to_excel(ena_pdp_path, index=False)
            saved_files['ena_pdp'] = str(ena_pdp_path)
            self.logger.info(f"Dados ENA PDP salvos em: {ena_pdp_path}")
        
        # Salvar dados agrupados
        if self.grouped_data is not None and not self.grouped_data.empty:
            grouped_data_path = outputs_dir / "grouped_data.xlsx"
            self.grouped_data.to_excel(grouped_data_path, index=False)
            saved_files['grouped_data'] = str(grouped_data_path)
            self.logger.info(f"Dados agrupados salvos em: {grouped_data_path}")
        
        # Salvar dados PMO
        if self.grouped_data_pmo is not None and not self.grouped_data_pmo.empty:
            pmo_data_path = outputs_dir / "pmo_data.xlsx"
            self.grouped_data_pmo.to_excel(pmo_data_path, index=False)
            saved_files['pmo_data'] = str(pmo_data_path)
            self.logger.info(f"Dados PMO salvos em: {pmo_data_path}")
        
        # Salvar dados ENA diário
        if self.grouped_ena_data is not None and not self.grouped_ena_data.empty:
            ena_diario_path = outputs_dir / "ena_diario_data.xlsx"
            self.grouped_ena_data.to_excel(ena_diario_path, index=False)
            saved_files['ena_diario'] = str(ena_diario_path)
            self.logger.info(f"Dados ENA diário salvos em: {ena_diario_path}")
        
        # Salvar dados ENA mensal
        if self.ena_mensal_data is not None and not self.ena_mensal_data.empty:
            ena_mensal_path = outputs_dir / "ena_mensal_data.xlsx"
            self.ena_mensal_data.to_excel(ena_mensal_path, index=False)
            saved_files['ena_mensal'] = str(ena_mensal_path)
            self.logger.info(f"Dados ENA mensal salvos em: {ena_mensal_path}")
        
        return saved_files
    
    def run_full_pipeline(self, download_ena: bool = True, 
                         process_pmo: bool = True,
                         create_visualizations: bool = True,
                         save_data: bool = True) -> Dict[str, Any]:
        """
        Executa o pipeline completo de processamento
        
        Args:
            download_ena: Se deve baixar dados ENA diários
            process_pmo: Se deve processar dados PMO
            create_visualizations: Se deve criar visualizações
            save_data: Se deve salvar os dados processados
            
        Returns:
            Dicionário com os resultados do pipeline
        """
        self.logger.info("Iniciando pipeline completo de processamento ENA")
        
        results = {
            'success': True,
            'errors': [],
            'files_saved': {},
            'reports_created': {}
        }
        
        try:
            # Configurar diretórios
            self.setup_directories()
            
            # Download de dados ENA diários
            if download_ena:
                download_success = self.download_ena_data()
                if not download_success:
                    results['errors'].append("Falha no download de dados ENA diários")
            
            # Processar arquivos ENA PDP
            ena_pdp_data = self.process_ena_pdp_files()
            if ena_pdp_data.empty:
                results['errors'].append("Nenhum dado ENA PDP foi processado")
            
            # Processar dados PMO
            if process_pmo:
                pmo_data = self.process_pmo_data()
            
            # Processar dados ENA diários
            ena_diario_data = self.process_ena_diario_data()
            
            # Processar dados ENA mensais
            ena_mensal_data = self.process_ena_mensal_data()
            
            # Criar visualizações
            if create_visualizations:
                reports = self.create_visualizations(save_reports=True)
                results['reports_created'] = reports
            
            # Salvar dados processados
            if save_data:
                saved_files = self.save_processed_data()
                results['files_saved'] = saved_files
            
            self.logger.info("Pipeline completo executado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro durante a execução do pipeline: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna um resumo dos dados processados
        
        Returns:
            Dicionário com o resumo dos dados
        """
        summary = {
            'ena_pdp_records': 0,
            'grouped_records': 0,
            'pmo_records': 0,
            'ena_diario_records': 0,
            'ena_mensal_records': 0,
            'date_ranges': {}
        }
        
        if self.final_combined_data is not None and not self.final_combined_data.empty:
            summary['ena_pdp_records'] = len(self.final_combined_data)
            summary['date_ranges']['ena_pdp'] = {
                'data_min': self.final_combined_data['data'].min(),
                'data_max': self.final_combined_data['data'].max(),
                'data_projecao_min': self.final_combined_data['data_projecao'].min(),
                'data_projecao_max': self.final_combined_data['data_projecao'].max()
            }
        
        if self.grouped_data is not None and not self.grouped_data.empty:
            summary['grouped_records'] = len(self.grouped_data)
        
        if self.grouped_data_pmo is not None and not self.grouped_data_pmo.empty:
            summary['pmo_records'] = len(self.grouped_data_pmo)
        
        if self.grouped_ena_data is not None and not self.grouped_ena_data.empty:
            summary['ena_diario_records'] = len(self.grouped_ena_data)
            summary['date_ranges']['ena_diario'] = {
                'data_min': self.grouped_ena_data['data'].min(),
                'data_max': self.grouped_ena_data['data'].max()
            }
        
        if self.ena_mensal_data is not None and not self.ena_mensal_data.empty:
            summary['ena_mensal_records'] = len(self.ena_mensal_data)
            summary['date_ranges']['ena_mensal'] = {
                'data_min': self.ena_mensal_data['data'].min(),
                'data_max': self.ena_mensal_data['data'].max()
            }
        
        return summary

