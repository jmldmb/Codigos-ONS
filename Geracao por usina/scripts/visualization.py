"""
Módulo para visualização e geração de gráficos
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import seaborn as sns
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.config import config
from utils.logger import logger

# Configuração do matplotlib
plt.style.use('default')
sns.set_palette("husl")


class DataVisualizer:
    """Classe para visualização de dados de geração"""
    
    def __init__(self):
        """Inicializa o visualizador"""
        self.figsize = tuple(config.get('visualization.figsize', [12, 8]))
        self.dpi = config.get('visualization.dpi', 300)
        self.save_format = config.get('visualization.save_format', 'png')
        self.colors = config.get('visualization.colors', {})
        self.anos_analise = config.get('processing.anos_analise', [2024, 2025])
        
        # Cria diretório de saída
        self.output_dir = config.get_path('paths.output.charts')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_geracao_renovavel_vs_certificacao(self, 
                                             geracao_df: pd.DataFrame, 
                                             p50_df: pd.DataFrame, 
                                             p90_df: pd.DataFrame) -> None:
        """
        Gera gráficos comparando geração renovável vs certificação P50/P90
        
        Args:
            geracao_df: DataFrame com dados de geração
            p50_df: DataFrame com dados P50
            p90_df: DataFrame com dados P90
        """
        logger.info("Gerando gráficos de geração renovável vs certificação")
        
        # Prepara dados
        geracao_df["mes_ano"] = pd.to_datetime(geracao_df["mes_ano"])
        df = geracao_df[geracao_df["mes_ano"].dt.year.isin(self.anos_analise)].copy()
        df["ano"] = df["mes_ano"].dt.year
        df["mes"] = df["mes_ano"].dt.month
        
        # Loop por empresa
        for empresa, sub in df.groupby("empresa"):
            logger.info(f"Gerando gráfico para empresa: {empresa}")
            
            # Dados reais (verificados)
            real_tab = (
                sub.pivot_table(index="mes", columns="ano",
                                values="val_geracaoverificada",
                                aggfunc="sum")
                   .reindex(range(1,13), fill_value=0.0)
            )
            vals_2024 = real_tab.get(2024, pd.Series(0, index=real_tab.index))
            vals_2025 = real_tab.get(2025, pd.Series(0, index=real_tab.index))
            
            # Dados estimados (potencial)
            real_tab_estimado = (
                sub.pivot_table(index="mes", columns="ano",
                                values="val_geracaoestimada",
                                aggfunc="sum")
                   .reindex(range(1,13), fill_value=0.0)
            )
            vals_2024_estimado = real_tab_estimado.get(2024, pd.Series(0, index=real_tab.index))
            vals_2025_estimado = real_tab_estimado.get(2025, pd.Series(0, index=real_tab.index))
            
            # Dados P50 e P90
            if not p50_df.empty and 'Empresa' in p50_df.columns:
                p50_sub = p50_df[p50_df["Empresa"] == empresa]
                if 'mes' in p50_sub.columns:
                    p50_vals = p50_sub.set_index("mes")["p50_mwm"].reindex(range(1,13), fill_value=np.nan)
                else:
                    p50_vals = pd.Series(np.nan, index=range(1,13))
            else:
                p50_vals = pd.Series(np.nan, index=range(1,13))
            
            if not p90_df.empty and 'Empresa' in p90_df.columns:
                p90_sub = p90_df[p90_df["Empresa"] == empresa]
                if 'mes' in p90_sub.columns:
                    p90_vals = p90_sub.set_index("mes")["p90_mwm"].reindex(range(1,13), fill_value=np.nan)
                else:
                    p90_vals = pd.Series(np.nan, index=range(1,13))
            else:
                p90_vals = pd.Series(np.nan, index=range(1,13))
            
            # Cria gráfico
            self._create_geracao_chart(
                empresa=empresa,
                vals_2024=vals_2024,
                vals_2025=vals_2025,
                vals_2024_estimado=vals_2024_estimado,
                vals_2025_estimado=vals_2025_estimado,
                p50_vals=p50_vals,
                p90_vals=p90_vals,
                chart_type="renovavel"
            )
    
    def plot_geracao_termica(self, geracao_df: pd.DataFrame) -> None:
        """
        Gera gráficos de geração térmica
        
        Args:
            geracao_df: DataFrame com dados de geração térmica
        """
        logger.info("Gerando gráficos de geração térmica")
        
        if geracao_df.empty:
            logger.warning("Dados de geração térmica vazios")
            return
        
        # Agrupa por empresa e combustível
        for (empresa, combustivel), sub in geracao_df.groupby(['empresa', 'nom_tipocombustivel']):
            logger.info(f"Gerando gráfico para {empresa} - {combustivel}")
            
            # Pivot table para anos e meses (usando val_geracao como no notebook original)
            pivot_data = sub.pivot_table(
                index='mes', 
                columns='ano', 
                values='val_geracao', 
                aggfunc='sum'
            ).fillna(0)
            
            # Cria gráfico
            self._create_termica_chart(
                empresa=empresa,
                combustivel=combustivel,
                pivot_data=pivot_data
            )
    
    def _create_geracao_chart(self, 
                            empresa: str,
                            vals_2024: pd.Series,
                            vals_2025: pd.Series,
                            vals_2024_estimado: pd.Series,
                            vals_2025_estimado: pd.Series,
                            p50_vals: pd.Series,
                            p90_vals: pd.Series,
                            chart_type: str) -> None:
        """
        Cria gráfico de geração
        
        Args:
            empresa: Nome da empresa
            vals_2024: Valores de 2024
            vals_2025: Valores de 2025
            vals_2024_estimado: Valores estimados de 2024
            vals_2025_estimado: Valores estimados de 2025
            p50_vals: Valores P50
            p90_vals: Valores P90
            chart_type: Tipo de gráfico
        """
        x = np.arange(1, 13)
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Plota linhas
        if 2024 in self.anos_analise:
            ax.plot(x, vals_2024, marker="o", linestyle="-",
                    color=self.colors.get('2024', '#1f77b4'), label="2024 (Real)")
            ax.plot(x, vals_2024_estimado, marker="", linestyle="--",
                    color=self.colors.get('2024', '#1f77b4'), alpha=0.7, 
                    label="2024 (Potencial)")
        
        if 2025 in self.anos_analise:
            ax.plot(x, vals_2025, marker="o", linestyle="-",
                    color=self.colors.get('2025', '#ff7f0e'), label="2025 (Real)")
            ax.plot(x, vals_2025_estimado, marker="", linestyle="--",
                    color=self.colors.get('estimado', '#ff7f0e'), alpha=0.7,
                    label="2025 (Potencial)")
        
        # Plota P50 e P90
        if not p50_vals.isna().all():
            ax.plot(x, p50_vals, marker="", linestyle=":",
                    color=self.colors.get('p50', '#2ca02c'), label="P50 (MWm)")
        
        if not p90_vals.isna().all():
            ax.plot(x, p90_vals, marker="", linestyle=":",
                    color=self.colors.get('p90', '#d62728'), label="P90 (MWm)")
        
        # Configurações do gráfico
        ax.set_xlabel("Mês")
        ax.set_ylabel("Geração (MWm)")
        ax.set_title(f"Geração verificada vs P50/P90 – {empresa}")
        ax.set_xticks(x)
        ax.set_xticklabels(range(1,13))
        ax.grid(axis="y", alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        # Salva gráfico
        filename = f"{empresa}_{chart_type}_vs_certificacao.{self.save_format}"
        file_path = self.output_dir / filename
        plt.savefig(file_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico salvo: {file_path}")
    
    def _create_termica_chart(self, 
                            empresa: str,
                            combustivel: str,
                            pivot_data: pd.DataFrame) -> None:
        """
        Cria gráfico de geração térmica
        
        Args:
            empresa: Nome da empresa
            combustivel: Tipo de combustível
            pivot_data: Dados pivotados
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Plota dados para cada ano
        for ano in pivot_data.columns:
            ax.plot(pivot_data.index, pivot_data[ano], 
                   marker="o", linestyle="-", label=f"{ano}")
        
        # Configurações do gráfico
        ax.set_xlabel("Mês")
        ax.set_ylabel("Geração Média (MW)")
        ax.set_title(f"Geração Térmica - {empresa} ({combustivel})")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(range(1, 13))
        ax.grid(axis="y", alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        # Salva gráfico
        filename = f"{empresa}_{combustivel}_geracao_termica.{self.save_format}"
        file_path = self.output_dir / filename
        plt.savefig(file_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico salvo: {file_path}")
    
    def create_summary_chart(self, geracao_df: pd.DataFrame) -> None:
        """
        Cria gráfico resumo de todas as empresas
        
        Args:
            geracao_df: DataFrame com dados de geração
        """
        logger.info("Gerando gráfico resumo")
        
        if geracao_df.empty:
            logger.warning("Dados vazios para gráfico resumo")
            return
        
        # Agrupa por empresa e mês/ano
        summary_data = geracao_df.groupby(['empresa', 'mes_ano'])['val_geracaoverificada'].sum().reset_index()
        summary_data['mes_ano'] = pd.to_datetime(summary_data['mes_ano'])
        summary_data['ano'] = summary_data['mes_ano'].dt.year
        summary_data['mes'] = summary_data['mes_ano'].dt.month
        
        # Filtra anos de análise
        summary_data = summary_data[summary_data['ano'].isin(self.anos_analise)]
        
        # Pivot para empresas vs meses
        pivot_summary = summary_data.pivot_table(
            index='mes', 
            columns='empresa', 
            values='val_geracaoverificada', 
            aggfunc='sum'
        ).fillna(0)
        
        # Cria gráfico
        fig, ax = plt.subplots(figsize=(15, 10))
        
        for empresa in pivot_summary.columns:
            ax.plot(pivot_summary.index, pivot_summary[empresa], 
                   marker="o", linestyle="-", label=empresa)
        
        ax.set_xlabel("Mês")
        ax.set_ylabel("Geração Total (MWm)")
        ax.set_title("Resumo de Geração por Empresa")
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(range(1, 13))
        ax.grid(axis="y", alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        
        # Salva gráfico
        filename = f"resumo_geracao_empresas.{self.save_format}"
        file_path = self.output_dir / filename
        plt.savefig(file_path, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico resumo salvo: {file_path}")
    
    def generate_all_charts(self, processed_data: Dict) -> None:
        """
        Gera todos os gráficos baseado nos dados processados
        
        Args:
            processed_data: Dicionário com dados processados
        """
        logger.info("Iniciando geração de todos os gráficos")
        
        try:
            # Gráficos de geração renovável
            if 'geracao_renovavel' in processed_data and not processed_data['geracao_renovavel'].empty:
                if 'certificacao' in processed_data:
                    self.plot_geracao_renovavel_vs_certificacao(
                        processed_data['geracao_renovavel'],
                        processed_data['certificacao'].get('p50', pd.DataFrame()),
                        processed_data['certificacao'].get('p90', pd.DataFrame())
                    )
                
                # Gráfico resumo
                self.create_summary_chart(processed_data['geracao_renovavel'])
            
            # Gráficos de geração térmica
            if 'geracao_termica' in processed_data and not processed_data['geracao_termica'].empty:
                self.plot_geracao_termica(processed_data['geracao_termica'])
            
            logger.info("Geração de todos os gráficos concluída com sucesso")
            
        except Exception as e:
            logger.error(f"Erro durante a geração de gráficos: {str(e)}")
            raise
