"""
Validação dos Gráficos de Curtailment
======================================

Valida se os cálculos dos Gráficos 3 e 4 estão corretos.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Adicionar src ao path
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

from mini_dessem.config import OUTPUT_DIR

# Definir diretório de análises
BASE_OUTPUT = OUTPUT_DIR.parent.parent / "output"
ANALISES_DIR = BASE_OUTPUT / "analises"


def validar_graficos(ano=2025):
    """Valida cálculos dos gráficos 3 e 4."""
    
    print(f"\n{'='*80}")
    print(f"  VALIDAÇÃO DOS GRÁFICOS DE CURTAILMENT - {ano}")
    print(f"{'='*80}")
    
    # Carregar dados
    resultados_dir = OUTPUT_DIR
    arquivos = list(resultados_dir.glob('resultados_simulacao_*.parquet'))
    arquivo_path = max(arquivos, key=lambda p: p.stat().st_mtime)
    
    df = pd.read_parquet(arquivo_path)
    df_ano = df[df['ano'] == ano].copy()
    
    # Geração pré-curtailment
    if 'val_gereolica_antes_corte' in df_ano.columns:
        df_ano['ger_eolica_pre'] = df_ano['val_gereolica_antes_corte']
    else:
        df_ano['ger_eolica_pre'] = df_ano['val_gereolica']
    
    if 'val_gersolar_cent_antes_corte' in df_ano.columns:
        df_ano['ger_solar_cent_pre'] = df_ano['val_gersolar_cent_antes_corte']
    else:
        df_ano['ger_solar_cent_pre'] = df_ano['val_gersolar'] * 0.36
    
    if 'val_gersolar_dist_antes_corte' in df_ano.columns:
        df_ano['ger_solar_dist_pre'] = df_ano['val_gersolar_dist_antes_corte']
    else:
        df_ano['ger_solar_dist_pre'] = df_ano['val_gersolar'] * 0.64
    
    # Denominador comum
    df_ano['ger_total_despacho_pre'] = df_ano['ger_eolica_pre'] + df_ano['ger_solar_cent_pre']
    df_ano['curtailment_total'] = df_ano['curtailment_eolica'] + df_ano['curtailment_solar_cent'] + df_ano['curtailment_solar_dist']
    
    # ========================================
    # GRÁFICO 3: Contribuição ao Total
    # ========================================
    
    print(f"\n{'='*80}")
    print(f"  GRÁFICO 3: Contribuição de cada fonte ao Total")
    print(f"{'='*80}\n")
    
    mensal_g3 = df_ano.groupby('mes').agg({
        'curtailment_eolica': 'sum',
        'curtailment_solar_cent': 'sum',
        'curtailment_solar_dist': 'sum',
        'curtailment_total': 'sum',
        'ger_total_despacho_pre': 'sum'
    })
    
    mensal_g3['pct_eolica_contrib'] = (mensal_g3['curtailment_eolica'] / mensal_g3['ger_total_despacho_pre']) * 100
    mensal_g3['pct_solar_cent_contrib'] = (mensal_g3['curtailment_solar_cent'] / mensal_g3['ger_total_despacho_pre']) * 100
    mensal_g3['pct_solar_dist_contrib'] = (mensal_g3['curtailment_solar_dist'] / mensal_g3['ger_total_despacho_pre']) * 100
    mensal_g3['pct_total'] = (mensal_g3['curtailment_total'] / mensal_g3['ger_total_despacho_pre']) * 100
    mensal_g3['soma_contrib'] = mensal_g3['pct_eolica_contrib'] + mensal_g3['pct_solar_cent_contrib'] + mensal_g3['pct_solar_dist_contrib']
    
    print("Mês | % Eólica | % Solar C | % Solar D | Soma | % Total | Match?")
    print("-" * 75)
    for mes in range(1, 13):
        if mes in mensal_g3.index:
            row = mensal_g3.loc[mes]
            match = "OK" if abs(row['soma_contrib'] - row['pct_total']) < 0.01 else "ERRO"
            print(f"{mes:3d} | {row['pct_eolica_contrib']:>8.2f} | {row['pct_solar_cent_contrib']:>9.2f} | "
                  f"{row['pct_solar_dist_contrib']:>9.2f} | {row['soma_contrib']:>4.2f} | {row['pct_total']:>7.2f} | {match}")
    
    print(f"\n  Linha Vermelha (média): {mensal_g3['pct_total'].mean():.2f}%")
    print(f"  Soma das médias:        {mensal_g3['pct_eolica_contrib'].mean() + mensal_g3['pct_solar_cent_contrib'].mean() + mensal_g3['pct_solar_dist_contrib'].mean():.2f}%")
    
    # ========================================
    # GRÁFICO 4: Cada Fonte vs Própria Geração
    # ========================================
    
    print(f"\n{'='*80}")
    print(f"  GRÁFICO 4: Cada fonte vs sua própria geração")
    print(f"{'='*80}\n")
    
    mensal_g4 = df_ano.groupby('mes').agg({
        'curtailment_eolica': 'sum',
        'curtailment_solar_cent': 'sum',
        'curtailment_solar_dist': 'sum',
        'ger_eolica_pre': 'sum',
        'ger_solar_cent_pre': 'sum',
        'ger_solar_dist_pre': 'sum'
    })
    
    mensal_g4['pct_eolica_proprio'] = (mensal_g4['curtailment_eolica'] / mensal_g4['ger_eolica_pre']) * 100
    mensal_g4['pct_solar_cent_proprio'] = (mensal_g4['curtailment_solar_cent'] / mensal_g4['ger_solar_cent_pre']) * 100
    mensal_g4['pct_solar_dist_proprio'] = (mensal_g4['curtailment_solar_dist'] / mensal_g4['ger_solar_dist_pre']) * 100
    
    print("Mês | % Eólica | % Solar C | % Solar D | Dif Eól-Sol")
    print("-" * 65)
    for mes in range(1, 13):
        if mes in mensal_g4.index:
            row = mensal_g4.loc[mes]
            diff = row['pct_eolica_proprio'] - row['pct_solar_cent_proprio']
            print(f"{mes:3d} | {row['pct_eolica_proprio']:>8.2f} | {row['pct_solar_cent_proprio']:>9.2f} | "
                  f"{row['pct_solar_dist_proprio']:>9.2f} | {diff:>11.2f}pp")
    
    print(f"\n  Média Eólica:      {mensal_g4['pct_eolica_proprio'].mean():.2f}%")
    print(f"  Média Solar Cent:  {mensal_g4['pct_solar_cent_proprio'].mean():.2f}%")
    print(f"  Média Solar Dist:  {mensal_g4['pct_solar_dist_proprio'].mean():.2f}%")
    
    # ========================================
    # COMPARAÇÃO
    # ========================================
    
    print(f"\n{'='*80}")
    print(f"  COMPARAÇÃO DOS DOIS GRÁFICOS")
    print(f"{'='*80}\n")
    
    print("GRÁFICO 3 (Contribuição ao Total - empilhado):")
    print(f"  - Denominador: Eólica + Solar Cent (sem distribuída)")
    print(f"  - Eólica contribui:      {mensal_g3['pct_eolica_contrib'].mean():.2f}%")
    print(f"  - Solar Cent contribui:  {mensal_g3['pct_solar_cent_contrib'].mean():.2f}%")
    print(f"  - Soma (deve bater):     {mensal_g3['pct_total'].mean():.2f}%")
    
    print("\nGRÁFICO 4 (Cada fonte vs própria geração - lado a lado):")
    print(f"  - Cada fonte usa seu próprio denominador")
    print(f"  - Eólica cortada:        {mensal_g4['pct_eolica_proprio'].mean():.2f}%")
    print(f"  - Solar Cent cortada:    {mensal_g4['pct_solar_cent_proprio'].mean():.2f}%")
    print(f"  - Solar tem % MAIOR pois gera só de dia (concentração)")
    
    print(f"\n[OK] Graficos estao corretos se:")
    print(f"  1. Grafico 3: Soma empilhada = % Total")
    print(f"  2. Grafico 4: Solar > Eolica (solar mais concentrado)")


if __name__ == '__main__':
    validar_graficos(2025)

