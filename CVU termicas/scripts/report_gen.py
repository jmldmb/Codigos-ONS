"""
Script para geração de relatórios CVU de usinas térmicas
"""

import pandas as pd
import logging
from pathlib import Path
import yaml
from datetime import datetime
from jinja2 import Template
import os

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

class ReportGenerator:
    """Classe para geração de relatórios CVU"""
    
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
        self.processed_data_path = self.project_root / self.config['paths']['processed_data']
        self.output_reports_path = self.project_root / self.config['paths']['output_reports']
        self.output_charts_path = self.project_root / self.config['paths']['output_charts']
        self.output_reports_path.mkdir(parents=True, exist_ok=True)
        
        self.report_config = self.config['report']
        
        logger.info(f"Diretórios configurados:")
        logger.info(f"  Processed data: {self.processed_data_path}")
        logger.info(f"  Output reports: {self.output_reports_path}")
        logger.info(f"  Output charts: {self.output_charts_path}")
    
    def load_summary_data(self):
        """Carrega dados de resumo"""
        summaries = {}
        
        # Carregar resumos
        summary_files = {
            'yearly': 'summary_yearly.parquet',
            'usina': 'summary_usina.parquet',
            'monthly': 'summary_monthly.parquet'
        }
        
        for name, filename in summary_files.items():
            filepath = self.processed_data_path / filename
            if filepath.exists():
                summaries[name] = pd.read_parquet(filepath)
                logger.info(f"Carregado resumo {name}: {len(summaries[name])} registros")
            else:
                logger.warning(f"Arquivo de resumo não encontrado: {filename}")
        
        return summaries
    
    def generate_summary_stats(self, summaries):
        """Gera estatísticas resumidas"""
        stats = {}
        
        if 'yearly' in summaries:
            yearly = summaries['yearly']
            stats['total_years'] = len(yearly)
            stats['avg_cvu'] = yearly['cvu_medio'].mean()
            stats['max_cvu'] = yearly['cvu_max'].max()
            stats['min_cvu'] = yearly['cvu_min'].min()
            stats['total_records'] = yearly['registros'].sum()
        
        if 'usina' in summaries:
            usina = summaries['usina']
            stats['total_usinas'] = len(usina)
            stats['top_usina'] = usina.loc[usina['cvu_medio'].idxmax(), 'usina']
            stats['top_cvu'] = usina['cvu_medio'].max()
        
        if 'monthly' in summaries:
            monthly = summaries['monthly']
            stats['avg_monthly_cvu'] = monthly['cvu_medio'].mean()
            stats['highest_month'] = monthly.loc[monthly['cvu_medio'].idxmax(), 'mes']
            stats['lowest_month'] = monthly.loc[monthly['cvu_medio'].idxmin(), 'mes']
        
        return stats
    
    def create_html_template(self):
        """Cria template HTML para o relatório"""
        template_str = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório CVU - Usinas Térmicas</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #1f77b4;
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            color: #666;
            margin: 10px 0 0 0;
            font-size: 1.1em;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #333;
            border-left: 4px solid #1f77b4;
            padding-left: 15px;
            margin-bottom: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #1f77b4, #2ca02c);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            font-size: 1.2em;
        }
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-card .label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .chart-section {
            margin: 30px 0;
        }
        .chart-container {
            text-align: center;
            margin: 20px 0;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .table-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #1f77b4;
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #e6f3ff;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Relatório CVU - Usinas Térmicas</h1>
            <p>Análise de Custos Variáveis Unitários</p>
            <p><strong>Data de Geração:</strong> {{ generation_date }}</p>
        </div>

        <div class="section">
            <h2>Resumo Executivo</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Período Analisado</h3>
                    <div class="value">{{ stats.total_years }}</div>
                    <div class="label">Anos</div>
                </div>
                <div class="stat-card">
                    <h3>Total de Registros</h3>
                    <div class="value">{{ "{:,.0f}".format(stats.total_records) }}</div>
                    <div class="label">Registros</div>
                </div>
                <div class="stat-card">
                    <h3>CVU Médio</h3>
                    <div class="value">R$ {{ "{:.2f}".format(stats.avg_cvu) }}</div>
                    <div class="label">R$/MWh</div>
                </div>
                <div class="stat-card">
                    <h3>Total de Usinas</h3>
                    <div class="value">{{ stats.total_usinas }}</div>
                    <div class="label">Usinas</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Análise Temporal</h2>
            <div class="chart-container">
                <img src="cvu_timeline.png" alt="Evolução Temporal do CVU">
            </div>
            <div class="chart-container">
                <img src="cvu_by_year.png" alt="Distribuição do CVU por Ano">
            </div>
        </div>

        <div class="section">
            <h2>Análise por Usina</h2>
            <div class="chart-container">
                <img src="top_usinas_cvu.png" alt="Top Usinas por CVU">
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Usina</th>
                            <th>CVU Médio (R$/MWh)</th>
                            <th>CVU Mínimo</th>
                            <th>CVU Máximo</th>
                            <th>Registros</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for _, row in top_usinas.iterrows() %}
                        <tr>
                            <td>{{ row.usina }}</td>
                            <td>{{ "{:.2f}".format(row.cvu_medio) }}</td>
                            <td>{{ "{:.2f}".format(row.cvu_min) }}</td>
                            <td>{{ "{:.2f}".format(row.cvu_max) }}</td>
                            <td>{{ "{:,.0f}".format(row.registros) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <h2>Padrão Mensal</h2>
            <div class="chart-container">
                <img src="monthly_pattern.png" alt="Padrão Mensal do CVU">
            </div>
        </div>

        <div class="footer">
            <p>Relatório gerado automaticamente em {{ generation_date }}</p>
            <p>Fonte: ONS - Operador Nacional do Sistema Elétrico</p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)
    
    def generate_report(self):
        """Gera o relatório completo"""
        logger.info("Iniciando geração do relatório...")
        
        # Carregar dados
        summaries = self.load_summary_data()
        if not summaries:
            logger.error("Nenhum dado de resumo encontrado")
            return False
        
        # Gerar estatísticas
        stats = self.generate_summary_stats(summaries)
        
        # Preparar dados para o template
        template_data = {
            'generation_date': datetime.now().strftime('%d/%m/%Y às %H:%M'),
            'stats': stats,
            'top_usinas': summaries.get('usina', pd.DataFrame()).head(10)
        }
        
        # Criar template
        template = self.create_html_template()
        
        # Renderizar relatório
        html_content = template.render(**template_data)
        
        # Salvar relatório
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        report_file = self.output_reports_path / f"relatorio_cvu_{timestamp}.html"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Relatório gerado: {report_file}")
        
        # Copiar imagens para o diretório de relatórios
        self.copy_charts_to_report()
        
        return True
    
    def copy_charts_to_report(self):
        """Copia gráficos para o diretório de relatórios"""
        chart_files = [
            'cvu_timeline.png',
            'cvu_by_year.png',
            'top_usinas_cvu.png',
            'monthly_pattern.png'
        ]
        
        for chart_file in chart_files:
            src = self.output_charts_path / chart_file
            dst = self.output_reports_path / chart_file
            
            if src.exists():
                import shutil
                shutil.copy2(src, dst)
                logger.info(f"Gráfico copiado: {chart_file}")
            else:
                logger.warning(f"Gráfico não encontrado: {chart_file}")

def main():
    """Função principal"""
    generator = ReportGenerator()
    success = generator.generate_report()
    
    if success:
        logger.info("Relatório gerado com sucesso")
    else:
        logger.error("Falha na geração do relatório")

if __name__ == "__main__":
    main() 