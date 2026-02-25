"""
Módulo de visualização para o projeto Captura ENA
"""
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from typing import Optional
from dateutil.relativedelta import relativedelta

from ..utils.logger import get_logger
from ..utils.config import config

logger = get_logger(__name__)


class ENAPlotter:
    """Classe para visualização de dados ENA"""
    
    def __init__(self):
        """Inicializa o plotter"""
        self.config = config
        self.logger = logger
    
    def _get_filter_range(self, grouped_data_pmo: pd.DataFrame = None) -> tuple:
        """
        Calcula o intervalo de filtro baseado na configuração
        
        Args:
            grouped_data_pmo: DataFrame com dados PMO para determinar data máxima
            
        Returns:
            Tupla com (data_inicio, data_fim) do período filtrado
        """
        # Obter configuração de meses para trás
        months_back = self.config.get('visualization.filter.months_back', 1)
        
        # Data atual
        current_date = datetime.now()
        
        # Primeiro dia do mês atual
        current_month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Primeiro dia do mês N meses atrás (configurável)
        start_date = current_month_start - relativedelta(months=months_back-1)
        
        # Determinar data final baseada nos dados PMO disponíveis
        if grouped_data_pmo is not None and not grouped_data_pmo.empty:
            # Usar a data máxima disponível nos dados PMO
            pmo_max_date = grouped_data_pmo['data_fim'].max()
            end_date = pmo_max_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            self.logger.info(f"Data final baseada em dados PMO: {end_date.strftime('%Y-%m-%d')}")
        else:
            # Se não há dados PMO, usar o último dia do mês atual
            end_date = current_month_start + relativedelta(months=1) - relativedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            self.logger.info(f"Data final baseada no mês atual: {end_date.strftime('%Y-%m-%d')}")
        
        self.logger.info(f"Filtro de {months_back} mês(es) para trás: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        
        return start_date, end_date
    

    
    def create_hairy_chart(self, grouped_data: pd.DataFrame, 
                          grouped_data_pmo: pd.DataFrame = None,
                          grouped_ena_data: pd.DataFrame = None,
                          save_path: str = None) -> plt.Figure:
        """
        Cria o gráfico "hairy chart" com as projeções de ENA
        
        Args:
            grouped_data: DataFrame com dados agrupados das projeções diárias
            grouped_data_pmo: DataFrame com dados PMO (opcional)
            grouped_ena_data: DataFrame com dados reais ENA (opcional)
            save_path: Caminho para salvar o gráfico (opcional)
            
        Returns:
            Figura do matplotlib
        """
        # Garantir que as colunas de data estão no formato correto
        grouped_data['data'] = pd.to_datetime(grouped_data['data'])
        grouped_data['data_projecao'] = pd.to_datetime(grouped_data['data_projecao'])
        
        if grouped_data_pmo is not None and not grouped_data_pmo.empty:
            grouped_data_pmo['data_inicio'] = pd.to_datetime(grouped_data_pmo['data_inicio'])
            grouped_data_pmo['data_fim'] = pd.to_datetime(grouped_data_pmo['data_fim'])
        
        if grouped_ena_data is not None and not grouped_ena_data.empty:
            grouped_ena_data['data'] = pd.to_datetime(grouped_ena_data['data'])
        
        # Aplicar filtro de período
        start_date, end_date = self._get_filter_range(grouped_data_pmo)
        
        # Filtrar grouped_data
        grouped_data = grouped_data[
            (grouped_data['data'] >= start_date) & (grouped_data['data'] <= end_date)
        ].copy()
        
        # Filtrar grouped_data_pmo
        if grouped_data_pmo is not None and not grouped_data_pmo.empty:
            grouped_data_pmo = grouped_data_pmo[
                (grouped_data_pmo['data_inicio'] <= end_date) & 
                (grouped_data_pmo['data_fim'] >= start_date)
            ].copy()
        
        # Filtrar grouped_ena_data
        if grouped_ena_data is not None and not grouped_ena_data.empty:
            grouped_ena_data = grouped_ena_data[
                (grouped_ena_data['data'] >= start_date) & (grouped_ena_data['data'] <= end_date)
            ].copy()
        
        # Obter a última data_projecao
        last_data_proj = grouped_data['data_projecao'].max()
        
        # Criar o gráfico
        fig, ax = plt.subplots(figsize=tuple(self.config.get('visualization.figure_size')))
        
        # Cores
        line_color = self.config.get('visualization.colors.line_color')
        last_line_color = self.config.get('visualization.colors.last_line_color')
        pmo_color = self.config.get('visualization.colors.pmo_color')
        real_color = 'orange'  # Cor para dados reais (como no notebook original)
        
        # Plotar as linhas do grouped_data (projeções diárias)
        for data_proj in grouped_data['data_projecao'].unique():
            subset = grouped_data[grouped_data['data_projecao'] == data_proj]
            if data_proj == last_data_proj:
                ax.plot(subset['data'], subset['percentual_MLT'], 
                       color=last_line_color, linewidth=2, 
                       label='Última Projeção Diária')
            else:
                ax.plot(subset['data'], subset['percentual_MLT'], 
                       color=line_color, alpha=0.7)
        
        # Plotar os dados do PMO como linhas retas (se disponível)
        if grouped_data_pmo is not None and not grouped_data_pmo.empty:
            for i, row in grouped_data_pmo.iterrows():
                ax.hlines(row['percentual_MLT'], row['data_inicio'], row['data_fim'], 
                         colors=pmo_color, linewidth=2, 
                         label="Previsão Semanal" if i == 0 else "")
        
        # Plotar os dados reais (se disponível)
        if grouped_ena_data is not None and not grouped_ena_data.empty:
            ax.plot(
                grouped_ena_data['data'],
                grouped_ena_data['percentual_MLT'],
                color=real_color,
                linewidth=2,
                label='Realizado'
            )
        
        # Configurar o gráfico
        ax.set_xlabel('Data')
        ax.set_ylabel('Percentual MLT')
        ax.set_title('Projeções de ENA como Percentual MLT')
        
        # Definir a escala do eixo Y
        y_limits = self.config.get('visualization.y_limits')
        ax.set_ylim(y_limits[0], y_limits[1])
        
        # Adicionar a legenda
        ax.legend()
        
        # Ajustar layout
        plt.tight_layout()
        
        # Salvar o gráfico se especificado
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Gráfico salvo em: {save_path}")
        
        return fig
    
    def create_comparison_chart(self, grouped_ena_data: pd.DataFrame,
                               grouped_data: pd.DataFrame,
                               grouped_data_pmo: pd.DataFrame = None,
                               save_path: str = None) -> plt.Figure:
        """
        Cria gráfico comparativo entre dados reais e projeções
        
        Args:
            grouped_ena_data: DataFrame com dados reais ENA
            grouped_data: DataFrame com projeções diárias
            grouped_data_pmo: DataFrame com dados PMO (opcional)
            save_path: Caminho para salvar o gráfico (opcional)
            
        Returns:
            Figura do matplotlib
        """
        # Garantir que as colunas de data estão no formato correto
        grouped_ena_data['data'] = pd.to_datetime(grouped_ena_data['data'])
        grouped_data['data'] = pd.to_datetime(grouped_data['data'])
        grouped_data['data_projecao'] = pd.to_datetime(grouped_data['data_projecao'])
        
        if grouped_data_pmo is not None and not grouped_data_pmo.empty:
            grouped_data_pmo['data_inicio'] = pd.to_datetime(grouped_data_pmo['data_inicio'])
            grouped_data_pmo['data_fim'] = pd.to_datetime(grouped_data_pmo['data_fim'])
        
        # Aplicar filtro de período
        start_date, end_date = self._get_filter_range(grouped_data_pmo)
        
        # Filtrar grouped_data
        grouped_data = grouped_data[
            (grouped_data['data'] >= start_date) & (grouped_data['data'] <= end_date)
        ].copy()
        
        # Filtrar grouped_data_pmo
        if grouped_data_pmo is not None and not grouped_data_pmo.empty:
            grouped_data_pmo = grouped_data_pmo[
                (grouped_data_pmo['data_inicio'] <= end_date) & 
                (grouped_data_pmo['data_fim'] >= start_date)
            ].copy()
        
        # Filtrar os dados de grouped_ena_data para corresponder ao período filtrado
        filtered_grouped_ena_data = grouped_ena_data[
            (grouped_ena_data['data'] >= start_date) & (grouped_ena_data['data'] <= end_date)
        ]
        
        # Obter a última data_projecao
        last_data_proj = grouped_data['data_projecao'].max()
        
        # Criar o gráfico
        fig, ax = plt.subplots(figsize=tuple(self.config.get('visualization.figure_size')))
        
        # Cores
        real_color = 'orange'  # Cor para dados reais (como no notebook original)
        line_color = self.config.get('visualization.colors.line_color')
        last_line_color = self.config.get('visualization.colors.last_line_color')
        pmo_color = self.config.get('visualization.colors.pmo_color')
        
        # Variável para controlar a adição da legenda "Previsões anteriores"
        label_added = False
        
        # Plotar as linhas do grouped_data (projeções diárias) usando percentual_MLT
        for data_proj in grouped_data['data_projecao'].tail(20).unique():
            subset = grouped_data[grouped_data['data_projecao'] == data_proj]
            if data_proj == last_data_proj:
                ax.plot(
                    subset['data'],
                    subset['percentual_MLT'],
                    color=last_line_color,
                    linewidth=2,
                    label='Última Previsão'
                )
            else:
                if not label_added:
                    ax.plot(
                        subset['data'],
                        subset['percentual_MLT'],
                        color=line_color,
                        label='Previsões Anteriores'
                    )
                    label_added = True
                else:
                    ax.plot(
                        subset['data'],
                        subset['percentual_MLT'],
                        color=line_color
                    )
        
        # Plotar os dados do PMO como linhas retas
        if grouped_data_pmo is not None and not grouped_data_pmo.empty:
            for i, row in grouped_data_pmo.iterrows():
                ax.hlines(
                    row['percentual_MLT'],
                    row['data_inicio'],
                    row['data_fim'],
                    colors=pmo_color,
                    linewidth=2,
                    label="Previsão Semanal" if i == 0 else ""
                )
        
        # Plotar os dados reais
        ax.plot(
            filtered_grouped_ena_data['data'],
            filtered_grouped_ena_data['percentual_MLT'],
            color=real_color,
            linewidth=2,
            label='Realizado'
        )
        
        # Configurar o gráfico
        ax.set_xlabel('Data')
        ax.set_ylabel('Percentual MLT')
        ax.set_title(f'Projeções de ENA como % da MLT - {datetime.now().strftime("%Y-%m-%d")}')
        
        # Definir a escala do eixo Y
        y_limits = self.config.get('visualization.y_limits')
        ax.set_ylim(y_limits[0], y_limits[1])
        
        # Adicionar a legenda
        ax.legend()
        
        # Ajustar layout
        plt.tight_layout()
        
        # Salvar o gráfico se especificado
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Gráfico salvo em: {save_path}")
        
        return fig

    def create_monthly_ranking_chart(self, ena_mensal_data: pd.DataFrame, save_path: str = None, target_month: int = None, target_year: int = None) -> plt.Figure:
        """
        Cria gráfico de ranking mensal da ENA
        
        Args:
            ena_mensal_data: DataFrame com dados ENA mensais
            save_path: Caminho para salvar o gráfico (opcional)
            target_month: Mês específico para o ranking (padrão: mês atual)
            target_year: Ano específico para destacar (padrão: ano atual)
            
        Returns:
            Figura do matplotlib
        """
        if ena_mensal_data.empty:
            self.logger.warning("Dados ENA mensais vazios para criar gráfico de ranking")
            return None
        
        current_date = datetime.now()
        
        # Usar mês e ano especificados ou mês/ano atual
        if target_month is None:
            target_month = current_date.month
        if target_year is None:
            target_year = current_date.year
        
        self.logger.info(f"Criando gráfico de ranking para {target_month}/{target_year}")
        
        # Filtrar dados do mês especificado
        month_data = ena_mensal_data[
            ena_mensal_data['mes'] == target_month
        ].copy()
        
        if month_data.empty:
            self.logger.warning(f"Nenhum dado encontrado para o mês {target_month}")
            return None
        
        # Ordenar por percentual em ordem decrescente
        month_data = month_data.sort_values('ena_bruta_regiao_percentualmlt', ascending=False)
        
        # Encontrar posição do ano especificado
        target_year_position = month_data[
            month_data['ano'] == target_year
        ]
        
        if target_year_position.empty:
            self.logger.warning(f"Nenhum dado encontrado para {target_month}/{target_year}")
            return None
        
        # Encontrar a posição correta no ranking ordenado
        target_position = month_data[
            month_data['ano'] == target_year
        ].index[0]
        
        # Calcular posição real (1-based) no ranking ordenado
        target_position = month_data.index.get_loc(target_position) + 1
        
        total_months = len(month_data)
        
        # Calcular percentil
        percentile = ((total_months - target_position + 1) / total_months) * 100
        
        # Criar o gráfico
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Preparar dados para o gráfico
        years = month_data['ano'].astype(str)
        percentual_mlt = month_data['ena_bruta_regiao_percentualmlt']
        
        # Cores para as barras
        colors = ['lightblue' if year != str(target_year) else 'red' for year in years]
        
        # Criar gráfico de barras
        bars = ax.bar(range(len(years)), percentual_mlt, color=colors, alpha=0.7)
        
        # Destacar a barra do ano especificado
        if str(target_year) in years:
            target_idx = years.tolist().index(str(target_year))
            bars[target_idx].set_color('red')
            bars[target_idx].set_alpha(1.0)
            bars[target_idx].set_edgecolor('darkred')
            bars[target_idx].set_linewidth(2)
        
        # Configurar eixo X
        ax.set_xlabel('Ano')
        ax.set_ylabel('Percentual MLT Consolidado')
        
        # Nome do mês
        month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        month_name = month_names[target_month - 1]
        
        ax.set_title(f'Ranking de ENA - {month_name}\n'
                    f'{target_year} na posição {target_position} de {total_months} ({percentile:.1f}%)')
        
        # Configurar ticks do eixo X
        ax.set_xticks(range(len(years)))
        ax.set_xticklabels(years, rotation=45, ha='right')
        
        # Adicionar grade
        ax.grid(True, alpha=0.3, axis='y')
        
        # Adicionar valores nas barras
        for i, (bar, value) in enumerate(zip(bars, percentual_mlt)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{value:.1f}%', ha='center', va='bottom', fontsize=8)
        
        # Adicionar linha de média
        mean_value = percentual_mlt.mean()
        ax.axhline(y=mean_value, color='orange', linestyle='--', alpha=0.7, 
                  label=f'Média: {mean_value:.1f}%')
        
        # Adicionar legenda
        ax.legend()
        
        # Ajustar layout
        plt.tight_layout()
        
        # Salvar o gráfico se especificado
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"✓ Gráfico de ranking mensal salvo em: {save_path}")
        
        return fig