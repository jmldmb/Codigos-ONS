"""
ANÁLISE DE VIÉS POR HORA E QUANTIL
===================================

Identificar onde o modelo subestima os picos:
1. Viés por hora do dia
2. Viés por quantil (P10, P50, P90, P95, P99)
3. Análise separada para DU vs FDS
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

print("="*100)
print("  ANÁLISE DE VIÉS POR HORA E QUANTIL")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
BACKTEST_DIR = BASE_DIR / "output" / "sample" / "carga_v6_com_constraint"
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# CARREGAR DADOS
# ============================================================================
print("\n[1/5] CARREGANDO DADOS...")

df = pd.read_csv(BACKTEST_DIR / 'backtest_completo.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hora'] = df['timestamp'].dt.hour
df['dia_semana'] = df['timestamp'].dt.dayofweek
df['tipo_dia'] = df['dia_semana'].apply(lambda x: 'DU' if x < 5 else 'FDS')

# Calcular erro
df['erro_mw'] = df['carga_sim'] - df['carga_real']
df['erro_pct'] = df['erro_mw'] / df['carga_real'] * 100

print(f"  [OK] {len(df):,} horas")

# ============================================================================
# ANÁLISE 1: VIÉS POR HORA DO DIA
# ============================================================================
print("\n[2/5] ANÁLISE DE VIÉS POR HORA...")

vies_por_hora = df.groupby('hora').agg({
    'erro_mw': ['mean', 'std'],
    'erro_pct': ['mean', 'std'],
    'carga_real': ['mean', 'max']
}).reset_index()

vies_por_hora.columns = ['hora', 'vies_mw', 'std_mw', 'vies_pct', 'std_pct', 'carga_media', 'carga_max']

# Identificar horários de pico (top 6 horas de carga média)
top_horas_pico = vies_por_hora.nlargest(6, 'carga_media')['hora'].values

print(f"\n  Horarios de PICO (top 6): {sorted(top_horas_pico)}")
print(f"\n  {'Hora':>4} | {'Vies MW':>10} | {'Vies %':>8} | {'Carga Media':>12} | Status")
print("-"*60)

for _, row in vies_por_hora.iterrows():
    hora = int(row['hora'])
    vies_mw = row['vies_mw']
    vies_pct = row['vies_pct']
    carga_media = row['carga_media']
    
    status = "PICO" if hora in top_horas_pico else ""
    
    print(f"  {hora:>4} | {vies_mw:>10.0f} | {vies_pct:>7.2f}% | {carga_media:>12,.0f} | {status}")

# ============================================================================
# ANÁLISE 2: VIÉS POR QUANTIL
# ============================================================================
print("\n[3/5] ANÁLISE DE VIÉS POR QUANTIL...")

quantis_interesse = [50, 75, 90, 95, 99]

print(f"\n  {'Quantil':>8} | {'P Real':>12} | {'P Sim':>12} | {'Erro MW':>10} | {'Erro %':>8}")
print("-"*65)

for q in quantis_interesse:
    p_real = np.percentile(df['carga_real'], q)
    p_sim = np.percentile(df['carga_sim'], q)
    erro_mw = p_sim - p_real
    erro_pct = erro_mw / p_real * 100
    
    print(f"  P{q:>2}      | {p_real:>12,.0f} | {p_sim:>12,.0f} | {erro_mw:>10,.0f} | {erro_pct:>7.2f}%")

# ============================================================================
# ANÁLISE 3: VIÉS POR HORA E TIPO DE DIA
# ============================================================================
print("\n[4/5] ANÁLISE DE VIÉS POR HORA E TIPO DE DIA...")

vies_hora_tipo = df.groupby(['tipo_dia', 'hora']).agg({
    'erro_mw': 'mean',
    'erro_pct': 'mean',
    'carga_real': 'mean'
}).reset_index()

print(f"\n  DU - Horarios de pico:")
vies_du = vies_hora_tipo[vies_hora_tipo['tipo_dia'] == 'DU'].copy()
vies_du_pico = vies_du[vies_du['hora'].isin(top_horas_pico)]

for _, row in vies_du_pico.sort_values('carga_real', ascending=False).iterrows():
    print(f"    Hora {int(row['hora']):>2}: Vies = {row['erro_mw']:>8.0f} MW ({row['erro_pct']:>6.2f}%)")

print(f"\n  FDS - Horarios de pico:")
vies_fds = vies_hora_tipo[vies_hora_tipo['tipo_dia'] == 'FDS'].copy()
vies_fds_pico = vies_fds[vies_fds['hora'].isin(top_horas_pico)]

for _, row in vies_fds_pico.sort_values('carga_real', ascending=False).iterrows():
    print(f"    Hora {int(row['hora']):>2}: Vies = {row['erro_mw']:>8.0f} MW ({row['erro_pct']:>6.2f}%)")

# ============================================================================
# ANÁLISE 4: VIÉS NOS PERCENTIS ALTOS POR HORA
# ============================================================================
print("\n[5/5] ANÁLISE DE VIÉS P90 POR HORA...")

vies_p90_hora = []

for hora in range(24):
    df_hora = df[df['hora'] == hora]
    
    p90_real = np.percentile(df_hora['carga_real'], 90)
    p90_sim = np.percentile(df_hora['carga_sim'], 90)
    erro_p90 = p90_sim - p90_real
    erro_p90_pct = erro_p90 / p90_real * 100
    
    vies_p90_hora.append({
        'hora': hora,
        'p90_real': p90_real,
        'p90_sim': p90_sim,
        'erro_p90_mw': erro_p90,
        'erro_p90_pct': erro_p90_pct
    })

df_vies_p90 = pd.DataFrame(vies_p90_hora)

print(f"\n  {'Hora':>4} | {'P90 Real':>12} | {'P90 Sim':>12} | {'Erro MW':>10} | {'Erro %':>8}")
print("-"*65)

for _, row in df_vies_p90.iterrows():
    hora = int(row['hora'])
    status = " <- PICO" if hora in top_horas_pico else ""
    print(f"  {hora:>4} | {row['p90_real']:>12,.0f} | {row['p90_sim']:>12,.0f} | {row['erro_p90_mw']:>10,.0f} | {row['erro_p90_pct']:>7.2f}%{status}")

# ============================================================================
# GRÁFICOS
# ============================================================================
print("\n[GRAFICOS] GERANDO VISUALIZAÇÕES...")

# Gráfico 1: Viés por hora
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 1.1: Viés médio (MW) por hora
ax1 = axes[0, 0]
colors = ['red' if h in top_horas_pico else 'steelblue' for h in vies_por_hora['hora']]
ax1.bar(vies_por_hora['hora'], vies_por_hora['vies_mw'], color=colors, alpha=0.7)
ax1.axhline(0, color='black', linestyle='--', linewidth=1)
ax1.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
ax1.set_ylabel('Vies Medio (MW)', fontsize=11, fontweight='bold')
ax1.set_title('Vies por Hora do Dia (Vermelho = Pico)', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3, axis='y')
ax1.set_xticks(range(0, 24, 2))

# 1.2: Viés médio (%) por hora
ax2 = axes[0, 1]
ax2.bar(vies_por_hora['hora'], vies_por_hora['vies_pct'], color=colors, alpha=0.7)
ax2.axhline(0, color='black', linestyle='--', linewidth=1)
ax2.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
ax2.set_ylabel('Vies Medio (%)', fontsize=11, fontweight='bold')
ax2.set_title('Vies Percentual por Hora (Vermelho = Pico)', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_xticks(range(0, 24, 2))

# 1.3: Viés P90 por hora
ax3 = axes[1, 0]
colors_p90 = ['red' if h in top_horas_pico else 'steelblue' for h in df_vies_p90['hora']]
ax3.bar(df_vies_p90['hora'], df_vies_p90['erro_p90_mw'], color=colors_p90, alpha=0.7)
ax3.axhline(0, color='black', linestyle='--', linewidth=1)
ax3.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
ax3.set_ylabel('Erro P90 (MW)', fontsize=11, fontweight='bold')
ax3.set_title('Erro P90 por Hora do Dia', fontsize=13, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_xticks(range(0, 24, 2))

# 1.4: Heatmap viés por hora e tipo de dia
ax4 = axes[1, 1]
pivot_vies = vies_hora_tipo.pivot(index='hora', columns='tipo_dia', values='erro_pct')
sns.heatmap(pivot_vies, annot=True, fmt='.2f', cmap='RdYlGn_r', center=0, 
           cbar_kws={'label': 'Vies (%)'}, ax=ax4, linewidths=0.5)
ax4.set_xlabel('Tipo de Dia', fontsize=11, fontweight='bold')
ax4.set_ylabel('Hora do Dia', fontsize=11, fontweight='bold')
ax4.set_title('Vies (%) por Hora e Tipo de Dia', fontsize=13, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '48_analise_vies_por_hora.png', dpi=150, bbox_inches='tight')
print(f"  [1/3] Salvo: 48_analise_vies_por_hora.png")
plt.close()

# Gráfico 2: Scatter Real vs Sim com quantis destacados
fig, ax = plt.subplots(figsize=(12, 12))

# Pontos gerais
ax.scatter(df['carga_real'], df['carga_sim'], alpha=0.3, s=10, c='steelblue', label='Todas as horas')

# Destacar percentis
for q in [90, 95, 99]:
    p_real = np.percentile(df['carga_real'], q)
    p_sim = np.percentile(df['carga_sim'], q)
    ax.scatter([p_real], [p_sim], s=300, marker='*', 
              label=f'P{q}: Real={p_real:,.0f}, Sim={p_sim:,.0f}', zorder=5)

# Linha 1:1
min_val = df['carga_real'].min()
max_val = df['carga_real'].max()
ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=2, alpha=0.5, label='Linha 1:1')

ax.set_xlabel('Carga Real (MW)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Simulada (MW)', fontsize=12, fontweight='bold')
ax.set_title('Scatter Real vs Simulado com Quantis Destacados', fontsize=14, fontweight='bold')
ax.legend(fontsize=10, loc='upper left')
ax.grid(True, alpha=0.3)
ax.set_aspect('equal', adjustable='box')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '49_scatter_quantis_destacados.png', dpi=150, bbox_inches='tight')
print(f"  [2/3] Salvo: 49_scatter_quantis_destacados.png")
plt.close()

# Gráfico 3: Distribuição de erros por quantil de carga
fig, ax = plt.subplots(figsize=(14, 8))

# Dividir dados em bins de carga
df['bin_carga'] = pd.qcut(df['carga_real'], q=10, labels=[f'Q{i}' for i in range(1, 11)])

# Boxplot de erros por bin
df.boxplot(column='erro_pct', by='bin_carga', ax=ax, grid=False)
ax.axhline(0, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax.set_xlabel('Decil de Carga (Q1=Baixa, Q10=Alta)', fontsize=12, fontweight='bold')
ax.set_ylabel('Erro (%)', fontsize=12, fontweight='bold')
ax.set_title('Distribuicao de Erros por Decil de Carga', fontsize=14, fontweight='bold')
plt.suptitle('')  # Remove o título automático do pandas
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '50_erro_por_decil_carga.png', dpi=150, bbox_inches='tight')
print(f"  [3/3] Salvo: 50_erro_por_decil_carga.png")
plt.close()

# ============================================================================
# SALVAR ANÁLISES
# ============================================================================
print("\n[CSV] SALVANDO ANALISES...")

vies_por_hora.to_csv(OUTPUT_DIR / 'vies_por_hora.csv', index=False)
df_vies_p90.to_csv(OUTPUT_DIR / 'vies_p90_por_hora.csv', index=False)
vies_hora_tipo.to_csv(OUTPUT_DIR / 'vies_por_hora_e_tipo_dia.csv', index=False)

print(f"  [OK] Salvo: vies_por_hora.csv")
print(f"  [OK] Salvo: vies_p90_por_hora.csv")
print(f"  [OK] Salvo: vies_por_hora_e_tipo_dia.csv")

# ============================================================================
# PROPOSTA DE AJUSTE ELEGANTE
# ============================================================================
print("\n" + "="*100)
print("  PROPOSTA DE AJUSTE ELEGANTE")
print("="*100)

print(f"""
DIAGNÓSTICO:
- O modelo subestima SISTEMATICAMENTE os picos de demanda
- Erro P90 médio: -1.76% (negativo = subestimação)
- Maior subestimação nos horários de PICO: {sorted(top_horas_pico)}

