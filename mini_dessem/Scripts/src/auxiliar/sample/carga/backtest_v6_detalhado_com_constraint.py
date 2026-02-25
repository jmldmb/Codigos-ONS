"""
BACKTEST DETALHADO: V6 COM CONSTRAINT
======================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime, date
from scipy import stats
import sys

sys.path.insert(0, str(Path(__file__).parent))
from carga_model_v6 import sample_carga_v6

print("="*100)
print("  BACKTEST DETALHADO: V6 COM CONSTRAINT")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"
BACKTEST_DIR = BASE_DIR / "output" / "sample" / "carga_v6_com_constraint"
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

# Forçar reload dos parâmetros
import carga_model_v6
carga_model_v6._PARAMS_CACHE = None

print("\n[1/5] CARREGANDO DADOS...")
df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()
df['temp_media_mes'] = df.groupby(['ano', 'mes'])['temp_brasil_c'].transform('mean')
df['carga_media_mes'] = df.groupby(['ano', 'mes'])['carga_mw'].transform('mean')
df['data'] = df['timestamp'].dt.date

print(f"  [OK] {len(df):,} horas")

print("\n[2/5] SIMULANDO...")
simulacoes = []
for data_dia in df['data'].unique():
    df_dia = df[df['data'] == data_dia].sort_values('hora')
    if len(df_dia) != 24:
        continue
    
    try:
        # Extrair temperaturas horárias REAIS do dia
        temp_horaria_real = {}
        for _, row in df_dia.iterrows():
            temp_horaria_real[int(row['hora'])] = float(row['temp_brasil_c'])
        
        # Simular com temperaturas REAIS hora-a-hora
        carga_sim = sample_carga_v6(
            data_dia, 
            df_dia['carga_media_mes'].iloc[0], 
            df_dia['temp_media_mes'].iloc[0],
            temp_horaria_real=temp_horaria_real  # AGORA SIM USA TEMP REAL!
        )
        
        for h in range(24):
            simulacoes.append({
                'timestamp': df_dia.iloc[h]['timestamp'],
                'hora': h,
                'carga_real': df_dia.iloc[h]['carga_mw'],
                'carga_sim': carga_sim[h],
                'mes': df_dia.iloc[h]['mes'],
                'tipo_dia': df_dia.iloc[h]['tipo_dia_v2']
            })
    except:
        pass

df_backtest = pd.DataFrame(simulacoes)
print(f"  [OK] {len(df_backtest):,} horas simuladas")

print("\n[3/5] CALCULANDO MÉTRICAS...")
df_backtest['erro'] = df_backtest['carga_sim'] - df_backtest['carga_real']
df_backtest['erro_abs'] = np.abs(df_backtest['erro'])
df_backtest['erro_pct'] = (df_backtest['erro'] / df_backtest['carga_real']) * 100
df_backtest['erro_pct_abs'] = np.abs(df_backtest['erro_pct'])

mae = df_backtest['erro_abs'].mean()
rmse = np.sqrt((df_backtest['erro']**2).mean())
mape = df_backtest['erro_pct_abs'].mean()
bias = df_backtest['erro'].mean()
bias_pct = (bias / df_backtest['carga_real'].mean()) * 100

slope, intercept, r_val, _, _ = stats.linregress(df_backtest['carga_real'], df_backtest['carga_sim'])
r2 = r_val ** 2

print(f"\n  MAPE:  {mape:.2f}%")
print(f"  MAE:   {mae:,.0f} MW")
print(f"  RMSE:  {rmse:,.0f} MW")
print(f"  Bias:  {bias:+,.0f} MW ({bias_pct:+.2f}%)")
print(f"  R2:    {r2:.4f}")

print("\n[4/5] GERANDO GRÁFICOS...")

# Fig 1: Scatter + Erros
fig, axes = plt.subplots(1, 2, figsize=(18, 7))

ax = axes[0]
sample = df_backtest.sample(min(5000, len(df_backtest)), random_state=42)
ax.scatter(sample['carga_real'], sample['carga_sim'], alpha=0.3, s=10, color='green')
x_line = np.linspace(df_backtest['carga_real'].min(), df_backtest['carga_real'].max(), 100)
y_line = slope * x_line + intercept
ax.plot(x_line, y_line, 'r-', linewidth=3, alpha=0.7, label=f'R2={r2:.4f}')
ax.plot([df_backtest['carga_real'].min(), df_backtest['carga_real'].max()],
        [df_backtest['carga_real'].min(), df_backtest['carga_real'].max()],
        'k--', linewidth=2, alpha=0.5, label='Perfeito')
ax.set_xlabel('Carga Real (MW)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Simulada (MW)', fontsize=12, fontweight='bold')
ax.set_title(f'Real vs Simulado\nMAPE={mape:.2f}%, R2={r2:.4f}', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

ax = axes[1]
ax.hist(df_backtest['erro_pct'], bins=100, color='green', alpha=0.7, edgecolor='black')
ax.axvline(0, color='red', linewidth=2, linestyle='--', label='Zero')
ax.axvline(bias_pct, color='darkgreen', linewidth=2, label=f'Bias={bias_pct:.2f}%')
ax.set_xlabel('Erro (%)', fontsize=12, fontweight='bold')
ax.set_ylabel('Frequencia', fontsize=12, fontweight='bold')
ax.set_title('Distribuicao de Erros', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')

plt.suptitle('V6 COM CONSTRAINT', fontsize=16, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(BACKTEST_DIR / '01_scatter_erros.png', dpi=150, bbox_inches='tight')
print(f"  [1/4] Salvo: 01_scatter_erros.png")

# Fig 2: Métricas por hora
metricas_hora = []
for h in range(24):
    df_h = df_backtest[df_backtest['hora'] == h]
    mape_h = df_h['erro_pct_abs'].mean()
    mae_h = df_h['erro_abs'].mean()
    bias_h = df_h['erro'].mean()
    slope_h, _, r_h, _, _ = stats.linregress(df_h['carga_real'], df_h['carga_sim'])
    metricas_hora.append({'hora': h, 'mape': mape_h, 'mae': mae_h, 'bias': bias_h, 'r2': r_h**2})

df_mh = pd.DataFrame(metricas_hora)

fig, axes = plt.subplots(2, 2, figsize=(18, 12))

ax = axes[0, 0]
ax.bar(df_mh['hora'], df_mh['mape'], color='green', alpha=0.7)
ax.axhline(mape, color='red', linestyle='--', label=f'Media={mape:.2f}%')
ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
ax.set_ylabel('MAPE (%)', fontsize=11, fontweight='bold')
ax.set_title('MAPE por Hora', fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

ax = axes[0, 1]
ax.bar(df_mh['hora'], df_mh['mae'], color='orange', alpha=0.7)
ax.axhline(mae, color='red', linestyle='--', label=f'Media={mae:.0f} MW')
ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
ax.set_ylabel('MAE (MW)', fontsize=11, fontweight='bold')
ax.set_title('MAE por Hora', fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

ax = axes[1, 0]
ax.bar(df_mh['hora'], df_mh['bias'], color='darkgreen', alpha=0.7)
ax.axhline(0, color='black', linestyle='-', linewidth=1)
ax.axhline(bias, color='red', linestyle='--', label=f'Media={bias:.0f} MW')
ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
ax.set_ylabel('Bias (MW)', fontsize=11, fontweight='bold')
ax.set_title('Bias por Hora', fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

ax = axes[1, 1]
ax.bar(df_mh['hora'], df_mh['r2'], color='purple', alpha=0.7)
ax.axhline(r2, color='red', linestyle='--', label=f'Media={r2:.4f}')
ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
ax.set_ylabel('R2', fontsize=11, fontweight='bold')
ax.set_title('R2 por Hora', fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim([0, 1])

plt.suptitle('Metricas por Hora - V6 COM CONSTRAINT', fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(BACKTEST_DIR / '02_metricas_hora.png', dpi=150, bbox_inches='tight')
print(f"  [2/4] Salvo: 02_metricas_hora.png")

# Fig 3: Métricas por mês
metricas_mes = []
for m in range(1, 13):
    df_m = df_backtest[df_backtest['mes'] == m]
    if len(df_m) > 0:
        mape_m = df_m['erro_pct_abs'].mean()
        mae_m = df_m['erro_abs'].mean()
        bias_m = df_m['erro'].mean()
        slope_m, _, r_m, _, _ = stats.linregress(df_m['carga_real'], df_m['carga_sim'])
        metricas_mes.append({'mes': m, 'mape': mape_m, 'mae': mae_m, 'bias': bias_m, 'r2': r_m**2})

df_mm = pd.DataFrame(metricas_mes)

fig, axes = plt.subplots(2, 2, figsize=(18, 12))

ax = axes[0, 0]
ax.bar(df_mm['mes'], df_mm['mape'], color='green', alpha=0.7)
ax.axhline(mape, color='red', linestyle='--')
ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
ax.set_ylabel('MAPE (%)', fontsize=11, fontweight='bold')
ax.set_title('MAPE por Mes', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(range(1, 13))

ax = axes[0, 1]
ax.bar(df_mm['mes'], df_mm['mae'], color='orange', alpha=0.7)
ax.axhline(mae, color='red', linestyle='--')
ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
ax.set_ylabel('MAE (MW)', fontsize=11, fontweight='bold')
ax.set_title('MAE por Mes', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(range(1, 13))

ax = axes[1, 0]
ax.bar(df_mm['mes'], df_mm['bias'], color='darkgreen', alpha=0.7)
ax.axhline(0, color='black', linestyle='-', linewidth=1)
ax.axhline(bias, color='red', linestyle='--')
ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
ax.set_ylabel('Bias (MW)', fontsize=11, fontweight='bold')
ax.set_title('Bias por Mes', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(range(1, 13))

ax = axes[1, 1]
ax.bar(df_mm['mes'], df_mm['r2'], color='purple', alpha=0.7)
ax.axhline(r2, color='red', linestyle='--')
ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
ax.set_ylabel('R2', fontsize=11, fontweight='bold')
ax.set_title('R2 por Mes', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(range(1, 13))
ax.set_ylim([0, 1])

plt.suptitle('Metricas por Mes - V6 COM CONSTRAINT', fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(BACKTEST_DIR / '03_metricas_mes.png', dpi=150, bbox_inches='tight')
print(f"  [3/4] Salvo: 03_metricas_mes.png")

# Fig 4: Série temporal
df_sorted = df_backtest.sort_values('timestamp')
df_30d = df_sorted.tail(24 * 30)

fig, ax = plt.subplots(figsize=(20, 8))
ax.plot(df_30d['timestamp'], df_30d['carga_real'], label='Real', color='blue', linewidth=2, alpha=0.7)
ax.plot(df_30d['timestamp'], df_30d['carga_sim'], label='Simulado', color='green', linewidth=2, alpha=0.7, linestyle='--')
ax.set_xlabel('Data/Hora', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Serie Temporal: Real vs Simulado (Ultimos 30 dias) - V6 COM CONSTRAINT', fontsize=14, fontweight='bold')
ax.legend(fontsize=12)
ax.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(BACKTEST_DIR / '04_serie_temporal.png', dpi=150, bbox_inches='tight')
print(f"  [4/4] Salvo: 04_serie_temporal.png")

print("\n[5/5] SALVANDO RESULTADOS...")
df_backtest.to_csv(BACKTEST_DIR / 'backtest_completo.csv', index=False)
print(f"  [OK] Salvo: backtest_completo.csv")

pd.DataFrame([{
    'modelo': 'V6_COM_constraint',
    'mape': mape,
    'mae': mae,
    'rmse': rmse,
    'bias': bias,
    'bias_pct': bias_pct,
    'r2': r2,
    'n_obs': len(df_backtest)
}]).to_csv(BACKTEST_DIR / 'metricas.csv', index=False)
print(f"  [OK] Salvo: metricas.csv")

print("\n" + "="*100)
print(f"BACKTEST COMPLETO SALVO EM: {BACKTEST_DIR}")
print("="*100)

