"""
Exemplo de uso do projeto CVU Termicas
Demonstra como usar as diferentes funcionalidades do projeto
"""

import sys
from pathlib import Path

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

def exemplo_download_dados():
    """Exemplo de como baixar dados"""
    print("=" * 50)
    print("EXEMPLO: DOWNLOAD DE DADOS")
    print("=" * 50)
    
    # Inicializar captura de dados
    ingest = DataIngest()
    
    # Baixar dados históricos (2020-2024)
    print("Baixando dados históricos...")
    ingest.download_historical_data()
    
    # Baixar dados do ano atual (2025)
    print("Baixando dados do ano atual...")
    ingest.download_current_year()
    
    # Verificar downloads
    print("Verificando downloads...")
    ingest.verify_downloads()
    
    # Mostrar resumo
    summary = ingest.get_data_summary()
    print("\nResumo dos dados baixados:")
    for year, info in summary.items():
        print(f"  {year}: {info['registros']} registros, {info['tamanho_arquivo']:.2f} MB")

def exemplo_processamento():
    """Exemplo de como processar dados"""
    print("\n" + "=" * 50)
    print("EXEMPLO: PROCESSAMENTO DE DADOS")
    print("=" * 50)
    
    # Inicializar processador
    processor = DataProcessor()
    
    # Executar pipeline completo
    print("Executando pipeline de processamento...")
    success = processor.process_all()
    
    if success:
        print("✅ Processamento concluído com sucesso!")
    else:
        print("❌ Falha no processamento")

def exemplo_visualizacao():
    """Exemplo de como gerar visualizações"""
    print("\n" + "=" * 50)
    print("EXEMPLO: GERAÇÃO DE VISUALIZAÇÕES")
    print("=" * 50)
    
    # Inicializar visualizador
    visualizer = DataVisualizer()
    
    # Gerar todas as visualizações
    print("Gerando visualizações...")
    success = visualizer.generate_all_visualizations()
    
    if success:
        print("✅ Visualizações geradas com sucesso!")
        print("Verifique a pasta 'output/charts' para ver os gráficos")
    else:
        print("❌ Falha na geração de visualizações")

def exemplo_relatorio():
    """Exemplo de como gerar relatório"""
    print("\n" + "=" * 50)
    print("EXEMPLO: GERAÇÃO DE RELATÓRIO")
    print("=" * 50)
    
    # Inicializar gerador de relatório
    generator = ReportGenerator()
    
    # Gerar relatório
    print("Gerando relatório...")
    success = generator.generate_report()
    
    if success:
        print("✅ Relatório gerado com sucesso!")
        print("Verifique a pasta 'output/reports' para ver o relatório HTML")
    else:
        print("❌ Falha na geração do relatório")

def exemplo_pipeline_completo():
    """Exemplo de pipeline completo"""
    print("\n" + "=" * 50)
    print("EXEMPLO: PIPELINE COMPLETO")
    print("=" * 50)
    
    # Importar pipeline principal
    from main import CVUTermicasPipeline
    
    # Inicializar pipeline
    pipeline = CVUTermicasPipeline()
    
    # Executar pipeline completo
    print("Executando pipeline completo...")
    success = pipeline.run_full_pipeline()
    
    if success:
        print("✅ Pipeline completo executado com sucesso!")
    else:
        print("❌ Falha na execução do pipeline")

def main():
    """Função principal com exemplos"""
    print("EXEMPLOS DE USO - CVU TERMICAS")
    print("=" * 60)
    
    # Exemplo 1: Download de dados
    exemplo_download_dados()
    
    # Exemplo 2: Processamento
    exemplo_processamento()
    
    # Exemplo 3: Visualização
    exemplo_visualizacao()
    
    # Exemplo 4: Relatório
    exemplo_relatorio()
    
    # Exemplo 5: Pipeline completo
    exemplo_pipeline_completo()
    
    print("\n" + "=" * 60)
    print("EXEMPLOS CONCLUÍDOS!")
    print("=" * 60)
    print("\nPara executar apenas uma parte específica:")
    print("- Download: python scripts/data_ingest.py")
    print("- Processamento: python scripts/data_process.py")
    print("- Visualização: python scripts/data_viz.py")
    print("- Relatório: python scripts/report_gen.py")
    print("- Pipeline completo: python main.py")

if __name__ == "__main__":
    main() 