"""
VERIFICAR: Correlação Temperatura×Carga Normalizada por Tipo de Dia
====================================================================

Checar se a correlação é diferente entre DU, SAB, DOM
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

print("="*100)
print("  VERIFICAR: Correlação Temp×Carga por Tipo de Dia")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# Carregar dados
df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

# Carga normalizada
df['carga_media_mes'] = df.groupby(['ano', 'mes'])['carga_mw'].transform('mean')
df['carga_normalizada'] = df['carga_mw'] / df['carga_media_mes']

print(f"\n[OK] {len(df):,} horas carregadas")

# ============================================================================
# ANÁLISE 1: CORRELAÇÃO GLOBAL POR TIPO DE DIA
# ============================================================================
print("\n[1/3] CORRELAÇÃO GLOBAL POR TIPO DE DIA...")

print(f"\n{'Tipo Dia':>8} | {'N obs':>8} | {'Corr':>8} | {'R2':>8} | {'Slope':>10}")
print("-"*55)

for tipo in ['DU', 'SAB', 'DOM']:
    df_tipo = df[df['tipo_dia_v2'] == tipo]
    
    if len(df_tipo) > 100:
        corr = df_tipo[['temp_brasil_c', 'carga_normalizada']].corr().iloc[0, 1]
        slope, _, r_val, _, _ = stats.linregress(df_tipo['temp_brasil_c'], df_tipo['carga_normalizada'])
        r2 = r_val ** 2
        
        print(f"{tipo:>8} | {len(df_tipo):>8,} | {corr:>+7.4f} | {r2:>7.4f} | {slope:>+9.4f}")

# ============================================================================
# ANÁLISE 2: CORRELAÇÃO POR MÊS E TIPO DE DIA
# ============================================================================
print("\n[2/3] CORRELAÇÃO POR MÊS E TIPO DE DIA...")

resultados = []

for mes in range(1, 13):
    for tipo in ['DU', 'SAB', 'DOM']:
        df_subset = df[(df['mes'] == mes) & (df['tipo_dia_v2'] == tipo)]
        
        if len(df_subset) >= 50:
            corr = df_subset[['temp_brasil_c', 'carga_normalizada']].corr().iloc[0, 1]
            slope, _, r_val, _, _ = stats.linregress(df_subset['temp_brasil_c'], df_subset['carga_normalizada'])
            r2 = r_val ** 2
            
            resultados.append({
                'mes': mes,
                'tipo_dia': tipo,
                'corr': corr,
                'r2': r2,
                'slope': slope,
                'n_obs': len(df_subset)
            })

df_resultados = pd.DataFrame(resultados)

# Mostrar por mês
print(f"\n{'Mes':>4} | {'DU R2':>8} | {'SAB R2':>8} | {'DOM R2':>8} | {'Dif DU-SAB':>12} | {'Dif DU-DOM':>12}")
print("-"*70)

for mes in range(1, 13):
    df_mes = df_resultados[df_resultados['mes'] == mes]
    
    r2_du = df_mes[df_mes['tipo_dia'] == 'DU']['r2'].values
    r2_sab = df_mes[df_mes['tipo_dia'] == 'SAB']['r2'].values
    r2_dom = df_mes[df_mes['tipo_dia'] == 'DOM']['r2'].values
    
    if len(r2_du) > 0 and len(r2_sab) > 0 and len(r2_dom) > 0:
        r2_du = r2_du[0]
        r2_sab = r2_sab[0]
        r2_dom = r2_dom[0]
        
        print(f"{mes:>4} | {r2_du:>7.4f} | {r2_sab:>7.4f} | {r2_dom:>7.4f} | {r2_du-r2_sab:>+11.4f} | {r2_du-r2_dom:>+11.4f}")

# ============================================================================
# ANÁLISE 3: POR HORA E TIPO DE DIA (amostra)
# ============================================================================
print("\n[3/3] EXEMPLO: CORRELAÇÃO POR HORA E TIPO DE DIA (Janeiro)...")

print(f"\n{'Hora':>4} | {'DU R2':>8} | {'SAB R2':>8} | {'DOM R2':>8}")
print("-"*40)

for hora in [0, 6, 12, 18, 23]:  # Amostra de horas
    for tipo in ['DU', 'SAB', 'DOM']:
        df_subset = df[(df['mes'] == 1) & (df['hora'] == hora) & (df['tipo_dia_v2'] == tipo)]
        
        if len(df_subset) >= 30:
            _, _, r_val, _, _ = stats.linregress(df_subset['temp_brasil_c'], df_subset['carga_normalizada'])
            r2 = r_val ** 2
        else:
            r2 = np.nan
        
        if tipo == 'DU':
            print(f"{hora:>4} | {r2:>7.4f} |", end='')
        elif tipo == 'SAB':
            print(f" {r2:>7.4f} |", end='')
        else:
            print(f" {r2:>7.4f}")

# ============================================================================
# VISUALIZAÇÃO
# ============================================================================
print("\n" + "="*100)
print("  GERANDO VISUALIZAÇÃO...")
print("="*100)

# Heatmap: R2 por mês e tipo de dia
df_pivot = df_resultados.pivot(index='mes', columns='tipo_dia', values='r2')

fig, ax = plt.subplots(figsize=(10, 10))
sns.heatmap(df_pivot, annot=True, fmt='.3f', cmap='YlOrRd', 
            vmin=0, vmax=0.6, cbar_kws={'label': 'R2'}, ax=ax)
ax.set_xlabel('Tipo de Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('Mes', fontsize=12, fontweight='bold')
ax.set_title('R2 (Temperatura vs Carga Normalizada) por Mes e Tipo de Dia', 
            fontsize=14, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '39_r2_por_mes_tipo_dia.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 39_r2_por_mes_tipo_dia.png")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*100)
print("  RESUMO: DIFERENÇAS POR TIPO DE DIA")
print("="*100)

# Calcular diferença média
df_du = df_resultados[df_resultados['tipo_dia'] == 'DU']
df_sab = df_resultados[df_resultados['tipo_dia'] == 'SAB']
df_dom = df_resultados[df_resultados['tipo_dia'] == 'DOM']

r2_medio_du = df_du['r2'].mean()
r2_medio_sab = df_sab['r2'].mean()
r2_medio_dom = df_dom['r2'].mean()

print(f"""
R2 MÉDIO (Temperatura vs Carga Normalizada):
  Dias Úteis (DU):   {r2_medio_du:.4f}
  Sábados (SAB):     {r2_medio_sab:.4f}
  Domingos (DOM):    {r2_medio_dom:.4f}

