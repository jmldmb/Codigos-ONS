#!/usr/bin/env python3
"""
Exemplo de uso do projeto Captura ENA
"""
import sys
from pathlib import Path

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent / "src"))

from src.orchestrator import ENAOrchestrator
from src.utils.logger import get_logger

logger = get_logger(__name__)


def example_basic_usage():
    """Exemplo de uso básico do orquestrador"""
    print("=== Exemplo de Uso Básico ===")
    
    # Inicializar orquestrador
    orchestrator = ENAOrchestrator()
    
    # Configurar diretórios
    orchestrator.setup_directories()
    
    # Download de dados ENA diários
    print("1. Baixando dados ENA diários...")
    download_success = orchestrator.download_ena_data()
    if download_success:
        print("   ✓ Download concluído")
    else:
        print("   ✗ Falha no download")
    
    # Processar arquivos ENA PDP
    print("2. Processando arquivos ENA PDP...")
    ena_pdp_data = orchestrator.process_ena_pdp_files()
    if not ena_pdp_data.empty:
        print(f"   ✓ Processados {len(ena_pdp_data)} registros")
    else:
        print("   ✗ Nenhum dado processado")
    
    # Processar dados PMO
    print("3. Processando dados PMO...")
    pmo_data = orchestrator.process_pmo_data()
    if not pmo_data.empty:
        print(f"   ✓ Processados {len(pmo_data)} registros")
    else:
        print("   ✗ Nenhum dado PMO processado")
    
    # Processar dados ENA diários
    print("4. Processando dados ENA diários...")
    ena_diario_data = orchestrator.process_ena_diario_data()
    if not ena_diario_data.empty:
        print(f"   ✓ Processados {len(ena_diario_data)} registros")
    else:
        print("   ✗ Nenhum dado ENA diário processado")
    
    # Criar visualizações
    print("5. Criando visualizações...")
    reports = orchestrator.create_visualizations(save_reports=True)
    if reports:
        print("   ✓ Visualizações criadas:")
        for report_type, report_path in reports.items():
            print(f"     - {report_type}: {report_path}")
    else:
        print("   ✗ Nenhuma visualização criada")
    
    # Salvar dados processados
    print("6. Salvando dados processados...")
    saved_files = orchestrator.save_processed_data()
    if saved_files:
        print("   ✓ Dados salvos:")
        for file_type, file_path in saved_files.items():
            print(f"     - {file_type}: {file_path}")
    else:
        print("   ✗ Nenhum dado salvo")
    
    # Mostrar resumo
    print("\n=== Resumo ===")
    summary = orchestrator.get_summary()
    print(f"Registros ENA PDP: {summary['ena_pdp_records']}")
    print(f"Registros agrupados: {summary['grouped_records']}")
    print(f"Registros PMO: {summary['pmo_records']}")
    print(f"Registros ENA diário: {summary['ena_diario_records']}")


def example_pipeline_completo():
    """Exemplo de uso do pipeline completo"""
    print("\n=== Pipeline Completo ===")
    
    # Inicializar orquestrador
    orchestrator = ENAOrchestrator()
    
    # Executar pipeline completo
    results = orchestrator.run_full_pipeline(
        download_ena=True,
        process_pmo=True,
        create_visualizations=True,
        save_data=True
    )
    
    if results['success']:
        print("✓ Pipeline executado com sucesso!")
        
        # Mostrar resumo
        summary = orchestrator.get_summary()
        print(f"\nResumo:")
        print(f"- Registros ENA PDP: {summary['ena_pdp_records']}")
        print(f"- Registros agrupados: {summary['grouped_records']}")
        print(f"- Registros PMO: {summary['pmo_records']}")
        print(f"- Registros ENA diário: {summary['ena_diario_records']}")
        
        # Mostrar arquivos salvos
        if results['files_saved']:
            print(f"\nArquivos salvos:")
            for file_type, file_path in results['files_saved'].items():
                print(f"- {file_type}: {file_path}")
        
        # Mostrar relatórios criados
        if results['reports_created']:
            print(f"\nRelatórios criados:")
            for report_type, report_path in results['reports_created'].items():
                print(f"- {report_type}: {report_path}")
    else:
        print("✗ Erro durante a execução do pipeline")
        for error in results['errors']:
            print(f"  - {error}")


def example_operacoes_especificas():
    """Exemplo de operações específicas"""
    print("\n=== Operações Específicas ===")
    
    # Inicializar orquestrador
    orchestrator = ENAOrchestrator()
    
    # Apenas download
    print("1. Apenas download de dados ENA diários:")
    success = orchestrator.download_ena_data()
    print(f"   {'✓' if success else '✗'} Download {'concluído' if success else 'falhou'}")
    
    # Apenas processamento ENA PDP
    print("\n2. Apenas processamento ENA PDP:")
    ena_data = orchestrator.process_ena_pdp_files()
    print(f"   {'✓' if not ena_data.empty else '✗'} Processamento {'concluído' if not ena_data.empty else 'falhou'}")
    
    # Apenas visualizações
    print("\n3. Apenas criação de visualizações:")
    reports = orchestrator.create_visualizations(save_reports=True)
    print(f"   {'✓' if reports else '✗'} Visualizações {'criadas' if reports else 'não criadas'}")


if __name__ == "__main__":
    print("Projeto Captura ENA - Exemplos de Uso")
    print("=" * 50)
    
    try:
        # Exemplo básico
        example_basic_usage()
        
        # Pipeline completo
        example_pipeline_completo()
        
        # Operações específicas
        example_operacoes_especificas()
        
    except Exception as e:
        logger.error(f"Erro durante a execução dos exemplos: {e}")
        print(f"Erro: {e}")


