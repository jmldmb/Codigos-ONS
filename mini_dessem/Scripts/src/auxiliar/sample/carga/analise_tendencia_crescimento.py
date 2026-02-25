"""
ANÁLISE: SEPARAR EFEITO TEMPERATURA vs CRESCIMENTO
===================================================

Identificar e remover tendência temporal de crescimento
para isolar efeito puro de temperatura
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from sklearn.linear_model import LinearRegression

print("="*100)
print("  ANÁLISE: SEPARAR EFEITO TEMPERATURA vs CRESCIMENTO")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1/5] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()
df_du = df[(df['tipo_dia_v2'] == 'DU')].copy()

print(f"  [OK] {len(df_du):,} horas de dias úteis")

# Criar variável temporal (dias desde início)
df_du['dias_desde_inicio'] = (df_du['timestamp'] - df_du['timestamp'].min()).dt.days

# ============================================================================
# 2. ANÁLISE DE TENDÊNCIA TEMPORAL
# ============================================================================
print("\n[2/5] ANALISANDO TENDÊNCIA TEMPORAL...")

# Carga média mensal ao longo do tempo
df_mensal = df_du.groupby(['ano', 'mes']).agg({
    'carga_mw': 'mean',
    'temp_brasil_c': 'mean',
    'timestamp': 'first'
}).reset_index()

df_mensal['dias_desde_inicio'] = (df_mensal['timestamp'] - df_mensal['timestamp'].min()).dt.days

# Tendência linear da carga
slope_carga, intercept_carga, r_carga, p_carga, _ = stats.linregress(
    df_mensal['dias_desde_inicio'], 
    df_mensal['carga_mw']
)

# Tendência linear da temperatura
slope_temp, intercept_temp, r_temp, p_temp, _ = stats.linregress(
    df_mensal['dias_desde_inicio'], 
    df_mensal['temp_brasil_c']
)

print(f"\n  TENDÊNCIA DE CARGA:")
print(f"    Slope:        {slope_carga:+.2f} MW/dia = {slope_carga*365:+,.0f} MW/ano")
print(f"    Crescimento:  {(slope_carga*365/df_mensal['carga_mw'].mean())*100:+.2f}%/ano")
print(f"    R2:           {r_carga**2:.4f}")
print(f"    P-value:      {p_carga:.4e}")

print(f"\n  TENDÊNCIA DE TEMPERATURA:")
print(f"    Slope:        {slope_temp:+.4f} °C/dia = {slope_temp*365:+.3f} °C/ano")
print(f"    R2:           {r_temp**2:.4f}")
print(f"    P-value:      {p_temp:.4e}")

# ============================================================================
# 3. REMOVER TENDÊNCIA (DETREND)
# ============================================================================
print("\n[3/5] REMOVENDO TENDÊNCIA TEMPORAL...")

# Carga esperada pela tendência temporal
df_du['carga_tendencia'] = intercept_carga + slope_carga * df_du['dias_desde_inicio']

# Carga detrendada (remover crescimento)
df_du['carga_detrendada'] = df_du['carga_mw'] - df_du['carga_tendencia'] + df_du['carga_mw'].mean()

print(f"\n  Estatísticas após detrend:")
print(f"    Carga original - média:     {df_du['carga_mw'].mean():,.0f} MW")
print(f"    Carga detrendada - média:   {df_du['carga_detrendada'].mean():,.0f} MW")
print(f"    Carga original - std:       {df_du['carga_mw'].std():,.0f} MW")
print(f"    Carga detrendada - std:     {df_du['carga_detrendada'].std():,.0f} MW")

# ============================================================================
# 4. COMPARAR CORRELAÇÕES: ANTES vs DEPOIS
# ============================================================================
print("\n[4/5] COMPARANDO CORRELAÇÕES...")

# ANTES: Carga original vs Temperatura
corr_antes = df_du[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
slope_antes, intercept_antes, r_antes, p_antes, _ = stats.linregress(
    df_du['temp_brasil_c'], 
    df_du['carga_mw']
)
r2_antes = r_antes ** 2

# DEPOIS: Carga detrendada vs Temperatura
corr_depois = df_du[['temp_brasil_c', 'carga_detrendada']].corr().iloc[0, 1]
slope_depois, intercept_depois, r_depois, p_depois, _ = stats.linregress(
    df_du['temp_brasil_c'], 
    df_du['carga_detrendada']
)
r2_depois = r_depois ** 2

print(f"\n{'Métrica':25s} | {'ANTES (com trend)':>20s} | {'DEPOIS (detrendada)':>20s} | {'Diferença':>12s}")
print("-"*85)
print(f"{'Correlação':25s} | {corr_antes:>+19.4f} | {corr_depois:>+19.4f} | {corr_depois-corr_antes:>+11.4f}")
print(f"{'R2':25s} | {r2_antes:>19.4f} | {r2_depois:>19.4f} | {r2_depois-r2_antes:>+11.4f}")
print(f"{'Slope (MW/°C)':25s} | {slope_antes:>+19.1f} | {slope_depois:>+19.1f} | {slope_depois-slope_antes:>+11.1f}")
print(f"{'P-value':25s} | {p_antes:>19.2e} | {p_depois:>19.2e} | {'':>12s}")

print(f"\n  INTERPRETAÇÃO:")
if r2_depois < r2_antes:
    diff_pct = ((r2_antes - r2_depois) / r2_antes) * 100
    print(f"    R2 DIMINUIU {diff_pct:.1f}% após remover tendência")
    print(f"    Parte da correlação era ESPÚRIA (devido ao crescimento temporal)!")
    print(f"    Correlação VERDADEIRA com temperatura: R2 = {r2_depois:.4f} ({r2_depois*100:.1f}%)")
else:
    print(f"    R2 não mudou significativamente")
    print(f"    Tendência temporal não afeta correlação temperatura-carga")

# ============================================================================
# 5. ANÁLISE POR ANO
# ============================================================================
print("\n[5/5] ANÁLISE POR ANO (INTRA-ANUAL)...")

print(f"\n{'Ano':>6} | {'Corr Temp-Carga':>17} | {'R2':>8} | {'Slope':>12} | {'N Obs':>8}")
print("-"*65)

for ano in sorted(df_du['ano'].unique()):
    df_ano = df_du[df_du['ano'] == ano]
    
    if len(df_ano) >= 100:
        corr_ano = df_ano[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
        slope_ano, _, r_ano, _, _ = stats.linregress(
            df_ano['temp_brasil_c'], 
            df_ano['carga_mw']
        )
        r2_ano = r_ano ** 2
        
        print(f"{ano:>6.0f} | {corr_ano:>+16.4f} | {r2_ano:>7.4f} | {slope_ano:>+11.1f} | {len(df_ano):>8}")

print(f"\n  Média intra-anual (sem efeito inter-anual):")
correlacoes_ano = []
r2s_ano = []
for ano in sorted(df_du['ano'].unique()):
    df_ano = df_du[df_du['ano'] == ano]
    if len(df_ano) >= 100:
        corr = df_ano[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
        _, _, r, _, _ = stats.linregress(df_ano['temp_brasil_c'], df_ano['carga_mw'])
        correlacoes_ano.append(corr)
        r2s_ano.append(r**2)

if correlacoes_ano:
    print(f"    Correlação média: {np.mean(correlacoes_ano):+.4f}")
    print(f"    R2 médio:         {np.mean(r2s_ano):.4f}")

# ============================================================================
# VISUALIZAÇÕES
# ============================================================================
print("\n" + "="*100)
print("  GERANDO VISUALIZAÇÕES...")
print("="*100)

# Figura 1: Tendência temporal de carga e temperatura
fig, axes = plt.subplots(2, 1, figsize=(16, 10))

# Subplot 1: Carga ao longo do tempo
ax = axes[0]
ax.scatter(df_mensal['timestamp'], df_mensal['carga_mw'], 
          s=100, alpha=0.6, color='steelblue', label='Carga mensal')

# Linha de tendência
x_days = np.linspace(df_mensal['dias_desde_inicio'].min(), 
                     df_mensal['dias_desde_inicio'].max(), 100)
y_tend = intercept_carga + slope_carga * x_days
x_dates = df_mensal['timestamp'].min() + pd.to_timedelta(x_days, unit='D')
ax.plot(x_dates, y_tend, 'r-', linewidth=3, alpha=0.7,
       label=f'Tendência: {slope_carga*365:+,.0f} MW/ano (R2={r_carga**2:.3f})')

ax.set_xlabel('Data', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Tendência Temporal de Carga (2023-2025)', fontsize=14, fontweight='bold')
ax.legend(fontsize=11, loc='best')
ax.grid(True, alpha=0.3)

# Subplot 2: Temperatura ao longo do tempo
ax = axes[1]
ax.scatter(df_mensal['timestamp'], df_mensal['temp_brasil_c'], 
          s=100, alpha=0.6, color='red', label='Temperatura mensal')

# Linha de tendência
y_tend_temp = intercept_temp + slope_temp * x_days
ax.plot(x_dates, y_tend_temp, 'darkred', linewidth=3, alpha=0.7,
       label=f'Tendência: {slope_temp*365:+.3f} °C/ano (R2={r_temp**2:.3f})')

ax.set_xlabel('Data', fontsize=12, fontweight='bold')
ax.set_ylabel('Temperatura (°C)', fontsize=12, fontweight='bold')
ax.set_title('Tendência Temporal de Temperatura (2023-2025)', fontsize=14, fontweight='bold')
ax.legend(fontsize=11, loc='best')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '34_tendencia_temporal.png', dpi=150, bbox_inches='tight')
print(f"\n[1/3] Salvo: 34_tendencia_temporal.png")

# Figura 2: Comparação ANTES vs DEPOIS do detrend
fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# ANTES
ax = axes[0]
sample = df_du.sample(min(5000, len(df_du)), random_state=42)
ax.scatter(sample['temp_brasil_c'], sample['carga_mw'], 
          alpha=0.3, s=10, color='steelblue')
x_line = np.linspace(df_du['temp_brasil_c'].min(), df_du['temp_brasil_c'].max(), 100)
y_line = slope_antes * x_line + intercept_antes
ax.plot(x_line, y_line, 'r-', linewidth=3, label=f'R2={r2_antes:.4f}')
ax.set_xlabel('Temperatura (°C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('ANTES: Carga Original (COM tendência temporal)', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

# DEPOIS
ax = axes[1]
ax.scatter(sample['temp_brasil_c'], sample['carga_detrendada'], 
          alpha=0.3, s=10, color='darkgreen')
x_line = np.linspace(df_du['temp_brasil_c'].min(), df_du['temp_brasil_c'].max(), 100)
y_line = slope_depois * x_line + intercept_depois
ax.plot(x_line, y_line, 'r-', linewidth=3, label=f'R2={r2_depois:.4f}')
ax.set_xlabel('Temperatura (°C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Detrendada (MW)', fontsize=12, fontweight='bold')
ax.set_title('DEPOIS: Carga Detrendada (SEM tendência temporal)', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '35_comparacao_antes_depois_detrend.png', dpi=150, bbox_inches='tight')
print(f"[2/3] Salvo: 35_comparacao_antes_depois_detrend.png")

# Figura 3: Correlação por ano
fig, ax = plt.subplots(figsize=(14, 8))

anos = []
r2s = []
for ano in sorted(df_du['ano'].unique()):
    df_ano = df_du[df_du['ano'] == ano]
    if len(df_ano) >= 100:
        _, _, r, _, _ = stats.linregress(df_ano['temp_brasil_c'], df_ano['carga_mw'])
        anos.append(ano)
        r2s.append(r**2)

ax.bar(anos, r2s, color='steelblue', alpha=0.7, edgecolor='black', width=0.6)
ax.axhline(r2_antes, color='red', linewidth=2, linestyle='--', 
          label=f'R2 inter-anual (com trend): {r2_antes:.4f}')
ax.axhline(r2_depois, color='green', linewidth=2, linestyle='--',
          label=f'R2 detrendado: {r2_depois:.4f}')
ax.axhline(np.mean(r2s), color='blue', linewidth=2, linestyle='-',
          label=f'R2 médio intra-anual: {np.mean(r2s):.4f}')

ax.set_xlabel('Ano', fontsize=12, fontweight='bold')
ax.set_ylabel('R2 (Temperatura vs Carga)', fontsize=12, fontweight='bold')
ax.set_title('Correlação Temperatura-Carga por Ano\n(elimina efeito inter-anual)', 
            fontsize=14, fontweight='bold')
ax.legend(fontsize=11, loc='best')
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(anos)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '36_correlacao_por_ano.png', dpi=150, bbox_inches='tight')
print(f"[3/3] Salvo: 36_correlacao_por_ano.png")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO: EFEITO TEMPERATURA vs CRESCIMENTO")
print("="*100)

print(f"""
TENDÊNCIA TEMPORAL:
  Carga:        {slope_carga*365:+,.0f} MW/ano ({(slope_carga*365/df_mensal['carga_mw'].mean())*100:+.2f}%/ano)
  Temperatura:  {slope_temp*365:+.3f} °C/ano
  