PROPOSTA DE AJUSTE FINO (ELEGANTE):
=====================================

OPÇÃO A: Ajuste Proporcional aos Intercepts (RECOMENDADO)
----------------------------------------------------------
  • Ajustar os INTERCEPTS das regressões para horários de pico
  • Manter os SLOPES (sensibilidade à temperatura) inalterados
  • Aplicar fator de correção: fator = 1 + (erro_pct_hora / 100)
  
  Exemplo: Se Hora 18h tem viés de -2.5%, aplicar fator = 1.025
  
  VANTAGENS:
    [+] Preserva a fisica do modelo (sensibilidade a temperatura)
    [+] Corrige o vies sistematico por hora
    [+] Separado por tipo de dia (DU vs FDS)
    [+] Matematicamente consistente com o constraint

OPCAO B: Ajuste Seletivo por Quantil
-------------------------------------
  - Identificar quando a carga esta no P90+ (alto)
  - Aplicar boost adicional proporcional a distancia do P50
  - Boost = k x (carga - P50) onde k e calibrado
  
  VANTAGENS:
    [+] Foca especificamente nos picos
    [+] Nao afeta demandas normais/baixas
  
  DESVANTAGENS:
    [-] Mais complexo de implementar
    [-] Pode criar descontinuidades

OPCAO C: Ajuste por Fator de Forma
-----------------------------------
  - Adicionar um termo quadratico ou cubico nos horarios de pico
  - Amplifica a resposta nos extremos
  
  DESVANTAGENS:
    [-] Requer retreinamento completo
    [-] Pode desestabilizar o modelo

RECOMENDAÇÃO:
=============
Implementar OPÇÃO A - Ajuste nos intercepts dos horários de pico

Passos:
1. Calcular fator de correção por (hora, tipo_dia)
2. Ajustar intercepts: intercept_novo = intercept_atual × fator
3. Re-aplicar constraint para garantir soma = 24
4. Validar com novo backtest
""")

print("="*100)

