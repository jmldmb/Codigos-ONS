"""Debug do merge"""
import pandas as pd
from pathlib import Path

MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")

# Simulado (pequena amostra)
sim_path = MINI_DESSEM_DIR / "output" / "resultados" / "resultados_simulacao_20251103_193327.parquet"
df_sim = pd.read_parquet(sim_path)
df_sim = df_sim.head(1000)  # Apenas amostra

print("Colunas simulado:")
print([c for c in df_sim.columns if 'carga' in c.lower()])

# Histórico
hist_path = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
df_hist = pd.read_parquet(hist_path)
df_hist = df_hist.head(100)

print("\nColunas histórico:")
print(list(df_hist.columns))

# Merge
df_sim['din_instante'] = pd.to_datetime(
    df_sim['ano'].astype(str) + '-' + 
    df_sim['mes'].astype(str).str.zfill(2) + '-' + 
    df_sim['dia'].astype(str).str.zfill(2) + ' ' + 
    df_sim['hora'].astype(str).str.zfill(2) + ':00:00'
)

df_merged = pd.merge(df_hist, df_sim, on='din_instante', how='inner', suffixes=('_hist', '_sim'))

print(f"\nColunas após merge ({len(df_merged.columns)}):")
for i, col in enumerate(df_merged.columns):
    print(f"  {i+1}. {col}")







