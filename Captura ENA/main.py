#!/usr/bin/env python3
"""
Script principal do projeto Captura ENA
"""
import sys
import argparse
from pathlib import Path

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent / "src"))

from src.orchestrator import ENAOrchestrator
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Processamento de dados ENA do ONS')
    
    parser.add_argument('--download-ena', action='store_true', 
                       help='Baixar dados ENA diários')
    parser.add_argument('--process-pmo', action='store_true', 
                       help='Processar dados PMO')
    parser.add_argument('--create-viz', action='store_true', 
                       help='Criar visualizações')
    parser.add_argument('--save-data', action='store_true', 
                       help='Salvar dados processados')
    parser.add_argument('--full-pipeline', action='store_true', 
                       help='Executar pipeline completo')
    parser.add_argument('--ena-folder', type=str, 
                       help='Caminho para pasta com arquivos ENA PDP')
    parser.add_argument('--year', type=int, 
                       help='Ano para processamento (padrão: ano atual)')
    
    args = parser.parse_args()
    
    # Se nenhuma opção foi especificada, executar pipeline completo
    if not any([args.download_ena, args.process_pmo, args.create_viz, 
                args.save_data, args.full_pipeline]):
        args.full_pipeline = True
    
    try:
        # Inicializar orquestrador
        orchestrator = ENAOrchestrator()
        
        if args.full_pipeline:
            # Executar pipeline completo
            logger.info("Executando pipeline completo")
            results = orchestrator.run_full_pipeline(
                download_ena=True,
                process_pmo=True,
                create_visualizations=True,
                save_data=True
            )
            
            if results['success']:
                logger.info("Pipeline executado com sucesso!")
                
                # Mostrar resumo
                summary = orchestrator.get_summary()
                logger.info("Resumo dos dados processados:")
                logger.info(f"- Registros ENA PDP: {summary['ena_pdp_records']}")
                logger.info(f"- Registros agrupados: {summary['grouped_records']}")
                logger.info(f"- Registros PMO: {summary['pmo_records']}")
                logger.info(f"- Registros ENA diário: {summary['ena_diario_records']}")
                logger.info(f"- Registros ENA mensal: {summary['ena_mensal_records']}")

                
                # Mostrar arquivos salvos
                if results['files_saved']:
                    logger.info("Arquivos salvos:")
                    for file_type, file_path in results['files_saved'].items():
                        logger.info(f"  - {file_type}: {file_path}")
                
                # Mostrar relatórios criados
                if results['reports_created']:
                    logger.info("Relatórios criados:")
                    for report_type, report_path in results['reports_created'].items():
                        logger.info(f"  - {report_type}: {report_path}")
            else:
                logger.error("Erro durante a execução do pipeline")
                for error in results['errors']:
                    logger.error(f"  - {error}")
                sys.exit(1)
        
        else:
            # Executar operações específicas
            if args.download_ena:
                logger.info("Baixando dados ENA diários")
                success = orchestrator.download_ena_data(args.year)
                if success:
                    logger.info("Download concluído com sucesso")
                else:
                    logger.error("Falha no download")
                    sys.exit(1)
            
            if args.process_pmo:
                logger.info("Processando dados PMO")
                pmo_data = orchestrator.process_pmo_data(args.ena_folder)
                if not pmo_data.empty:
                    logger.info(f"PMO processado: {len(pmo_data)} registros")
                else:
                    logger.warning("Nenhum dado PMO processado")
            
            if args.create_viz:
                logger.info("Criando visualizações")
                reports = orchestrator.create_visualizations(save_reports=True)
                if reports:
                    logger.info("Visualizações criadas:")
                    for report_type, report_path in reports.items():
                        logger.info(f"  - {report_type}: {report_path}")
                else:
                    logger.warning("Nenhuma visualização foi criada")
            
            if args.save_data:
                logger.info("Salvando dados processados")
                saved_files = orchestrator.save_processed_data()
                if saved_files:
                    logger.info("Dados salvos:")
                    for file_type, file_path in saved_files.items():
                        logger.info(f"  - {file_type}: {file_path}")
                else:
                    logger.warning("Nenhum dado foi salvo")
    
    except Exception as e:
        logger.error(f"Erro durante a execução: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


