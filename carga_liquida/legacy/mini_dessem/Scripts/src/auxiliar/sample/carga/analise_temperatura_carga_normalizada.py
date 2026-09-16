"""
ANÁLISE: TEMPERATURA vs CARGA NORMALIZADA
==========================================

Correlação entre temperatura e (carga_hora / carga_media_mensal)
Objetivo: Ver se temperatura afeta o SHAPE do perfil, não apenas o nível
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

print("="*100)
print("  ANÁLISE: TEMPERATURA vs CARGA NORMALIZADA (carga_hora / carga_media_mes)")
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

# ============================================================================
# 2. CALCULAR CARGA NORMALIZADA
# ============================================================================
print("\n[2/4] CALCULANDO CARGA NORMALIZADA...")

# Carga média mensal (MWmedios)
df_du['carga_media_mes'] = df_du.groupby(['ano', 'mes'])['carga_mw'].transform('mean')

# Carga normalizada (adimensional)
df_du['carga_normalizada'] = df_du['carga_mw'] / df_du['carga_media_mes']

print(f"\n  Estatísticas de Carga Normalizada:")
print(f"    Média:   {df_du['carga_normalizada'].mean():.4f} (deveria ser ~1.0)")
print(f"    Std:     {df_du['carga_normalizada'].std():.4f}")
print(f"    Min:     {df_du['carga_normalizada'].min():.4f}")
print(f"    Max:     {df_du['carga_normalizada'].max():.4f}")

# ============================================================================
# 3. ANÁLISE GERAL: ABSOLUTA vs NORMALIZADA
# ============================================================================
print("\n[3/4] ANÁLISE: ABSOLUTA vs NORMALIZADA...")

# Correlação com carga ABSOLUTA
corr_abs = df_du[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
slope_abs, intercept_abs, r_abs, p_abs, _ = stats.linregress(df_du['temp_brasil_c'], df_du['carga_mw'])
r2_abs = r_abs ** 2

# Correlação com carga NORMALIZADA
corr_norm = df_du[['temp_brasil_c', 'carga_normalizada']].corr().iloc[0, 1]
slope_norm, intercept_norm, r_norm, p_norm, _ = stats.linregress(df_du['temp_brasil_c'], df_du['carga_normalizada'])
r2_norm = r_norm ** 2

print(f"\n{'Métrica':20s} | {'ABSOLUTA':>15s} | {'NORMALIZADA':>15s} | {'Diferença':>12s}")
print("-"*70)
print(f"{'Correlação':20s} | {corr_abs:>+14.4f} | {corr_norm:>+14.4f} | {corr_norm-corr_abs:>+11.4f}")
print(f"{'R2':20s} | {r2_abs:>14.4f} | {r2_norm:>14.4f} | {r2_norm-r2_abs:>+11.4f}")
print(f"{'P-value':20s} | {p_abs:>14.2e} | {p_norm:>14.2e} | {'':>12s}")
print(f"{'Slope':20s} | {slope_abs:>+11.1f} MW/C | {slope_norm:>+11.4f} /C | {'':>12s}")

# ============================================================================
# 4. ANÁLISE POR HORA
# ============================================================================
print("\n[4/4] ANÁLISE POR HORA...")

resultados_hora = []

for hora in range(24):
    df_hora = df_du[df_du['hora'] == hora]
    
    if len(df_hora) >= 50:
        # Absoluta
        corr_abs_h = df_hora[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
        slope_abs_h, _, r_abs_h, _, _ = stats.linregress(df_hora['temp_brasil_c'], df_hora['carga_mw'])
        r2_abs_h = r_abs_h ** 2
        
        # Normalizada
        corr_norm_h = df_hora[['temp_brasil_c', 'carga_normalizada']].corr().iloc[0, 1]
        slope_norm_h, _, r_norm_h, _, _ = stats.linregress(df_hora['temp_brasil_c'], df_hora['carga_normalizada'])
        r2_norm_h = r_norm_h ** 2
        
        resultados_hora.append({
            'hora': hora,
            'corr_abs': corr_abs_h,
            'r2_abs': r2_abs_h,
            'slope_abs': slope_abs_h,
            'corr_norm': corr_norm_h,
            'r2_norm': r2_norm_h,
            'slope_norm': slope_norm_h,
            'diff_corr': corr_norm_h - corr_abs_h,
            'diff_r2': r2_norm_h - r2_abs_h,
            'n_obs': len(df_hora)
        })

df_hora = pd.DataFrame(resultados_hora)

print(f"\n{'Hora':>4} | {'Corr ABS':>9} | {'Corr NORM':>10} | {'D Corr':>9} | {'R2 ABS':>8} | {'R2 NORM':>9} | {'D R2':>8}")
print("-"*80)
for _, row in df_hora.iterrows():
    print(f"{row['hora']:>4.0f} | {row['corr_abs']:>+8.4f} | {row['corr_norm']:>+9.4f} | {row['diff_corr']:>+8.4f} | "
          f"{row['r2_abs']:>7.4f} | {row['r2_norm']:>8.4f} | {row['diff_r2']:>+7.4f}")

print(f"\n  Hora com MAIOR ganho em R2 (normalizado): {df_hora.loc[df_hora['diff_r2'].idxmax(), 'hora']:.0f}h "
      f"(ganho={df_hora['diff_r2'].max():+.4f})")
print(f"  Hora com MENOR ganho em R2 (normalizado): {df_hora.loc[df_hora['diff_r2'].idxmin(), 'hora']:.0f}h "
      f"(ganho={df_hora['diff_r2'].min():+.4f})")

# ============================================================================
# ANÁLISE POR MÊS
# ============================================================================
print("\n[5/5] ANÁLISE POR MÊS...")

resultados_mes = []

for mes in range(1, 13):
    df_mes = df_du[df_du['mes'] == mes]
    
    if len(df_mes) >= 100:
        # Absoluta
        corr_abs_m = df_mes[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
        slope_abs_m, _, r_abs_m, _, _ = stats.linregress(df_mes['temp_brasil_c'], df_mes['carga_mw'])
        r2_abs_m = r_abs_m ** 2
        
        # Normalizada
        corr_norm_m = df_mes[['temp_brasil_c', 'carga_normalizada']].corr().iloc[0, 1]
        slope_norm_m, _, r_norm_m, _, _ = stats.linregress(df_mes['temp_brasil_c'], df_mes['carga_normalizada'])
        r2_norm_m = r_norm_m ** 2
        
        resultados_mes.append({
            'mes': mes,
            'corr_abs': corr_abs_m,
            'r2_abs': r2_abs_m,
            'slope_abs': slope_abs_m,
            'corr_norm': corr_norm_m,
            'r2_norm': r2_norm_m,
            'slope_norm': slope_norm_m,
            'diff_corr': corr_norm_m - corr_abs_m,
            'diff_r2': r2_norm_m - r2_abs_m,
            'n_obs': len(df_mes)
        })

df_mes = pd.DataFrame(resultados_mes)

print(f"\n{'Mes':>4} | {'Corr ABS':>9} | {'Corr NORM':>10} | {'D Corr':>9} | {'R2 ABS':>8} | {'R2 NORM':>9} | {'D R2':>8}")
print("-"*80)
for _, row in df_mes.iterrows():
    print(f"{row['mes']:>4.0f} | {row['corr_abs']:>+8.4f} | {row['corr_norm']:>+9.4f} | {row['diff_corr']:>+8.4f} | "
          f"{row['r2_abs']:>7.4f} | {row['r2_norm']:>8.4f} | {row['diff_r2']:>+7.4f}")

# ============================================================================
# ANÁLISE CRUZADA: MÊS × HORA (NORMALIZADA)
# ============================================================================
print("\n[6/6] ANÁLISE CRUZADA MÊS × HORA (NORMALIZADA)...")

resultados_cruzados = []

for mes in range(1, 13):
    for hora in range(24):
        df_subset = df_du[(df_du['mes'] == mes) & (df_du['hora'] == hora)]
        
        if len(df_subset) >= 30:
            corr_norm = df_subset[['temp_brasil_c', 'carga_normalizada']].corr().iloc[0, 1]
            
            try:
                slope_norm, _, r_norm, p_norm, _ = stats.linregress(
                    df_subset['temp_brasil_c'], 
                    df_subset['carga_normalizada']
                )
                r2_norm = r_norm ** 2
            except:
                slope_norm, r2_norm, p_norm = 0, 0, 1
            
            resultados_cruzados.append({
                'mes': mes,
                'hora': hora,
                'corr_norm': corr_norm,
                'r2_norm': r2_norm,
                'slope_norm': slope_norm,
                'p_value': p_norm,
                'n_obs': len(df_subset)
            })

df_cruzado = pd.DataFrame(resultados_cruzados)

print(f"\n  Total de combinações: {len(df_cruzado)}")
print(f"  Com R2 > 0.3 (normalizada): {(df_cruzado['r2_norm'] > 0.3).sum()}")
print(f"  Com R2 > 0.5 (normalizada): {(df_cruzado['r2_norm'] > 0.5).sum()}")

print(f"\n[TOP 10 MAIORES R2 (NORMALIZADA)]")
print(f"{'Mes':>4} | {'Hora':>4} | {'R2':>7} | {'Slope':>10} | {'Interp':>30}")
print("-"*70)
for _, row in df_cruzado.nlargest(10, 'r2_norm').iterrows():
    interp = f"{row['slope_norm']:+.4f}/C = {row['slope_norm']*100:+.2f}%/C"
    print(f"{row['mes']:>4.0f} | {row['hora']:>4.0f} | {row['r2_norm']:>6.4f} | {row['slope_norm']:>+9.4f} | {interp:>30}")

# ============================================================================
# VISUALIZAÇÕES
# ============================================================================
print("\n" + "="*100)
print("  GERANDO VISUALIZAÇÕES...")
print("="*100)

# Figura 1: Comparação Absoluta vs Normalizada (scatter)
fig, axes = plt.subplots(2, 2, figsize=(18, 14))

# Absoluta
ax = axes[0, 0]
sample = df_du.sample(min(5000, len(df_du)), random_state=42)
ax.scatter(sample['temp_brasil_c'], sample['carga_mw'], alpha=0.3, s=10, color='steelblue')
x_line = np.linspace(df_du['temp_brasil_c'].min(), df_du['temp_brasil_c'].max(), 100)
y_line = slope_abs * x_line + intercept_abs
ax.plot(x_line, y_line, 'r-', linewidth=3, label=f'R2={r2_abs:.4f}')
ax.set_xlabel('Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('ABSOLUTA: Temperatura vs Carga', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

# Normalizada
ax = axes[0, 1]
ax.scatter(sample['temp_brasil_c'], sample['carga_normalizada'], alpha=0.3, s=10, color='darkgreen')
x_line = np.linspace(df_du['temp_brasil_c'].min(), df_du['temp_brasil_c'].max(), 100)
y_line = slope_norm * x_line + intercept_norm
ax.plot(x_line, y_line, 'r-', linewidth=3, label=f'R2={r2_norm:.4f}')
ax.set_xlabel('Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Normalizada (carga/carga_media_mes)', fontsize=12, fontweight='bold')
ax.set_title('NORMALIZADA: Temperatura vs Carga/Carga_Media_Mes', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

# Comparação por hora
ax = axes[1, 0]
x = df_hora['hora']
width = 0.35
ax.bar(x - width/2, df_hora['r2_abs'], width, label='Absoluta', alpha=0.7, color='steelblue', edgecolor='black')
ax.bar(x + width/2, df_hora['r2_norm'], width, label='Normalizada', alpha=0.7, color='darkgreen', edgecolor='black')
ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('R2', fontsize=12, fontweight='bold')
ax.set_title('Comparação R2: Absoluta vs Normalizada por Hora', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(range(0, 24, 2))

# Comparação por mês
ax = axes[1, 1]
x = df_mes['mes']
width = 0.35
ax.bar(x - width/2, df_mes['r2_abs'], width, label='Absoluta', alpha=0.7, color='steelblue', edgecolor='black')
ax.bar(x + width/2, df_mes['r2_norm'], width, label='Normalizada', alpha=0.7, color='darkgreen', edgecolor='black')
ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
ax.set_ylabel('R2', fontsize=12, fontweight='bold')
ax.set_title('Comparação R2: Absoluta vs Normalizada por Mês', fontsize=13, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')
ax.set_xticks(range(1, 13))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '27_comparacao_absoluta_vs_normalizada.png', dpi=150, bbox_inches='tight')
print(f"\n[1/3] Salvo: 27_comparacao_absoluta_vs_normalizada.png")

# Figura 2: Heatmap R2 normalizada (mês × hora)
fig, ax = plt.subplots(figsize=(14, 10))
df_pivot_norm = df_cruzado.pivot(index='hora', columns='mes', values='r2_norm')
sns.heatmap(df_pivot_norm, annot=True, fmt='.3f', cmap='RdYlGn', center=0.2,
            vmin=0, vmax=0.6, ax=ax, cbar_kws={'label': 'R2 (Normalizada)'})
ax.set_xlabel('Mês', fontsize=13, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=13, fontweight='bold')
ax.set_title('R2 Temperatura vs Carga NORMALIZADA por Mês e Hora\n(Carga dividida pela média mensal)', 
             fontsize=15, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '28_heatmap_r2_normalizada.png', dpi=150, bbox_inches='tight')
print(f"[2/3] Salvo: 28_heatmap_r2_normalizada.png")

# Figura 3: Slope normalizado (quanto % a carga muda por °C)
fig, ax = plt.subplots(figsize=(14, 10))
df_pivot_slope_norm = df_cruzado.pivot(index='hora', columns='mes', values='slope_norm')
# Converter para percentual
df_pivot_slope_norm_pct = df_pivot_slope_norm * 100

sns.heatmap(df_pivot_slope_norm_pct, annot=True, fmt='.2f', cmap='coolwarm', center=0,
            vmin=-2, vmax=2, ax=ax, cbar_kws={'label': 'Slope (%/°C)'})
ax.set_xlabel('Mês', fontsize=13, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=13, fontweight='bold')
ax.set_title('Sensibilidade: Variação % da Carga Normalizada por °C\n(positivo = temperatura alta aumenta % dessa hora)', 
             fontsize=15, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '29_heatmap_slope_normalizada_pct.png', dpi=150, bbox_inches='tight')
print(f"[3/3] Salvo: 29_heatmap_slope_normalizada_pct.png")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO FINAL: ABSOLUTA vs NORMALIZADA")
print("="*100)

print(f"""
COMPARAÇÃO GERAL:
                      ABSOLUTA    NORMALIZADA    GANHO/PERDA
  Correlação:        {corr_abs:>+8.4f}    {corr_norm:>+8.4f}      {corr_norm-corr_abs:>+8.4f}
  R2:                {r2_abs:>8.4f}    {r2_norm:>8.4f}      {r2_norm-r2_abs:>+8.4f}
  
