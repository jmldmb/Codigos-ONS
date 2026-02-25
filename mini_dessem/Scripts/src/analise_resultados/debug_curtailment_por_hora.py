"""
Debug - Curtailment por Hora do Dia
====================================

Verifica se há curtailment à noite e mostra diferenças entre fontes.
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


def debug_curtailment_por_hora(ano=2025):
    """Analisa curtailment por hora do dia."""
    
    print(f"\n{'='*80}")
    print(f"  DEBUG: Curtailment por Hora - {ano}")
    print(f"{'='*80}")
    
    # Carregar dados
    resultados_dir = OUTPUT_DIR
    arquivos = list(resultados_dir.glob('resultados_simulacao_*.parquet'))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {resultados_dir}")
    
    arquivo_path = max(arquivos, key=lambda p: p.stat().st_mtime)
    print(f"\nCarregando: {arquivo_path.name}")
    
    df = pd.read_parquet(arquivo_path)
    
    # Filtrar por ano
    df_ano = df[df['ano'] == ano].copy()
    print(f"  Registros {ano}: {len(df_ano):,}")
    
    # Geração pré-curtailment
    if 'val_gereolica_antes_corte' in df_ano.columns:
        df_ano['ger_eolica_pre'] = df_ano['val_gereolica_antes_corte']
    else:
        df_ano['ger_eolica_pre'] = df_ano['val_gereolica']
    
    if 'val_gersolar_cent_antes_corte' in df_ano.columns:
        df_ano['ger_solar_cent_pre'] = df_ano['val_gersolar_cent_antes_corte']
    else:
        df_ano['ger_solar_cent_pre'] = df_ano['val_gersolar'] * 0.36
    
    # Verificar curtailment à noite
    print(f"\n{'='*80}")
    print(f"  CURTAILMENT À NOITE (horas 0-5 e 20-23)")
    print(f"{'='*80}\n")
    
    horas_noite = [0, 1, 2, 3, 4, 5, 20, 21, 22, 23]
    df_noite = df_ano[df_ano['hora'].isin(horas_noite)]
    
    curtail_noite = df_noite[df_noite['curtailment'] > 0]
    print(f"Ocorrências de curtailment à noite: {len(curtail_noite):,} de {len(df_noite):,}")
    
    if len(curtail_noite) > 0:
        print(f"\nCurtailment noturno:")
        print(f"  Eólica:    {curtail_noite['curtailment_eolica'].sum():>12,.0f} MWh")
        print(f"  Solar Cent:{curtail_noite['curtailment_solar_cent'].sum():>12,.0f} MWh")
        print(f"  Solar Dist:{curtail_noite['curtailment_solar_dist'].sum():>12,.0f} MWh")
        
        print(f"\nGeração Solar durante curtailment noturno:")
        print(f"  Geração Solar Cent média: {curtail_noite['ger_solar_cent_pre'].mean():.2f} MW")
        print(f"  Geração Solar Cent max:   {curtail_noite['ger_solar_cent_pre'].max():.2f} MW")
    
    # Análise por hora
    print(f"\n{'='*80}")
    print(f"  ANÁLISE POR HORA DO DIA")
    print(f"{'='*80}\n")
    
    # Calcular % por hora
    df_ano['pct_eolica'] = np.where(
        df_ano['ger_eolica_pre'] > 0,
        (df_ano['curtailment_eolica'] / df_ano['ger_eolica_pre']) * 100,
        0
    )
    
    df_ano['pct_solar_cent'] = np.where(
        df_ano['ger_solar_cent_pre'] > 0,
        (df_ano['curtailment_solar_cent'] / df_ano['ger_solar_cent_pre']) * 100,
        0
    )
    
    # Agrupar por hora
    por_hora = df_ano.groupby('hora').agg({
        'curtailment_eolica': 'sum',
        'curtailment_solar_cent': 'sum',
        'ger_eolica_pre': 'sum',
        'ger_solar_cent_pre': 'sum',
        'pct_eolica': 'mean',
        'pct_solar_cent': 'mean'
    })
    
    # Calcular % total por hora
    por_hora['pct_eolica_total'] = np.where(
        por_hora['ger_eolica_pre'] > 0,
        (por_hora['curtailment_eolica'] / por_hora['ger_eolica_pre']) * 100,
        0
    )
    
    por_hora['pct_solar_cent_total'] = np.where(
        por_hora['ger_solar_cent_pre'] > 0,
        (por_hora['curtailment_solar_cent'] / por_hora['ger_solar_cent_pre']) * 100,
        0
    )
    
    print("Hora | Curtail Eól | Curtail Sol | Ger Eól | Ger Sol | % Eól (média) | % Sol (média) | % Eól (total) | % Sol (total)")
    print("-" * 130)
    
    for hora in range(24):
        if hora in por_hora.index:
            row = por_hora.loc[hora]
            print(f"{hora:4d} | {row['curtailment_eolica']:>11,.0f} | {row['curtailment_solar_cent']:>11,.0f} | "
                  f"{row['ger_eolica_pre']:>7,.0f} | {row['ger_solar_cent_pre']:>7,.0f} | "
                  f"{row['pct_eolica']:>13.2f}% | {row['pct_solar_cent']:>13.2f}% | "
                  f"{row['pct_eolica_total']:>13.2f}% | {row['pct_solar_cent_total']:>13.2f}%")
    
    print(f"\n{'='*80}")
    print(f"  MÉDIA GERAL")
    print(f"{'='*80}\n")
    print(f"% Eólica (média dos % horários):      {df_ano['pct_eolica'].mean():.4f}%")
    print(f"% Solar Cent (média dos % horários):  {df_ano['pct_solar_cent'].mean():.4f}%")
    
    # Método CORRETO: Agregar primeiro
    print(f"\n{'='*80}")
    print(f"  MÉTODO CORRETO (Agregar por mês primeiro)")
    print(f"{'='*80}\n")
    
    mensal_proprio = df_ano.groupby('mes').agg({
        'curtailment_eolica': 'sum',
        'curtailment_solar_cent': 'sum',
        'ger_eolica_pre': 'sum',
        'ger_solar_cent_pre': 'sum'
    })
    
    mensal_proprio['pct_eolica'] = (mensal_proprio['curtailment_eolica'] / mensal_proprio['ger_eolica_pre']) * 100
    mensal_proprio['pct_solar_cent'] = (mensal_proprio['curtailment_solar_cent'] / mensal_proprio['ger_solar_cent_pre']) * 100
    
    print(f"% Eólica (agregado mensal):      {mensal_proprio['pct_eolica'].mean():.4f}%")
    print(f"% Solar Cent (agregado mensal):  {mensal_proprio['pct_solar_cent'].mean():.4f}%")
    
    print(f"\nPor mês:")
    for mes in range(1, 13):
        if mes in mensal_proprio.index:
            eol = mensal_proprio.loc[mes, 'pct_eolica']
            sol = mensal_proprio.loc[mes, 'pct_solar_cent']
            print(f"  Mês {mes:2d}: Eólica {eol:6.2f}% | Solar Cent {sol:6.2f}% | Diferença: {eol-sol:+6.2f}pp")
    
    # Salvar Excel
    curtailment_dir = ANALISES_DIR / 'curtailment'
    curtailment_dir.mkdir(parents=True, exist_ok=True)
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = curtailment_dir / f'debug_por_hora_{ano}_{timestamp}.xlsx'
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        por_hora.to_excel(writer, sheet_name='Por Hora')
        mensal_proprio.to_excel(writer, sheet_name='Mensal Próprio')
        
        # Amostra de horas noturnas com curtailment
        if len(curtail_noite) > 0:
            curtail_noite[['ano', 'mes', 'dia', 'hora', 'curtailment_eolica', 
                          'curtailment_solar_cent', 'ger_eolica_pre', 'ger_solar_cent_pre']].head(100).to_excel(
                writer, sheet_name='Amostra Noite', index=False)
    
    print(f"\nExcel salvo: {output_path}\n")


if __name__ == '__main__':
    debug_curtailment_por_hora(2025)

