import pandas as pd
from pathlib import Path

df = pd.read_parquet(Path('C:/Users/joao.barbosa/Desktop/Codigos/Codigos ONS/mini_dessem/output/curtailment/curtailment_raw.parquet'))
df['data'] = pd.to_datetime(df['data'])

print('\n=== PERIODO COMPLETO DOS DADOS ===')
print(f'Data inicial: {df["data"].min().date()}')
print(f'Data final: {df["data"].max().date()}')
print(f'Total de dias: {(df["data"].max() - df["data"].min()).days + 1}')

print('\n=== ULTIMOS 30 DIAS ===')
cutoff = df["data"].max() - pd.Timedelta(days=29)
df_recent = df[df["data"] >= cutoff]
dates = sorted(df_recent['data'].dt.date.unique())
print(f'De: {dates[0]}')
print(f'Ate: {dates[-1]}')
print(f'Total de dias: {len(dates)}')

print('\n=== ESTATISTICAS DOS ULTIMOS 30 DIAS ===')
print(f'Total de registros: {len(df_recent):,}')
print(f'Eolica: {len(df_recent[df_recent["tipo_usina"]=="eolica"]):,}')
print(f'Solar: {len(df_recent[df_recent["tipo_usina"]=="solar"]):,}')

# Calcular curtailment total
df_recent['curt_mwh'] = df_recent['val_curtail_mwh']
curt_total = df_recent.groupby('tipo_usina')['curt_mwh'].sum()
print('\n=== CURTAILMENT TOTAL (ULTIMOS 30 DIAS) ===')
for fonte, valor in curt_total.items():
    print(f'{fonte.capitalize()}: {valor:,.0f} MWh')
print(f'TOTAL: {curt_total.sum():,.0f} MWh')





