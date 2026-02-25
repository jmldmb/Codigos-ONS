"""
ANÁLISE: TEMPERATURA ABSOLUTA vs CARGA ABSOLUTA
================================================

Ver relação direta (não diferenças) entre temperatura e carga
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

print("="*100)
print("  ANÁLISE: TEMPERATURA ABSOLUTA vs CARGA ABSOLUTA")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1/4] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

# Filtrar apenas dias úteis
df_du = df[(df['tipo_dia_v2'] == 'DU')].copy()

print(f"  [OK] {len(df_du):,} horas de dias úteis")
print(f"       Período: {df_du['timestamp'].min()} até {df_du['timestamp'].max()}")

# ============================================================================
# 2. ANÁLISE GERAL
# ============================================================================
print("\n[2/4] ANÁLISE GERAL...")

# Correlação geral
corr_geral = df_du[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
print(f"\n  Correlação geral (temp x carga): {corr_geral:+.4f}")

# Regressão linear geral
slope, intercept, r_value, p_value, std_err = stats.linregress(df_du['temp_brasil_c'], df_du['carga_mw'])
print(f"\n  Regressão Linear: carga = {slope:.1f} * temp + {intercept:.0f}")
print(f"    R²: {r_value**2:.4f}")
print(f"    P-value: {p_value:.2e}")

# ============================================================================
# 3. ANÁLISE POR HORA
# ============================================================================
print("\n[3/4] ANÁLISE POR HORA DO DIA...")

correlacoes_hora = []
for hora in range(24):
    df_hora = df_du[df_du['hora'] == hora]
    
    if len(df_hora) > 50:
        corr = df_hora[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
        slope_h, intercept_h, r_h, p_h, _ = stats.linregress(df_hora['temp_brasil_c'], df_hora['carga_mw'])
        
        correlacoes_hora.append({
            'hora': hora,
            'corr': corr,
            'slope': slope_h,
            'r2': r_h**2,
            'p_value': p_h,
            'n_obs': len(df_hora),
            'carga_media': df_hora['carga_mw'].mean(),
            'temp_media': df_hora['temp_brasil_c'].mean()
        })

df_corr_hora = pd.DataFrame(correlacoes_hora)

print(f"\n{'Hora':>4} | {'Corr':>7} | {'R²':>7} | {'Slope (MW/C)':>14} | {'Carga Média':>12} | {'Temp Média':>11}")
print("-"*75)
for _, row in df_corr_hora.iterrows():
    print(f"{row['hora']:>4.0f} | {row['corr']:>+6.4f} | {row['r2']:>6.4f} | {row['slope']:>+13.1f} | "
          f"{row['carga_media']:>10,.0f} MW | {row['temp_media']:>9.1f}C")

print(f"\n  Hora com MAIOR correlação: {df_corr_hora.loc[df_corr_hora['corr'].abs().idxmax(), 'hora']:.0f}h "
      f"(corr={df_corr_hora['corr'].abs().max():+.4f})")
print(f"  Hora com MENOR correlação: {df_corr_hora.loc[df_corr_hora['corr'].abs().idxmin(), 'hora']:.0f}h "
      f"(corr={df_corr_hora['corr'].abs().min():+.4f})")

# ============================================================================
# 4. ANÁLISE POR MÊS
# ============================================================================
print("\n[4/4] ANÁLISE POR MÊS...")

correlacoes_mes = []
for mes in range(1, 13):
    df_mes = df_du[df_du['mes'] == mes]
    
    if len(df_mes) > 100:
        corr = df_mes[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
        slope_m, intercept_m, r_m, p_m, _ = stats.linregress(df_mes['temp_brasil_c'], df_mes['carga_mw'])
        
        correlacoes_mes.append({
            'mes': mes,
            'corr': corr,
            'slope': slope_m,
            'r2': r_m**2,
            'p_value': p_m,
            'n_obs': len(df_mes),
            'carga_media': df_mes['carga_mw'].mean(),
            'temp_media': df_mes['temp_brasil_c'].mean()
        })

df_corr_mes = pd.DataFrame(correlacoes_mes)

print(f"\n{'Mês':>4} | {'Corr':>7} | {'R²':>7} | {'Slope (MW/C)':>14} | {'Carga Média':>12} | {'Temp Média':>11}")
print("-"*75)
for _, row in df_corr_mes.iterrows():
    print(f"{row['mes']:>4.0f} | {row['corr']:>+6.4f} | {row['r2']:>6.4f} | {row['slope']:>+13.1f} | "
          f"{row['carga_media']:>10,.0f} MW | {row['temp_media']:>9.1f}C")

# ============================================================================
# VISUALIZAÇÕES
# ============================================================================
print("\n" + "="*100)
print("  GERANDO VISUALIZAÇÕES...")
print("="*100)

# Figura 1: Scatter geral com densidade
fig, axes = plt.subplots(2, 2, figsize=(18, 14))

# Subplot 1: Scatter geral
ax = axes[0, 0]
sample = df_du.sample(min(10000, len(df_du)), random_state=42)
scatter = ax.scatter(sample['temp_brasil_c'], sample['carga_mw'], 
                    c=sample['hora'], cmap='viridis', alpha=0.4, s=20, edgecolors='none')
x_line = np.linspace(df_du['temp_brasil_c'].min(), df_du['temp_brasil_c'].max(), 100)
y_line = slope * x_line + intercept
ax.plot(x_line, y_line, 'r-', linewidth=3, 
        label=f'y = {slope:.1f}x + {intercept:.0f}\nR2 = {r_value**2:.4f}')
ax.set_xlabel('Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Temperatura vs Carga - Dias Uteis\n(cor = hora do dia)', 
             fontsize=13, fontweight='bold')
plt.colorbar(scatter, ax=ax, label='Hora')
ax.legend(fontsize=11, loc='upper left')
ax.grid(True, alpha=0.3)

# Subplot 2: Hexbin (densidade)
ax = axes[0, 1]
hexbin = ax.hexbin(df_du['temp_brasil_c'], df_du['carga_mw'], 
                   gridsize=30, cmap='YlOrRd', mincnt=1)
ax.plot(x_line, y_line, 'b-', linewidth=3, alpha=0.7,
        label=f'Regressao Linear (R2={r_value**2:.4f})')
ax.set_xlabel('Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Densidade: Temperatura vs Carga', fontsize=13, fontweight='bold')
plt.colorbar(hexbin, ax=ax, label='Contagem')
ax.legend(fontsize=11, loc='upper left')
ax.grid(True, alpha=0.3)

# Subplot 3: Por mês
ax = axes[1, 0]
meses_plot = [1, 4, 7, 10]  # Jan, Abr, Jul, Out
cores_meses = {'1': 'red', '4': 'orange', '7': 'blue', '10': 'green'}
nomes_meses = {1: 'Jan', 4: 'Abr', 7: 'Jul', 10: 'Out'}

for mes in meses_plot:
    df_mes = df_du[df_du['mes'] == mes].sample(min(1000, len(df_du[df_du['mes'] == mes])), random_state=42)
    ax.scatter(df_mes['temp_brasil_c'], df_mes['carga_mw'], 
              alpha=0.3, s=15, label=nomes_meses[mes], 
              color=cores_meses[str(mes)])

ax.set_xlabel('Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Temperatura vs Carga por Mes (amostra)', fontsize=13, fontweight='bold')
ax.legend(fontsize=11, loc='upper left')
ax.grid(True, alpha=0.3)

# Subplot 4: Por hora (amostra de horas específicas)
ax = axes[1, 1]
horas_plot = [3, 9, 15, 21]  # Madrugada, manhã, tarde, noite
cores_horas = {3: 'darkblue', 9: 'green', 15: 'red', 21: 'purple'}

for hora in horas_plot:
    df_hora = df_du[df_du['hora'] == hora].sample(min(800, len(df_du[df_du['hora'] == hora])), random_state=42)
    ax.scatter(df_hora['temp_brasil_c'], df_hora['carga_mw'], 
              alpha=0.4, s=20, label=f'{hora}h', 
              color=cores_horas[hora])

ax.set_xlabel('Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Temperatura vs Carga por Hora (amostra)', fontsize=13, fontweight='bold')
ax.legend(fontsize=11, loc='upper left')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '19_temperatura_absoluta_vs_carga.png', dpi=150, bbox_inches='tight')
print(f"\n[1/4] Salvo: 19_temperatura_absoluta_vs_carga.png")

# Figura 2: Correlação e R² por hora e mês
fig, axes = plt.subplots(2, 2, figsize=(18, 12))

# Correlação por hora
ax = axes[0, 0]
ax.bar(df_corr_hora['hora'], df_corr_hora['corr'], 
       color=['red' if x > 0 else 'blue' for x in df_corr_hora['corr']],
       alpha=0.7, edgecolor='black')
ax.axhline(0, color='black', linewidth=1)
ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('Correlacao', fontsize=12, fontweight='bold')
ax.set_title('Correlacao Temperatura-Carga por Hora', fontsize=13, fontweight='bold')
ax.set_xticks(range(0, 24, 2))
ax.grid(True, alpha=0.3, axis='y')

# R² por hora
ax = axes[0, 1]
ax.bar(df_corr_hora['hora'], df_corr_hora['r2'], 
       color='steelblue', alpha=0.7, edgecolor='black')
ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('R2', fontsize=12, fontweight='bold')
ax.set_title('R2 Temperatura-Carga por Hora', fontsize=13, fontweight='bold')
ax.set_xticks(range(0, 24, 2))
ax.grid(True, alpha=0.3, axis='y')

# Correlação por mês
ax = axes[1, 0]
ax.bar(df_corr_mes['mes'], df_corr_mes['corr'], 
       color=['red' if x > 0 else 'blue' for x in df_corr_mes['corr']],
       alpha=0.7, edgecolor='black')
ax.axhline(0, color='black', linewidth=1)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Correlacao', fontsize=12, fontweight='bold')
ax.set_title('Correlacao Temperatura-Carga por Mes', fontsize=13, fontweight='bold')
ax.set_xticks(range(1, 13))
ax.grid(True, alpha=0.3, axis='y')

# Slope por mês
ax = axes[1, 1]
ax.bar(df_corr_mes['mes'], df_corr_mes['slope'], 
       color=['red' if x > 0 else 'blue' for x in df_corr_mes['slope']],
       alpha=0.7, edgecolor='black')
ax.axhline(0, color='black', linewidth=1)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Coeficiente (MW/C)', fontsize=12, fontweight='bold')
ax.set_title('Sensibilidade Temperatura-Carga por Mes', fontsize=13, fontweight='bold')
ax.set_xticks(range(1, 13))
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '20_correlacao_por_hora_mes.png', dpi=150, bbox_inches='tight')
print(f"[2/4] Salvo: 20_correlacao_por_hora_mes.png")

# Figura 3: Scatter por hora (grid 6x4)
fig, axes = plt.subplots(4, 6, figsize=(24, 16))
axes = axes.flatten()

for hora in range(24):
    ax = axes[hora]
    df_hora = df_du[df_du['hora'] == hora]
    
    # Sample para não ficar muito pesado
    sample = df_hora.sample(min(2000, len(df_hora)), random_state=42)
    
    ax.scatter(sample['temp_brasil_c'], sample['carga_mw'], 
              alpha=0.3, s=10, color='steelblue')
    
    # Linha de regressão
    if len(df_hora) > 50:
        slope_h, intercept_h, r_h, _, _ = stats.linregress(df_hora['temp_brasil_c'], df_hora['carga_mw'])
        x_line = np.linspace(df_hora['temp_brasil_c'].min(), df_hora['temp_brasil_c'].max(), 100)
        y_line = slope_h * x_line + intercept_h
        ax.plot(x_line, y_line, 'r-', linewidth=2, alpha=0.7)
        
        # Título com R²
        r2 = r_h**2
        ax.set_title(f'{hora}h (R2={r2:.3f}, slope={slope_h:.0f})', fontsize=10, fontweight='bold')
    else:
        ax.set_title(f'{hora}h (poucos dados)', fontsize=10)
    
    ax.set_xlabel('Temp (C)', fontsize=8)
    ax.set_ylabel('Carga (MW)', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=8)

plt.suptitle('Temperatura vs Carga por Hora do Dia (Dias Uteis)', 
             fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '21_scatter_todas_horas.png', dpi=150, bbox_inches='tight')
print(f"[3/4] Salvo: 21_scatter_todas_horas.png")

# Figura 4: Scatter por mês (grid 3x4)
fig, axes = plt.subplots(3, 4, figsize=(20, 15))
axes = axes.flatten()

for i, mes in enumerate(range(1, 13)):
    ax = axes[i]
    df_mes = df_du[df_du['mes'] == mes]
    
    # Sample
    sample = df_mes.sample(min(2000, len(df_mes)), random_state=42)
    
    ax.scatter(sample['temp_brasil_c'], sample['carga_mw'], 
              alpha=0.3, s=15, color='steelblue')
    
    # Linha de regressão
    if len(df_mes) > 100:
        slope_m, intercept_m, r_m, _, _ = stats.linregress(df_mes['temp_brasil_c'], df_mes['carga_mw'])
        x_line = np.linspace(df_mes['temp_brasil_c'].min(), df_mes['temp_brasil_c'].max(), 100)
        y_line = slope_m * x_line + intercept_m
        ax.plot(x_line, y_line, 'r-', linewidth=2.5, alpha=0.7)
        
        # Título com R²
        r2 = r_m**2
        ax.set_title(f'Mes {mes} (R2={r2:.3f}, slope={slope_m:.0f} MW/C)', 
                    fontsize=11, fontweight='bold')
    else:
        ax.set_title(f'Mes {mes} (poucos dados)', fontsize=11)
    
    ax.set_xlabel('Temperatura (C)', fontsize=10)
    ax.set_ylabel('Carga (MW)', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=9)

plt.suptitle('Temperatura vs Carga por Mes (Dias Uteis)', 
             fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '22_scatter_todos_meses.png', dpi=150, bbox_inches='tight')
print(f"[4/4] Salvo: 22_scatter_todos_meses.png")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO FINAL: TEMPERATURA ABSOLUTA vs CARGA")
print("="*100)

print(f"""
ANALISE GERAL (Dias Uteis):
  Correlacao:        {corr_geral:>+8.4f}
  R2:                {r_value**2:>8.4f}
  Slope:             {slope:>+8.1f} MW/C
  Intercepto:        {intercept:>8.0f} MW
  P-value:           {p_value:>8.2e}

