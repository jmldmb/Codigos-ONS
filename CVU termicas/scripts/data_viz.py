"""
Script para visualização de dados CVU de usinas térmicas
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

class DataVisualizer:
    """Classe para visualização de dados CVU"""
    
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
        self.viz_data_path = self.project_root / self.config['paths']['viz_data']
        self.output_charts_path = self.project_root / self.config['paths']['output_charts']
        self.output_charts_path.mkdir(parents=True, exist_ok=True)
        
        # Configurar estilo
        plt.style.use(self.config['visualization']['style'])
        self.figsize = tuple(self.config['visualization']['default_figsize'])
        self.dpi = self.config['visualization']['dpi']
        self.colors = self.config['visualization']['colors']
        
        logger.info(f"Diretórios configurados:")
        logger.info(f"  Viz data: {self.viz_data_path}")
        logger.info(f"  Output charts: {self.output_charts_path}")
    
    def load_data(self):
        """Carrega dados para visualização"""
        viz_file = self.viz_data_path / "cvu_viz.parquet"
        
        if viz_file.exists():
            df = pd.read_parquet(viz_file)
            logger.info(f"Dados carregados: {len(df)} registros")
            return df
        else:
            logger.error(f"Arquivo de dados não encontrado: {viz_file}")
            return None
    
    def plot_cvu_timeline(self, df):
        """Gráfico de linha temporal do CVU"""
        logger.info("Criando gráfico de timeline do CVU...")
        
        if 'data' not in df.columns or 'cvu' not in df.columns:
            logger.warning("Colunas 'data' ou 'cvu' não encontradas")
            return
        
        # Agrupar por data e calcular média
        timeline_data = df.groupby('data')['cvu'].agg(['mean', 'std']).reset_index()
        
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Plot principal
        ax.plot(timeline_data['data'], timeline_data['mean'], 
                color=self.colors['primary'], linewidth=2, label='CVU Médio')
        
        # Área de desvio padrão
        ax.fill_between(timeline_data['data'], 
                       timeline_data['mean'] - timeline_data['std'],
                       timeline_data['mean'] + timeline_data['std'],
                       alpha=0.3, color=self.colors['primary'], label='±1 Desvio Padrão')
        
        ax.set_title('Evolução Temporal do CVU Médio', fontsize=16, fontweight='bold')
        ax.set_xlabel('Data', fontsize=12)
        ax.set_ylabel('CVU (R$/MWh)', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Rotacionar labels do eixo x
        plt.setp(ax.get_xticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Salvar
        output_file = self.output_charts_path / "cvu_timeline.png"
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico salvo: {output_file}")
    
    def plot_cvu_by_year(self, df):
        """Gráfico de boxplot por ano"""
        logger.info("Criando gráfico de CVU por ano...")
        
        if 'ano' not in df.columns or 'cvu' not in df.columns:
            logger.warning("Colunas 'ano' ou 'cvu' não encontradas")
            return
        
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Boxplot
        sns.boxplot(data=df, x='ano', y='cvu', ax=ax, color=self.colors['primary'])
        
        ax.set_title('Distribuição do CVU por Ano', fontsize=16, fontweight='bold')
        ax.set_xlabel('Ano', fontsize=12)
        ax.set_ylabel('CVU (R$/MWh)', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Salvar
        output_file = self.output_charts_path / "cvu_by_year.png"
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico salvo: {output_file}")
    
    def plot_top_usinas(self, df, top_n=10):
        """Gráfico das usinas com maior CVU médio"""
        logger.info(f"Criando gráfico das top {top_n} usinas...")
        
        if 'usina' not in df.columns or 'cvu' not in df.columns:
            logger.warning("Colunas 'usina' ou 'cvu' não encontradas")
            return
        
        # Calcular CVU médio por usina
        usina_stats = df.groupby('usina')['cvu'].mean().sort_values(ascending=False).head(top_n)
        
        fig, ax = plt.subplots(figsize=(12, 8), dpi=self.dpi)
        
        bars = ax.barh(range(len(usina_stats)), usina_stats.values, 
                      color=self.colors['secondary'])
        
        ax.set_yticks(range(len(usina_stats)))
        ax.set_yticklabels(usina_stats.index)
        ax.set_xlabel('CVU Médio (R$/MWh)', fontsize=12)
        ax.set_title(f'Top {top_n} Usinas por CVU Médio', fontsize=16, fontweight='bold')
        
        # Adicionar valores nas barras
        for i, v in enumerate(usina_stats.values):
            ax.text(v + 1, i, f'{v:.1f}', va='center', fontsize=10)
        
        plt.tight_layout()
        
        # Salvar
        output_file = self.output_charts_path / "top_usinas_cvu.png"
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico salvo: {output_file}")
    
    def plot_monthly_pattern(self, df):
        """Gráfico de padrão mensal"""
        logger.info("Criando gráfico de padrão mensal...")
        
        if 'mes' not in df.columns or 'cvu' not in df.columns:
            logger.warning("Colunas 'mes' ou 'cvu' não encontradas")
            return
        
        # Calcular CVU médio por mês
        monthly_data = df.groupby('mes')['cvu'].agg(['mean', 'std']).reset_index()
        
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        
        x_pos = range(len(months))
        
        # Plot principal
        ax.bar(x_pos, monthly_data['mean'], 
               color=self.colors['tertiary'], alpha=0.7, label='CVU Médio')
        
        # Barras de erro
        ax.errorbar(x_pos, monthly_data['mean'], yerr=monthly_data['std'],
                   fmt='none', color='black', capsize=5, capthick=2)
        
        ax.set_title('Padrão Mensal do CVU', fontsize=16, fontweight='bold')
        ax.set_xlabel('Mês', fontsize=12)
        ax.set_ylabel('CVU (R$/MWh)', fontsize=12)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(months)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Salvar
        output_file = self.output_charts_path / "monthly_pattern.png"
        plt.savefig(output_file, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico salvo: {output_file}")
    
    def create_interactive_dashboard(self, df):
        """Cria dashboard interativo com Plotly"""
        logger.info("Criando dashboard interativo...")
        
        # Dashboard com múltiplos gráficos
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Evolução Temporal', 'Distribuição por Ano', 
                           'Top Usinas', 'Padrão Mensal'),
            specs=[[{"type": "scatter"}, {"type": "box"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Gráfico 1: Timeline
        if 'data' in df.columns and 'cvu' in df.columns:
            timeline_data = df.groupby('data')['cvu'].mean().reset_index()
            fig.add_trace(
                go.Scatter(x=timeline_data['data'], y=timeline_data['cvu'],
                          mode='lines', name='CVU Médio'),
                row=1, col=1
            )
        
        # Gráfico 2: Boxplot por ano
        if 'ano' in df.columns and 'cvu' in df.columns:
            for year in df['ano'].unique():
                year_data = df[df['ano'] == year]['cvu']
                fig.add_trace(
                    go.Box(y=year_data, name=str(year)),
                    row=1, col=2
                )
        
        # Gráfico 3: Top usinas
        if 'usina' in df.columns and 'cvu' in df.columns:
            usina_stats = df.groupby('usina')['cvu'].mean().sort_values(ascending=False).head(10)
            fig.add_trace(
                go.Bar(x=usina_stats.values, y=usina_stats.index, orientation='h'),
                row=2, col=1
            )
        
        # Gráfico 4: Padrão mensal
        if 'mes' in df.columns and 'cvu' in df.columns:
            monthly_data = df.groupby('mes')['cvu'].mean()
            months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                     'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            fig.add_trace(
                go.Bar(x=months, y=monthly_data.values),
                row=2, col=2
            )
        
        fig.update_layout(
            title_text="Dashboard CVU - Usinas Térmicas",
            height=800,
            showlegend=False
        )
        
        # Salvar como HTML
        output_file = self.output_charts_path / "dashboard_interativo.html"
        fig.write_html(output_file)
        
        logger.info(f"Dashboard salvo: {output_file}")
    
    def generate_all_visualizations(self):
        """Gera todas as visualizações"""
        logger.info("Iniciando geração de visualizações...")
        
        df = self.load_data()
        if df is None:
            return False
        
        try:
            # Gráficos estáticos
            self.plot_cvu_timeline(df)
            self.plot_cvu_by_year(df)
            self.plot_top_usinas(df)
            self.plot_monthly_pattern(df)
            
            # Dashboard interativo
            self.create_interactive_dashboard(df)
            
            logger.info("Todas as visualizações foram geradas com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao gerar visualizações: {e}")
            return False

def main():
    """Função principal"""
    visualizer = DataVisualizer()
    success = visualizer.generate_all_visualizations()
    
    if success:
        logger.info("Visualizações geradas com sucesso")
    else:
        logger.error("Falha na geração de visualizações")

if __name__ == "__main__":
    main() 