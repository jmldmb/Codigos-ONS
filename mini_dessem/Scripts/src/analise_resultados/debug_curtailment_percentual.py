"""
Debug do Cálculo de Curtailment Percentual
==========================================

Gera um Excel com a memória de cálculo detalhada do curtailment
para entender e validar o cálculo do percentual médio.
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


def debug_curtailment_percentual(ano=2025):
    """Gera Excel com memória de cálculo do curtailment percentual."""
    
    print(f"\n{'='*80}")
    print(f"  DEBUG: Curtailment Percentual - {ano}")
    print(f"{'='*80}")
    
    # Carregar dados
    resultados_dir = OUTPUT_DIR
    arquivos = list(resultados_dir.glob('resultados_simulacao_*.parquet'))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {resultados_dir}")
    
    arquivo_path = max(arquivos, key=lambda p: p.stat().st_mtime)
    print(f"\nCarregando: {arquivo_path.name}")
    
    df = pd.read_parquet(arquivo_path)
    print(f"  Registros: {len(df):,}")
    
    # Filtrar por ano
    df_ano = df[df['ano'] == ano].copy()
    print(f"  Registros {ano}: {len(df_ano):,}")
    
    # Verificar colunas necessárias
    print(f"\nColunas disponíveis relacionadas ao curtailment:")
    cols_curtail = [col for col in df_ano.columns if 'curtail' in col.lower()]
    for col in cols_curtail:
        print(f"  - {col}")
    
    print(f"\nColunas disponíveis relacionadas à geração:")
    cols_ger = [col for col in df_ano.columns if 'ger' in col.lower() or 'val_ger' in col.lower()]
    for col in cols_ger:
        print(f"  - {col}")
    
    # Criar colunas de geração pré-curtailment usando as colunas ANTES DO CORTE
    if 'val_gereolica_antes_corte' in df_ano.columns:
        df_ano['geracao_eolica_pre'] = df_ano['val_gereolica_antes_corte']
    else:
        df_ano['geracao_eolica_pre'] = df_ano['val_gereolica']
    
    if 'val_gersolar_cent_antes_corte' in df_ano.columns:
        df_ano['geracao_solar_cent_pre'] = df_ano['val_gersolar_cent_antes_corte']
    elif 'val_gersolar_cent_depois_corte' in df_ano.columns:
        df_ano['geracao_solar_cent_pre'] = df_ano['val_gersolar_cent_depois_corte'] + df_ano['curtailment_solar_cent']
    else:
        df_ano['geracao_solar_cent_pre'] = df_ano['val_gersolar'] * 0.36
    
    if 'val_gersolar_dist_antes_corte' in df_ano.columns:
        df_ano['geracao_solar_dist_pre'] = df_ano['val_gersolar_dist_antes_corte']
    elif 'val_gersolar_dist_depois_corte' in df_ano.columns:
        df_ano['geracao_solar_dist_pre'] = df_ano['val_gersolar_dist_depois_corte'] + df_ano['curtailment_solar_dist']
    else:
        df_ano['geracao_solar_dist_pre'] = df_ano['val_gersolar'] * 0.64
    
    # Curtailment total por hora
    df_ano['curtailment_total'] = (df_ano['curtailment_eolica'] + 
                                     df_ano['curtailment_solar_cent'] + 
                                     df_ano['curtailment_solar_dist'])
    
    # Geração total pré-curtailment por hora - SEM DISTRIBUÍDA (não é despachável)
    df_ano['geracao_total_pre'] = (df_ano['geracao_eolica_pre'] + 
                                     df_ano['geracao_solar_cent_pre'])
    
    print(f"\n  [ATENÇÃO] Geração DISTRIBUÍDA NÃO entra no denominador (não é despachável pelo operador)")
    
    # Percentual por hora
    df_ano['pct_curtailment_hora'] = np.where(
        df_ano['geracao_total_pre'] > 0,
        (df_ano['curtailment_total'] / df_ano['geracao_total_pre']) * 100,
        0
    )
    
    # ========================================
    # AGREGAÇÃO MENSAL
    # ========================================
    
    print(f"\n{'='*80}")
    print(f"  CALCULANDO POR MÊS")
    print(f"{'='*80}")
    
    # Agrupar por mês
    mensal = df_ano.groupby('mes').agg({
        'curtailment_eolica': 'sum',
        'curtailment_solar_cent': 'sum',
        'curtailment_solar_dist': 'sum',
        'curtailment_total': 'sum',
        'geracao_eolica_pre': 'sum',
        'geracao_solar_cent_pre': 'sum',
        'geracao_solar_dist_pre': 'sum',
        'geracao_total_pre': 'sum',
        'pct_curtailment_hora': 'mean'  # Média dos percentuais horários
    }).reset_index()
    
    # Renomear colunas para clareza
    mensal.columns = [
        'Mês',
        'Curtailment Eólica (MWh)',
        'Curtailment Solar Cent (MWh)',
        'Curtailment Solar Dist (MWh)',
        'Curtailment TOTAL (MWh)',
        'Geração Eólica Pré-Curtail (MWh)',
        'Geração Solar Cent Pré-Curtail (MWh)',
        'Geração Solar Dist Pré-Curtail (MWh)',
        'Geração TOTAL Pré-Curtail (MWh)',
        'Média % Horário'
    ]
    
    # Calcular percentual mensal
    mensal['% Curtailment Mensal'] = (
        mensal['Curtailment TOTAL (MWh)'] / mensal['Geração TOTAL Pré-Curtail (MWh)']
    ) * 100
    
    # Converter para MWmédio (dividir por número de horas no mês)
    horas_por_mes = df_ano.groupby('mes').size().reset_index(name='Horas')
    mensal = mensal.merge(horas_por_mes, left_on='Mês', right_on='mes', how='left')
    mensal = mensal.drop('mes', axis=1)
    
    mensal['Curtailment MWmédio'] = mensal['Curtailment TOTAL (MWh)'] / mensal['Horas']
    mensal['Geração MWmédio'] = mensal['Geração TOTAL Pré-Curtail (MWh)'] / mensal['Horas']
    
    # ========================================
    # CÁLCULOS DE MÉDIAS
    # ========================================
    
    # Método 1: Média aritmética dos percentuais mensais
    metodo1 = mensal['% Curtailment Mensal'].mean()
    
    # Método 2: Média de curtailment / Média de geração
    metodo2_numerador = mensal['Curtailment TOTAL (MWh)'].mean()
    metodo2_denominador = mensal['Geração TOTAL Pré-Curtail (MWh)'].mean()
    metodo2 = (metodo2_numerador / metodo2_denominador) * 100
    
    # Método 3: Total anual / Total geração anual
    metodo3_numerador = mensal['Curtailment TOTAL (MWh)'].sum()
    metodo3_denominador = mensal['Geração TOTAL Pré-Curtail (MWh)'].sum()
    metodo3 = (metodo3_numerador / metodo3_denominador) * 100
    
    # Método 4: Média dos percentuais horários (CORRETO para o gráfico!)
    metodo4 = df_ano['pct_curtailment_hora'].mean()
    
    # Método 4b: Média dos % horários por mês (mesmo que método 4, mas agregado por mês primeiro)
    metodo4b_por_mes = df_ano.groupby('mes')['pct_curtailment_hora'].mean()
    metodo4b = metodo4b_por_mes.mean()
    
    # Método 5: Considerando APENAS horas COM curtailment
    df_com_curtail = df_ano[df_ano['curtailment_total'] > 0]
    if len(df_com_curtail) > 0:
        metodo5_numerador = df_com_curtail['curtailment_total'].sum()
        metodo5_denominador = df_com_curtail['geracao_total_pre'].sum()
        metodo5 = (metodo5_numerador / metodo5_denominador) * 100 if metodo5_denominador > 0 else 0
        horas_com_curtail = len(df_com_curtail)
        pct_horas_com_curtail = (horas_com_curtail / len(df_ano)) * 100
    else:
        metodo5 = 0
        horas_com_curtail = 0
        pct_horas_com_curtail = 0
    
    # Criar linha de resumo
    resumo = pd.DataFrame({
        'Mês': ['MÉDIA', '', 'TOTAL', '', 'Info Adicional:', f'Horas com curtail',
                '', 'Métodos de Cálculo:', 
                'Método 1', 'Método 2', 'Método 3', 'Método 4', 'Método 5'],
        'Curtailment TOTAL (MWh)': [
            mensal['Curtailment TOTAL (MWh)'].mean(),
            np.nan,
            mensal['Curtailment TOTAL (MWh)'].sum(),
            np.nan,
            np.nan,
            horas_com_curtail,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            metodo5_numerador
        ],
        'Geração TOTAL Pré-Curtail (MWh)': [
            mensal['Geração TOTAL Pré-Curtail (MWh)'].mean(),
            np.nan,
            mensal['Geração TOTAL Pré-Curtail (MWh)'].sum(),
            np.nan,
            np.nan,
            pct_horas_com_curtail,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            metodo5_denominador
        ],
        '% Curtailment Mensal': [
            metodo2,  # (média curtail / média geração) * 100
            np.nan,
            metodo3,  # (total curtail / total geração) * 100
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            np.nan,
            metodo1,  # Média dos % mensais
            metodo2,  # (média curtail / média geração)
            metodo3,  # (total curtail / total geração)
            metodo4,  # Média dos % horários
            metodo5   # Apenas horas com curtailment
        ],
        'Descrição': [
            'Média dos valores mensais',
            '',
            'Soma de todos os meses',
            '',
            '',
            f'{horas_com_curtail} de {len(df_ano)} horas ({pct_horas_com_curtail:.1f}%)',
            '',
            '',
            'Média aritmética dos % mensais',
            '(Média Curtail MWh / Média Geração MWh) * 100',
            '(Total Curtail MWh / Total Geração MWh) * 100 [% REAL]',
            'Média dos % calculados por hora (todas)',
            'Apenas horas COM curtailment'
        ]
    })
    
    # Imprimir no console
    print(f"\n{'='*80}")
    print(f"  RESUMO DOS MÉTODOS")
    print(f"{'='*80}\n")
    print(f"Método 1 - Média aritmética dos % mensais:        {metodo1:.2f}%")
    print(f"Método 2 - (Média Curtail / Média Geração) * 100: {metodo2:.2f}%")
    print(f"Método 3 - (Total Curtail / Total Geração) * 100: {metodo3:.2f}% [% REAL ANUAL]")
    print(f"Método 4 - Média dos % horários:                  {metodo4:.2f}% [USADO NO GRÁFICO!]")
    print(f"Método 4b- Média dos % horários por mês:          {metodo4b:.2f}%")
    print(f"Método 5 - Apenas horas COM curtailment:          {metodo5:.2f}%")
    print(f"\n{'='*80}")
    print(f"  Horas com curtailment: {horas_com_curtail:,} de {len(df_ano):,} ({pct_horas_com_curtail:.1f}%)")
    print(f"  O Método 4 é CORRETO: média dos % hora a hora")
    print(f"  O Método 3 é o % real anual (agregado)")
    print(f"{'='*80}\n")
    
    # Salvar Excel
    curtailment_dir = ANALISES_DIR / 'curtailment'
    curtailment_dir.mkdir(parents=True, exist_ok=True)
    
    # Tentar salvar, se arquivo estiver aberto, usar nome diferente
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = curtailment_dir / f'debug_curtailment_{ano}_{timestamp}.xlsx'
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Aba 1: Dados mensais
        mensal_export = mensal.copy()
        mensal_export = pd.concat([mensal_export, resumo], ignore_index=True)
        mensal_export.to_excel(writer, sheet_name='Mensal', index=False)
        
        # Aba 2: Amostra dos dados horários (primeiros 1000)
        df_hora_sample = df_ano[['ano', 'mes', 'dia', 'hora', 'simulacao',
                                  'curtailment_eolica', 'curtailment_solar_cent', 'curtailment_solar_dist',
                                  'curtailment_total', 'geracao_eolica_pre', 'geracao_solar_cent_pre',
                                  'geracao_solar_dist_pre', 'geracao_total_pre', 'pct_curtailment_hora']].head(1000)
        df_hora_sample.to_excel(writer, sheet_name='Amostra Horária', index=False)
        
        # Aba 3: Explicação dos métodos
        explicacao = pd.DataFrame({
            'Método': ['Método 1', 'Método 2', 'Método 3', 'Método 4', 'Método 5'],
            'Descrição': [
                'Média aritmética simples dos percentuais mensais',
                'Média do curtailment absoluto dividido pela média da geração (usado no gráfico)',
                'Total anual de curtailment dividido pelo total anual de geração (% REAL)',
                'Média dos percentuais calculados hora a hora (todas as horas)',
                'Curtailment apenas nas horas onde houve curtailment'
            ],
            'Fórmula': [
                'MÉDIA(% mês 1, % mês 2, ..., % mês 12)',
                '(MÉDIA(Curtail_jan, ..., Curtail_dez) / MÉDIA(Ger_jan, ..., Ger_dez)) * 100',
                '(SOMA(Curtail_jan, ..., Curtail_dez) / SOMA(Ger_jan, ..., Ger_dez)) * 100',
                'MÉDIA(% hora1, % hora2, ..., % hora_n)',
                '(SOMA(Curtail apenas horas>0) / SOMA(Ger apenas horas>0)) * 100'
            ],
            'Valor': [f'{metodo1:.2f}%', f'{metodo2:.2f}%', f'{metodo3:.2f}%', f'{metodo4:.2f}%', f'{metodo5:.2f}%']
        })
        explicacao.to_excel(writer, sheet_name='Explicação', index=False)
    
    print(f"Excel salvo: {output_path}\n")
    
    return output_path


if __name__ == '__main__':
    debug_curtailment_percentual(2025)