INTERPRETAÇÃO:
  {'Normalizar MELHORA correlação!' if r2_norm > r2_abs else 'Normalizar PIORA correlação!'} 
  R2 {'aumentou' if r2_norm > r2_abs else 'diminuiu'} {abs(r2_norm-r2_abs):.4f} ({abs(r2_norm-r2_abs)*100:.1f} pontos percentuais)
  
  Slope normalizada: {slope_norm:+.4f} por °C
  Significa: Para cada 1°C, a carga normalizada muda {slope_norm*100:+.2f}%
  
MÉDIA POR HORA:
  R2 Absoluta:     {df_hora['r2_abs'].mean():.4f}
  R2 Normalizada:  {df_hora['r2_norm'].mean():.4f}
  Diferença média: {df_hora['diff_r2'].mean():+.4f}
  
MÉDIA POR MÊS:
  R2 Absoluta:     {df_mes['r2_abs'].mean():.4f}
  R2 Normalizada:  {df_mes['r2_norm'].mean():.4f}
  Diferença média: {df_mes['diff_r2'].mean():+.4f}

HORAS QUE MAIS SE BENEFICIAM DA NORMALIZAÇÃO:
""")

top_ganho = df_hora.nlargest(5, 'diff_r2')
for _, row in top_ganho.iterrows():
    print(f"  {row['hora']:>2.0f}h: R2 absoluta={row['r2_abs']:.4f} -> normalizada={row['r2_norm']:.4f} (ganho={row['diff_r2']:+.4f})")

print(f"\nMESES QUE MAIS SE BENEFICIAM DA NORMALIZACAO:")
top_ganho_mes = df_mes.nlargest(5, 'diff_r2')
for _, row in top_ganho_mes.iterrows():
    print(f"  Mes {row['mes']:>2.0f}: R2 absoluta={row['r2_abs']:.4f} -> normalizada={row['r2_norm']:.4f} (ganho={row['diff_r2']:+.4f})")

print("\n" + "="*100)
print(f"Gráficos salvos em: {OUTPUT_DIR}")
print("="*100)

# Salvar dados
df_hora.to_csv(OUTPUT_DIR / 'comparacao_abs_norm_por_hora.csv', index=False)
df_mes.to_csv(OUTPUT_DIR / 'comparacao_abs_norm_por_mes.csv', index=False)
df_cruzado.to_csv(OUTPUT_DIR / 'correlacao_temp_carga_normalizada_mes_hora.csv', index=False)
print(f"\n[OK] Dados salvos")


