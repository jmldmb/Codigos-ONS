"""
Processamento de Carga Líquida Histórica
=========================================

Este script processa dados históricos detalhados (geração por usina) e calcula
a carga líquida real observada.

Definição (dados históricos):
    Carga Líquida = Hidro Reservatório + Térmica Flexível
    Onde:
    - Hidro Reservatório = geração das usinas classificadas como 'R'
    - Térmica Flexível = val_verifordemdemeritoacimadainflex + val_verifunitcommitment

Output:
    - carga_liquida_historica.parquet (para comparações)
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# Diretórios
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "Data" / "raw"
OUTPUT_DIR = BASE_DIR / "Output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def carregar_geracao_usinas():
    """Carrega dados de geração por usina."""
    print("\n[1/5] Carregando geração por usina...")
    
    geracao_dir = RAW_DIR / "geracao por usina"
    arquivos = sorted(geracao_dir.glob("GERACAO_USINA-2_*.parquet"))
    
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo de geração encontrado em {geracao_dir}")
    
    dfs = []
    for arquivo in arquivos:
        df = pd.read_parquet(arquivo)
        dfs.append(df)
    
    df_geracao = pd.concat(dfs, ignore_index=True)
    print(f"     [OK] {len(arquivos)} arquivos carregados ({len(df_geracao):,} registros)")
    
    return df_geracao

def carregar_cadastro():
    """Carrega cadastro de usinas."""
    print("\n[2/5] Carregando cadastro...")
    
    cadastro_path = RAW_DIR / "cadastros" / "cadastro.xlsx"
    cadastro = pd.read_excel(cadastro_path)
    
    print(f"     [OK] Cadastro carregado ({len(cadastro)} usinas)")
    
    return cadastro

def processar_hidro(df_geracao, cadastro):
    """Processa geração hidrelétrica (FD vs Reservatório)."""
    print("\n[3/5] Processando geração hidrelétrica...")
    
    # Filtrar hidrelétricas
    df_hidro = df_geracao[df_geracao['nom_tipousina'] == 'HIDROELÉTRICA'].copy()
    
    # Merge com cadastro
    df_hidro = df_hidro.merge(cadastro, on='nom_usina', how='left')
    
    # Converter para numérico
    df_hidro['val_geracao'] = pd.to_numeric(df_hidro['val_geracao'], errors='coerce')
    df_hidro['din_instante'] = pd.to_datetime(df_hidro['din_instante'])
    
    # Filtrar período válido
    data_inicio = "2022-01-01"
    data_fim = datetime.today().strftime("%Y-%m-%d")
    df_hidro = df_hidro[(df_hidro['din_instante'] >= data_inicio) & 
                         (df_hidro['din_instante'] <= data_fim)]
    
    # Agrupar por din_instante e Classificação
    df_grouped = df_hidro.groupby(['din_instante', 'Classificação'])['val_geracao'].sum().unstack()
    df_grouped = df_grouped.reset_index()
    
    # Garantir que colunas FD e R existem
    if 'FD' not in df_grouped.columns:
        df_grouped['FD'] = 0
    if 'R' not in df_grouped.columns:
        df_grouped['R'] = 0
    
    print(f"     [OK] Hidro processada: FD={df_grouped['FD'].mean():.0f} MW, R={df_grouped['R'].mean():.0f} MW")
    
    return df_grouped[['din_instante', 'FD', 'R']]

def carregar_termica():
    """Carrega dados de geração térmica."""
    print("\n[4/5] Carregando geração térmica...")
    
    termo_dir = RAW_DIR / "termoeletrica"
    arquivos = sorted(termo_dir.glob("GERACAO_TERMICA_DESPACHO-2_*.parquet"))
    
    if not arquivos:
        print(f"     [!] Nenhum arquivo térmico encontrado")
        return None
    
    dfs = []
    for arquivo in arquivos:
        df = pd.read_parquet(arquivo)
        dfs.append(df)
    
    df_termo = pd.concat(dfs, ignore_index=True)
    
    # Agrupar por din_instante e somar colunas de verificação
    cols_sum = [
        'val_verifordemdemeritoacimadainflex',
        'val_verifunitcommitment'
    ]
    
    # Converter para numérico
    for col in cols_sum:
        if col in df_termo.columns:
            df_termo[col] = pd.to_numeric(df_termo[col], errors='coerce')
    
    df_termo_grouped = df_termo.groupby('din_instante')[cols_sum].sum().reset_index()
    
    # Calcular térmica flexível
    df_termo_grouped['termica_flexivel'] = (
        df_termo_grouped.get('val_verifordemdemeritoacimadainflex', 0) + 
        df_termo_grouped.get('val_verifunitcommitment', 0)
    )
    
    print(f"     [OK] Térmica processada ({len(arquivos)} arquivos)")
    
    return df_termo_grouped[['din_instante', 'termica_flexivel']]

def calcular_carga_liquida_historica():
    """Processa tudo e calcula carga líquida histórica."""
    
    print("="*80)
    print("  PROCESSAMENTO: Carga Líquida Histórica (Dados Detalhados)")
    print("="*80)
    
    # Carregar dados
    df_geracao = carregar_geracao_usinas()
    cadastro = carregar_cadastro()
    df_hidro = processar_hidro(df_geracao, cadastro)
    df_termo = carregar_termica()
    
    # Merge
    print("\n[5/5] Calculando carga líquida...")
    
    df_merged = df_hidro.merge(df_termo, on='din_instante', how='left')
    df_merged['termica_flexivel'] = df_merged['termica_flexivel'].fillna(0)
    
    # CARGA LÍQUIDA = Hidro Reservatório + Térmica Flexível
    df_merged['carga_liquida_historica'] = (
        df_merged['R'] + 
        df_merged['termica_flexivel']
    )
    
    # Adicionar campos úteis
    df_merged['din_instante'] = pd.to_datetime(df_merged['din_instante'])
    df_merged['ano'] = df_merged['din_instante'].dt.year
    df_merged['mes'] = df_merged['din_instante'].dt.month
    df_merged['dia'] = df_merged['din_instante'].dt.day
    df_merged['hora'] = df_merged['din_instante'].dt.hour
    
    # Estatísticas
    print(f"\n     Período: {df_merged['din_instante'].min()} até {df_merged['din_instante'].max()}")
    print(f"     Registros: {len(df_merged):,}")
    print(f"\n     Carga Líquida Histórica:")
    print(f"       Média: {df_merged['carga_liquida_historica'].mean():,.0f} MW")
    print(f"       Min/Max: {df_merged['carga_liquida_historica'].min():,.0f} / {df_merged['carga_liquida_historica'].max():,.0f} MW")
    
    # Salvar em Parquet
    output_path = OUTPUT_DIR / 'carga_liquida_historica.parquet'
    df_merged.to_parquet(output_path, compression='snappy', index=False)
    
    print(f"\n     [OK] Arquivo salvo: {output_path}")
    print(f"     Tamanho: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Salvar também em Excel para referência
    excel_path = OUTPUT_DIR / 'carga_liquida_historica.xlsx'
    df_merged.to_excel(excel_path, index=False)
    print(f"     [OK] Excel salvo: {excel_path}")
    
    print("\n" + "="*80)
    print("  [OK] PROCESSAMENTO CONCLUÍDO!")
    print("="*80)
    
    return df_merged

if __name__ == '__main__':
    df = calcular_carga_liquida_historica()
    
    print(f"\nColunas disponíveis:")
    print(f"  - din_instante, ano, mes, dia, hora")
    print(f"  - FD (Hidro Fio d'Água)")
    print(f"  - R (Hidro Reservatório)")
    print(f"  - termica_flexivel")
    print(f"  - carga_liquida_historica")