DIFERENÇAS:
  DU - SAB:  {r2_medio_du - r2_medio_sab:+.4f} ({(r2_medio_du - r2_medio_sab)/r2_medio_du*100:+.1f}%)
  DU - DOM:  {r2_medio_du - r2_medio_dom:+.4f} ({(r2_medio_du - r2_medio_dom)/r2_medio_du*100:+.1f}%)

CONCLUSÃO:
  {'As correlações SÃO SIMILARES entre tipos de dia.' if abs(r2_medio_du - r2_medio_sab) < 0.05 and abs(r2_medio_du - r2_medio_dom) < 0.05 else ''}
  {'As correlações SÃO DIFERENTES! Considere treinar regressões separadas por tipo de dia.' if abs(r2_medio_du - r2_medio_sab) >= 0.05 or abs(r2_medio_du - r2_medio_dom) >= 0.05 else ''}
  
  {'RECOMENDAÇÃO: Regressões separadas NÃO são necessárias (diferença < 5%)' if abs(r2_medio_du - r2_medio_sab) < 0.05 and abs(r2_medio_du - r2_medio_dom) < 0.05 else ''}
  {'RECOMENDAÇÃO: Considere treinar regressões separadas por tipo de dia!' if abs(r2_medio_du - r2_medio_sab) >= 0.05 or abs(r2_medio_du - r2_medio_dom) >= 0.05 else ''}
""")

print("="*100)





