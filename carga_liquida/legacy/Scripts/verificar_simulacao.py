import pandas as pd
from pathlib import Path

resultados_dir = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\output\resultados")
arquivos = sorted(resultados_dir.glob("resultados_simulacao_*.parquet"))
path = arquivos[-1]  # Mais recente
print(f"Arquivo: {path.name}\n")
df = pd.read_parquet(path)

print(f"Anos simulados: {sorted(df['ano'].unique())}")
print(f"\nMeses por ano:")
for ano in sorted(df['ano'].unique()):
    meses = sorted(df[df['ano']==ano]['mes'].unique())
    print(f"  {ano}: {meses}")

print(f"\nTotal de registros: {len(df):,}")
print(f"Cenarios: {df['simulacao'].nunique()}")

