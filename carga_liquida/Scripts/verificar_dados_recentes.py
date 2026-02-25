"""Verifica se os dados estão atualizados."""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "Data" / "raw"

print("="*80)
print("  VERIFICAÇÃO: Dados Mais Recentes")
print("="*80)

# 1. Geração por usina
print("\n[1/2] Geração por Usina:")
geracao_dir = RAW_DIR / "geracao por usina"
arquivos_ger = sorted(geracao_dir.glob("GERACAO_USINA-2_*.parquet"))

if arquivos_ger:
    print(f"  Primeiro: {arquivos_ger[0].name}")
    print(f"  Último:   {arquivos_ger[-1].name}")
    
    df_ultimo = pd.read_parquet(arquivos_ger[-1])
    df_ultimo['din_instante'] = pd.to_datetime(df_ultimo['din_instante'])
    print(f"  Data máx: {df_ultimo['din_instante'].max()}")
else:
    print("  [!] Nenhum arquivo encontrado")

# 2. Térmica
print("\n[2/2] Geração Térmica:")
termo_dir = RAW_DIR / "termoeletrica"
arquivos_termo = sorted(termo_dir.glob("GERACAO_TERMICA_DESPACHO-2_*.parquet"))

if arquivos_termo:
    print(f"  Primeiro: {arquivos_termo[0].name}")
    print(f"  Último:   {arquivos_termo[-1].name}")
    
    df_ultimo = pd.read_parquet(arquivos_termo[-1])
    df_ultimo['din_instante'] = pd.to_datetime(df_ultimo['din_instante'])
    print(f"  Data máx: {df_ultimo['din_instante'].max()}")
else:
    print("  [!] Nenhum arquivo encontrado")

# 3. Data de hoje
print("\n" + "="*80)
print(f"  Hoje: {datetime.today().strftime('%Y-%m-%d')}")
print("="*80)

# 4. Verificar se precisa atualizar
hoje = datetime.today()
if arquivos_ger:
    ultimo_ger_mes = arquivos_ger[-1].name.split('_')[-1].split('.')[0]  # Extrai MM
    ultimo_ger_ano = arquivos_ger[-1].name.split('_')[-2]  # Extrai YYYY
    print(f"\n  Último arquivo de geração: {ultimo_ger_ano}-{ultimo_ger_mes}")
    print(f"  Mês atual: {hoje.year}-{hoje.month:02d}")
    
    if f"{hoje.year}_{hoje.month:02d}" > f"{ultimo_ger_ano}_{ultimo_ger_mes}":
        print(f"\n  [!] ATUALIZAÇÃO DISPONÍVEL!")
        print(f"      Execute: python carga_liquida.py para baixar dados mais recentes")
    else:
        print(f"\n  [OK] Dados atualizados!")