INTERPRETACAO:
  Para cada 1 C de aumento na temperatura, a carga aumenta em media {slope:.1f} MW
  Isso representa {slope/80000*100:.2f}% da carga media (~80 GW)

CORRELACAO POR HORA:
  Maxima: {df_corr_hora['corr'].max():>+8.4f} (hora {df_corr_hora.loc[df_corr_hora['corr'].idxmax(), 'hora']:.0f}h)
  Minima: {df_corr_hora['corr'].min():>+8.4f} (hora {df_corr_hora.loc[df_corr_hora['corr'].idxmin(), 'hora']:.0f}h)
  Media:  {df_corr_hora['corr'].mean():>+8.4f}
  
CORRELACAO POR MES:
  Maxima: {df_corr_mes['corr'].max():>+8.4f} (mes {df_corr_mes.loc[df_corr_mes['corr'].idxmax(), 'mes']:.0f})
  Minima: {df_corr_mes['corr'].min():>+8.4f} (mes {df_corr_mes.loc[df_corr_mes['corr'].idxmin(), 'mes']:.0f})
  Media:  {df_corr_mes['corr'].mean():>+8.4f}

R2 MEDIO:
  Por hora: {df_corr_hora['r2'].mean():>8.4f} ({df_corr_hora['r2'].mean()*100:.1f}%)
  Por mes:  {df_corr_mes['r2'].mean():>8.4f} ({df_corr_mes['r2'].mean()*100:.1f}%)

SLOPE MEDIO (sensibilidade):
  Por hora: {df_corr_hora['slope'].mean():>+8.1f} MW/C
  Por mes:  {df_corr_mes['slope'].mean():>+8.1f} MW/C
""")

print("="*100)
print(f"Graficos salvos em: {OUTPUT_DIR}")
print("="*100)

# Salvar dados
df_corr_hora.to_csv(OUTPUT_DIR / 'correlacao_temp_carga_por_hora.csv', index=False)
df_corr_mes.to_csv(OUTPUT_DIR / 'correlacao_temp_carga_por_mes.csv', index=False)
print(f"\n[OK] Dados salvos:")
print(f"  - correlacao_temp_carga_por_hora.csv")
print(f"  - correlacao_temp_carga_por_mes.csv")





