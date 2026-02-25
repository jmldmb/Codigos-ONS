"""
Exemplo de uso do orquestrador de Geração por Usina
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar módulos
sys.path.append(str(Path(__file__).parent))

from utils.config import config
from utils.logger import logger
from scripts.data_downloader import DataDownloader
from scripts.data_processor import DataProcessor
from scripts.visualization import DataVisualizer


def exemplo_download():
    """Exemplo de download de dados"""
    print("=== Exemplo: Download de Dados ===")
    
    downloader = DataDownloader()
    
    # Download de dados renováveis
    print("Baixando dados de geração renovável...")
    downloader.download_geracao_renovavel()
    
    # Download de dados horários
    print("Baixando dados de geração horária...")
    downloader.download_geracao_horaria()
    
    print("Download concluído!")


def exemplo_processamento():
    """Exemplo de processamento de dados"""
    print("=== Exemplo: Processamento de Dados ===")
    
    processor = DataProcessor()
    
    # Processa todos os dados
    print("Processando dados...")
    processed_data = processor.process_all()
    
    print(f"Dados processados: {list(processed_data.keys())}")
    
    # Mostra informações sobre os dados
    if 'geracao_renovavel' in processed_data and not processed_data['geracao_renovavel'].empty:
        df = processed_data['geracao_renovavel']
        print(f"Geração renovável: {len(df)} registros")
        print(f"Empresas: {df['empresa'].nunique()}")
        print(f"Período: {df['mes_ano'].min()} a {df['mes_ano'].max()}")
    
    if 'geracao_termica' in processed_data and not processed_data['geracao_termica'].empty:
        df = processed_data['geracao_termica']
        print(f"Geração térmica: {len(df)} registros")
        print(f"Usinas: {df['nom_usina'].nunique()}")
        print(f"Combustíveis: {df['nom_tipocombustivel'].unique()}")


def exemplo_visualizacao():
    """Exemplo de geração de gráficos"""
    print("=== Exemplo: Geração de Gráficos ===")
    
    processor = DataProcessor()
    visualizer = DataVisualizer()
    
    # Processa dados primeiro
    print("Processando dados para visualização...")
    processed_data = processor.process_all()
    
    # Gera gráficos
    print("Gerando gráficos...")
    visualizer.generate_all_charts(processed_data)
    
    print("Gráficos gerados com sucesso!")
    print(f"Arquivos salvos em: {config.get_path('paths.output.charts')}")


def exemplo_pipeline_completo():
    """Exemplo de pipeline completo"""
    print("=== Exemplo: Pipeline Completo ===")
    
    from orchestrator import GeracaoUsinaOrchestrator
    
    orchestrator = GeracaoUsinaOrchestrator()
    
    print("Executando pipeline completo...")
    orchestrator.run_full_pipeline()
    
    print("Pipeline concluído com sucesso!")


def exemplo_configuracao():
    """Exemplo de uso da configuração"""
    print("=== Exemplo: Configuração ===")
    
    # Acessa configurações
    print(f"Diretório base: {config.get('paths.base_dir')}")
    print(f"Anos de análise: {config.get('processing.anos_analise')}")
    print(f"Meses para baixar: {config.get('download.meses_para_baixar')}")
    
    # Acessa caminhos
    geracao_path = config.get_path('paths.data.geracao')
    print(f"Diretório de geração: {geracao_path}")
    
    # Verifica se diretório existe
    if geracao_path.exists():
        print(f"Diretório existe: {geracao_path}")
        files = list(geracao_path.glob("*.parquet"))
        print(f"Arquivos parquet encontrados: {len(files)}")
    else:
        print(f"Diretório não existe: {geracao_path}")


if __name__ == "__main__":
    print("Exemplos de uso do orquestrador de Geração por Usina")
    print("=" * 50)
    
    # Descomente a função que deseja executar
    
    # exemplo_configuracao()
    # exemplo_download()
    # exemplo_processamento()
    # exemplo_visualizacao()
    exemplo_pipeline_completo()
    
    print("\nPara executar um exemplo, descomente a função desejada no código.")
    print("Ou execute o orquestrador diretamente:")
    print("python orchestrator.py --mode full")
    print("python orchestrator.py --mode download")
    print("python orchestrator.py --mode process")
    print("python orchestrator.py --mode charts")
