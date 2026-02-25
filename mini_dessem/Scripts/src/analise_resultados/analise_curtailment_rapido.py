"""
Análise Rápida de Curtailment - Mini DESSEM
============================================

Script para rodar APENAS a análise de curtailment (inclui scatter plots).
Útil para regenerar os gráficos de curtailment sem rodar todas as outras análises.

Uso:
    python analise_curtailment_rapido.py
    python analise_curtailment_rapido.py --arquivo resultados_simulacao_YYYYMMDD_HHMMSS.parquet
"""

import sys
from pathlib import Path

# Adicionar src ao path
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

from analise_simulacoes import (
    carregar_resultados,
    analisar_curtailment,
    analisar_scatter_carga_curtailment
)
from mini_dessem.config import OUTPUT_DIR
import argparse


def main():
    parser = argparse.ArgumentParser(description='Análise rápida de curtailment')
    parser.add_argument('--arquivo', type=str, help='Caminho para arquivo de resultados')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("  ANÁLISE RÁPIDA DE CURTAILMENT")
    print("="*80)
    
    # Determinar arquivo
    if args.arquivo:
        arquivo_path = Path(args.arquivo)
    else:
        arquivo_path = None
    
    # Carregar dados
    df = carregar_resultados(arquivo_path)
    
    # Identificar anos únicos
    anos = sorted(df['ano'].unique())
    print(f"\nAnos encontrados: {anos}")
    
    # Criar diretório de análise
    analise_dir = OUTPUT_DIR / 'analises'
    analise_dir.mkdir(parents=True, exist_ok=True)
    
    # Executar análises de curtailment por ano
    for ano in anos:
        print("\n" + "="*80)
        print(f"  CURTAILMENT: {ano}")
        print("="*80)
        
        analisar_curtailment(df, analise_dir, ano)
        analisar_scatter_carga_curtailment(df, analise_dir, ano)
    
    print("\n" + "="*80)
    print(f"  Análise de Curtailment Concluída!")
    print("="*80)
    print(f"\nResultados salvos em: {analise_dir / 'curtailment'}")
    print(f"\nArquivos gerados:")
    print(f"  - {len(anos)} gráficos de análise de curtailment (1 por ano)")
    print(f"  - {len(anos)} scatter plots Carga vs Curtailment (1 por ano)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())





