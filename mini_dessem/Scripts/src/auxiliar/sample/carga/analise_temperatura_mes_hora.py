"""
ANÁLISE: TEMPERATURA vs CARGA - MÊS × HORA
============================================

Ver como a relação temperatura-carga varia por mês E hora simultaneamente
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

print("="*100)
print("  ANÁLISE: TEMPERATURA vs CARGA - MÊS × HORA")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1/3] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

# Filtrar apenas dias úteis
df_du = df[(df['tipo_dia_v2'] == 'DU')].copy()

print(f"  [OK] {len(df_du):,} horas de dias úteis")

# ============================================================================
# 2. ANÁLISE CRUZADA: MÊS × HORA
# ============================================================================
print("\n[2/3] ANÁLISE CRUZADA MÊS × HORA...")

resultados = []

for mes in range(1, 13):
    for hora in range(24):
        df_subset = df_du[(df_du['mes'] == mes) & (df_du['hora'] == hora)]
        
        if len(df_subset) >= 30:  # Mínimo de 30 observações
            corr = df_subset[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
            
            try:
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    df_subset['temp_brasil_c'], 
                    df_subset['carga_mw']
                )
                r2 = r_value ** 2
            except:
                slope, r2, p_value = 0, 0, 1
            
            resultados.append({
                'mes': mes,
                'hora': hora,
                'corr': corr,
                'r2': r2,
                'slope': slope,
                'p_value': p_value,
                'n_obs': len(df_subset),
                'carga_media': df_subset['carga_mw'].mean(),
                'temp_media': df_subset['temp_brasil_c'].mean(),
                'temp_std': df_subset['temp_brasil_c'].std(),
                'carga_std': df_subset['carga_mw'].std()
            })

df_resultados = pd.DataFrame(resultados)

print(f"\n  Total de combinações analisadas: {len(df_resultados)}")
print(f"  Combinações com boa correlação (R² > 0.5): {(df_resultados['r2'] > 0.5).sum()}")
print(f"  Combinações com correlação moderada (0.3 < R² < 0.5): {((df_resultados['r2'] > 0.3) & (df_resultados['r2'] <= 0.5)).sum()}")
print(f"  Combinações com correlação fraca (R² < 0.3): {(df_resultados['r2'] <= 0.3).sum()}")

# Top 10 maiores correlações
print(f"\n[TOP 10 MAIORES CORRELAÇÕES]")
print(f"{'Mês':>4} | {'Hora':>4} | {'Corr':>7} | {'R²':>7} | {'Slope':>12} | {'N Obs':>7} | {'Temp Média':>11}")
print("-"*75)
for _, row in df_resultados.nlargest(10, 'r2').iterrows():
    print(f"{row['mes']:>4.0f} | {row['hora']:>4.0f} | {row['corr']:>+6.4f} | {row['r2']:>6.4f} | "
          f"{row['slope']:>+11.1f} | {row['n_obs']:>7.0f} | {row['temp_media']:>9.1f}C")

# Top 10 menores correlações
print(f"\n[TOP 10 MENORES CORRELAÇÕES]")
print(f"{'Mês':>4} | {'Hora':>4} | {'Corr':>7} | {'R²':>7} | {'Slope':>12} | {'N Obs':>7} | {'Temp Média':>11}")
print("-"*75)
for _, row in df_resultados.nsmallest(10, 'r2').iterrows():
    print(f"{row['mes']:>4.0f} | {row['hora']:>4.0f} | {row['corr']:>+6.4f} | {row['r2']:>6.4f} | "
          f"{row['slope']:>+11.1f} | {row['n_obs']:>7.0f} | {row['temp_media']:>9.1f}C")

# ============================================================================
# 3. VISUALIZAÇÕES
# ============================================================================
print("\n[3/3] GERANDO VISUALIZAÇÕES...")

# Criar matrizes para heatmaps
df_pivot_corr = df_resultados.pivot(index='hora', columns='mes', values='corr')
df_pivot_r2 = df_resultados.pivot(index='hora', columns='mes', values='r2')
df_pivot_slope = df_resultados.pivot(index='hora', columns='mes', values='slope')

# Figura 1: Heatmap de Correlação
fig, axes = plt.subplots(2, 2, figsize=(20, 16))

# Subplot 1: Correlação
ax = axes[0, 0]
sns.heatmap(df_pivot_corr, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
            vmin=-1, vmax=1, ax=ax, cbar_kws={'label': 'Correlação'})
ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_title('Correlação Temperatura-Carga por Mês e Hora', fontsize=14, fontweight='bold')

# Subplot 2: R²
ax = axes[0, 1]
sns.heatmap(df_pivot_r2, annot=True, fmt='.2f', cmap='YlOrRd',
            vmin=0, vmax=1, ax=ax, cbar_kws={'label': 'R²'})
ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_title('R² (Poder Explicativo) por Mês e Hora', fontsize=14, fontweight='bold')

# Subplot 3: Slope (sensibilidade)
ax = axes[1, 0]
sns.heatmap(df_pivot_slope, annot=False, fmt='.0f', cmap='coolwarm', center=0,
            ax=ax, cbar_kws={'label': 'Slope (MW/°C)'})
ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_title('Sensibilidade (MW/°C) por Mês e Hora', fontsize=14, fontweight='bold')

# Subplot 4: Número de observações
df_pivot_n = df_resultados.pivot(index='hora', columns='mes', values='n_obs')
ax = axes[1, 1]
sns.heatmap(df_pivot_n, annot=True, fmt='.0f', cmap='Blues',
            ax=ax, cbar_kws={'label': 'N Observações'})
ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_title('Número de Observações por Mês e Hora', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '23_heatmap_mes_hora_correlacao.png', dpi=150, bbox_inches='tight')
print(f"\n[1/4] Salvo: 23_heatmap_mes_hora_correlacao.png")

# Figura 2: Heatmap de R² com anotações de significância
fig, ax = plt.subplots(figsize=(14, 10))

# Criar máscara para p-value > 0.05 (não significativo)
df_pivot_pvalue = df_resultados.pivot(index='hora', columns='mes', values='p_value')
mask = df_pivot_pvalue > 0.05

sns.heatmap(df_pivot_r2, annot=True, fmt='.3f', cmap='RdYlGn', center=0.3,
            vmin=0, vmax=0.8, ax=ax, cbar_kws={'label': 'R²'},
            linewidths=0.5, linecolor='gray')

# Adicionar X para células não significativas
for i in range(len(df_pivot_r2)):
    for j in range(len(df_pivot_r2.columns)):
        if mask.iloc[i, j]:
            ax.text(j + 0.5, i + 0.7, 'n.s.', ha='center', va='center', 
                   fontsize=7, color='red', fontweight='bold')

ax.set_xlabel('Mês', fontsize=13, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=13, fontweight='bold')
ax.set_title('R² Temperatura-Carga por Mês e Hora\n(n.s. = não significativo, p>0.05)', 
             fontsize=15, fontweight='bold', pad=15)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '24_heatmap_r2_com_significancia.png', dpi=150, bbox_inches='tight')
print(f"[2/4] Salvo: 24_heatmap_r2_com_significancia.png")

# Figura 3: Gráficos de linha - evolução por mês para horas selecionadas
fig, axes = plt.subplots(2, 2, figsize=(18, 12))

horas_interesse = [0, 6, 12, 18]  # Meia-noite, manhã, meio-dia, noite
titulos = ['0h (Madrugada)', '6h (Manhã)', '12h (Meio-dia)', '18h (Noite)']

for idx, (hora, titulo) in enumerate(zip(horas_interesse, titulos)):
    ax = axes[idx // 2, idx % 2]
    
    df_hora = df_resultados[df_resultados['hora'] == hora].sort_values('mes')
    
    ax2 = ax.twinx()
    
    line1 = ax.plot(df_hora['mes'], df_hora['r2'], 'o-', linewidth=3, markersize=10,
                    color='red', label='R²', alpha=0.8)
    line2 = ax2.plot(df_hora['mes'], df_hora['slope'], 's-', linewidth=3, markersize=10,
                     color='blue', label='Slope (MW/C)', alpha=0.8)
    
    ax.set_xlabel('Mês', fontsize=11, fontweight='bold')
    ax.set_ylabel('R²', fontsize=11, fontweight='bold', color='red')
    ax2.set_ylabel('Slope (MW/C)', fontsize=11, fontweight='bold', color='blue')
    ax.set_title(titulo, fontsize=13, fontweight='bold')
    ax.set_xticks(range(1, 13))
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='y', labelcolor='red')
    ax2.tick_params(axis='y', labelcolor='blue')
    
    # Combinar legendas
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, fontsize=10, loc='upper left')

plt.suptitle('Evolução Mensal da Relação Temperatura-Carga por Hora', 
             fontsize=15, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '25_evolucao_mensal_por_hora.png', dpi=150, bbox_inches='tight')
print(f"[3/4] Salvo: 25_evolucao_mensal_por_hora.png")

# Figura 4: Gráficos de linha - evolução por hora para meses selecionados
fig, axes = plt.subplots(2, 2, figsize=(18, 12))

meses_interesse = [1, 4, 7, 10]  # Jan (verão), Abr (outono), Jul (inverno), Out (primavera)
titulos_meses = ['Janeiro (Verão)', 'Abril (Outono)', 'Julho (Inverno)', 'Outubro (Primavera)']

for idx, (mes, titulo) in enumerate(zip(meses_interesse, titulos_meses)):
    ax = axes[idx // 2, idx % 2]
    
    df_mes = df_resultados[df_resultados['mes'] == mes].sort_values('hora')
    
    ax2 = ax.twinx()
    
    line1 = ax.plot(df_mes['hora'], df_mes['r2'], 'o-', linewidth=3, markersize=8,
                    color='red', label='R²', alpha=0.8)
    line2 = ax2.plot(df_mes['hora'], df_mes['slope'], 's-', linewidth=3, markersize=8,
                     color='blue', label='Slope (MW/C)', alpha=0.8)
    
    ax.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
    ax.set_ylabel('R²', fontsize=11, fontweight='bold', color='red')
    ax2.set_ylabel('Slope (MW/C)', fontsize=11, fontweight='bold', color='blue')
    ax.set_title(titulo, fontsize=13, fontweight='bold')
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='y', labelcolor='red')
    ax2.tick_params(axis='y', labelcolor='blue')
    
    # Combinar legendas
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, fontsize=10, loc='upper left')

plt.suptitle('Evolução Diária da Relação Temperatura-Carga por Mês', 
             fontsize=15, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '26_evolucao_diaria_por_mes.png', dpi=150, bbox_inches='tight')
print(f"[4/4] Salvo: 26_evolucao_diaria_por_mes.png")

# ============================================================================
# ANÁLISE ESTATÍSTICA
# ============================================================================
print("\n" + "="*100)
print("  RESUMO ESTATÍSTICO: MÊS × HORA")
print("="*100)

# Estatísticas gerais
print(f"\nR² GERAL:")
print(f"  Média:    {df_resultados['r2'].mean():.4f}")
print(f"  Mediana:  {df_resultados['r2'].median():.4f}")
print(f"  Std:      {df_resultados['r2'].std():.4f}")
print(f"  Min:      {df_resultados['r2'].min():.4f}")
print(f"  Max:      {df_resultados['r2'].max():.4f}")

# Por período do dia
periodos = {
    'Madrugada (0-5h)': df_resultados[df_resultados['hora'].isin([0,1,2,3,4,5])],
    'Manhã (6-11h)': df_resultados[df_resultados['hora'].isin([6,7,8,9,10,11])],
    'Tarde (12-17h)': df_resultados[df_resultados['hora'].isin([12,13,14,15,16,17])],
    'Noite (18-23h)': df_resultados[df_resultados['hora'].isin([18,19,20,21,22,23])]
}

print(f"\nR² MÉDIO POR PERÍODO DO DIA:")
for periodo, df_periodo in periodos.items():
    print(f"  {periodo:20s}: {df_periodo['r2'].mean():.4f}")

# Por estação
estacoes = {
    'Verão (Dez-Fev)': df_resultados[df_resultados['mes'].isin([12, 1, 2])],
    'Outono (Mar-Mai)': df_resultados[df_resultados['mes'].isin([3, 4, 5])],
    'Inverno (Jun-Ago)': df_resultados[df_resultados['mes'].isin([6, 7, 8])],
    'Primavera (Set-Nov)': df_resultados[df_resultados['mes'].isin([9, 10, 11])]
}

print(f"\nR² MÉDIO POR ESTAÇÃO:")
for estacao, df_estacao in estacoes.items():
    print(f"  {estacao:25s}: {df_estacao['r2'].mean():.4f}")

# Melhores e piores combinações
print(f"\n[TOP 5 COMBINAÇÕES - MAIOR R²]")
top5 = df_resultados.nlargest(5, 'r2')
for idx, row in top5.iterrows():
    print(f"  Mês {row['mes']:>2.0f}, Hora {row['hora']:>2.0f}h: R²={row['r2']:.4f}, Slope={row['slope']:>+7.1f} MW/C")

print(f"\n[TOP 5 COMBINAÇÕES - MENOR R²]")
bottom5 = df_resultados.nsmallest(5, 'r2')
for idx, row in bottom5.iterrows():
    print(f"  Mês {row['mes']:>2.0f}, Hora {row['hora']:>2.0f}h: R²={row['r2']:.4f}, Slope={row['slope']:>+7.1f} MW/C")

# Padrões identificados
print(f"\n[PADRÕES IDENTIFICADOS]")

# Hora com maior R² médio
r2_por_hora = df_resultados.groupby('hora')['r2'].mean()
melhor_hora = r2_por_hora.idxmax()
print(f"  Melhor hora (R² médio): {melhor_hora:.0f}h (R²={r2_por_hora.max():.4f})")

# Mês com maior R² médio
r2_por_mes = df_resultados.groupby('mes')['r2'].mean()
melhor_mes = r2_por_mes.idxmax()
print(f"  Melhor mês (R² médio):  {melhor_mes:.0f} (R²={r2_por_mes.max():.4f})")

# Hora com menor R² médio
pior_hora = r2_por_hora.idxmin()
print(f"  Pior hora (R² médio):   {pior_hora:.0f}h (R²={r2_por_hora.min():.4f})")

# Mês com menor R² médio
pior_mes = r2_por_mes.idxmin()
print(f"  Pior mês (R² médio):    {pior_mes:.0f} (R²={r2_por_mes.min():.4f})")

print("\n" + "="*100)
print(f"Gráficos salvos em: {OUTPUT_DIR}")
print("="*100)

# Salvar dados
df_resultados.to_csv(OUTPUT_DIR / 'correlacao_temp_carga_mes_hora.csv', index=False)
print(f"\n[OK] Dados salvos: correlacao_temp_carga_mes_hora.csv")