CORRELAÇÃO TEMPERATURA-CARGA:
  COM tendência (R2):     {r2_antes:.4f} ({r2_antes*100:.1f}%)
  SEM tendência (R2):     {r2_depois:.4f} ({r2_depois*100:.1f}%)
  Diferença:              {r2_antes-r2_depois:+.4f} ({(r2_antes-r2_depois)*100:+.1f} pontos percentuais)
  
  Perda de R2:            {((r2_antes-r2_depois)/r2_antes)*100:.1f}% do R2 era ESPÚRIO!
  
CORRELAÇÃO MÉDIA INTRA-ANUAL:
  R2 médio dentro de cada ano: {np.mean(r2s):.4f}
  (Elimina completamente efeito inter-anual)
  
RECOMENDAÇÃO:
  {'Usar carga DETRENDADA para análises!' if r2_depois < r2_antes * 0.9 else 'Tendência não afeta muito, pode usar carga original'}
  Correlação VERDADEIRA com temperatura: R2 = {r2_depois:.4f}
""")

print("="*100)
print(f"Gráficos salvos em: {OUTPUT_DIR}")
print("="*100)

# Salvar dados
df_du[['timestamp', 'carga_mw', 'carga_tendencia', 'carga_detrendada', 'temp_brasil_c']].to_csv(
    OUTPUT_DIR / 'carga_detrendada.csv', index=False
)
print(f"\n[OK] Dados salvos: carga_detrendada.csv")





