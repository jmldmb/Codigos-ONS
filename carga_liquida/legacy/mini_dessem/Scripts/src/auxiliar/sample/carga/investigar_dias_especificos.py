"""
INVESTIGAÇÃO DETALHADA DE DIAS ESPECÍFICOS
===========================================

Analisar o que acontece em dias específicos onde o modelo erra mais
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns
from datetime import datetime, timedelta

print("="*100)
print("  INVESTIGACAO DETALHADA: 21-24 JANEIRO 2025")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
BACKTEST_DIR = BASE_DIR / "output" / "sample" / "carga_v6_com_constraint"
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"
DATA_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# CARREGAR DADOS
# ============================================================================
print("\n[1/4] CARREGANDO DADOS...")

df_backtest = pd.read_csv(BACKTEST_DIR / 'backtest_completo.csv')
df_backtest['timestamp'] = pd.to_datetime(df_backtest['timestamp'])
df_backtest['data'] = df_backtest['timestamp'].dt.date
df_backtest['hora'] = df_backtest['timestamp'].dt.hour
df_backtest['dia_semana'] = df_backtest['timestamp'].dt.dayofweek
df_backtest['tipo_dia'] = df_backtest['dia_semana'].apply(lambda x: 'DU' if x < 5 else 'FDS')

# Calcular erro
df_backtest['erro_mw'] = df_backtest['carga_sim'] - df_backtest['carga_real']
df_backtest['erro_pct'] = df_backtest['erro_mw'] / df_backtest['carga_real'] * 100

print(f"  [OK] {len(df_backtest):,} horas carregadas")

# Carregar dados completos (com temperatura)
df_completo = pd.read_parquet(DATA_DIR / 'dados_processados_mai2023_com_feriados.parquet')
df_completo['data'] = df_completo['timestamp'].dt.date

print(f"  [OK] {len(df_completo):,} horas com temperatura")

# ============================================================================
# FILTRAR PERÍODO DE INTERESSE
# ============================================================================
print("\n[2/4] ANALISANDO PERIODO 21-24 JAN 2025...")

data_inicio = pd.to_datetime('2025-01-21').date()
data_fim = pd.to_datetime('2025-01-24').date()

df_periodo = df_backtest[
    (df_backtest['data'] >= data_inicio) & 
    (df_backtest['data'] <= data_fim)
].copy()

df_temp_periodo = df_completo[
    (df_completo['data'] >= data_inicio) & 
    (df_completo['data'] <= data_fim)
].copy()

print(f"\n  RESUMO DO PERIODO:")
print(f"  {'Data':>12} | {'Dia':>10} | {'Tipo':>4} | {'MAPE':>7} | {'Erro Medio':>12}")
print("-"*60)

for data in pd.date_range(data_inicio, data_fim):
    df_dia = df_periodo[df_periodo['data'] == data.date()]
    
    if len(df_dia) > 0:
        mape = df_dia['erro_pct'].abs().mean()
        erro_medio = df_dia['erro_mw'].mean()
        dia_semana = data.strftime('%A')
        tipo_dia = df_dia['tipo_dia'].iloc[0]
        
        print(f"  {data.date()} | {dia_semana:>10} | {tipo_dia:>4} | {mape:>6.2f}% | {erro_medio:>12,.0f} MW")

# Comparar com todo janeiro 2025
df_jan2025 = df_backtest[
    (df_backtest['timestamp'].dt.year == 2025) & 
    (df_backtest['timestamp'].dt.month == 1)
]

mape_jan = df_jan2025['erro_pct'].abs().mean()
mape_periodo = df_periodo['erro_pct'].abs().mean()

print(f"\n  COMPARACAO:")
print(f"    MAPE Janeiro 2025 (completo): {mape_jan:.2f}%")
print(f"    MAPE Periodo 21-24 Jan:       {mape_periodo:.2f}%")
print(f"    Diferenca:                    {mape_periodo - mape_jan:+.2f}%")

# ============================================================================
# ANÁLISE DE TEMPERATURA
# ============================================================================
print("\n[3/4] ANALISANDO TEMPERATURA...")

# Temperatura média de janeiro 2025
df_temp_jan = df_completo[
    (df_completo['timestamp'].dt.year == 2025) & 
    (df_completo['timestamp'].dt.month == 1)
]

temp_media_jan = df_temp_jan['temp_brasil_c'].mean()
temp_std_jan = df_temp_jan['temp_brasil_c'].std()

print(f"\n  TEMPERATURA JANEIRO 2025:")
print(f"    Media:      {temp_media_jan:.2f} C")
print(f"    Desvio:     {temp_std_jan:.2f} C")
print(f"    Min:        {df_temp_jan['temp_brasil_c'].min():.2f} C")
print(f"    Max:        {df_temp_jan['temp_brasil_c'].max():.2f} C")

print(f"\n  TEMPERATURA PERIODO 21-24 JAN:")
for data in pd.date_range(data_inicio, data_fim):
    df_dia_temp = df_temp_periodo[df_temp_periodo['data'] == data.date()]
    
    if len(df_dia_temp) > 0:
        temp_dia = df_dia_temp['temp_brasil_c'].mean()
        temp_min = df_dia_temp['temp_brasil_c'].min()
        temp_max = df_dia_temp['temp_brasil_c'].max()
        
        desvio = temp_dia - temp_media_jan
        n_desvios = desvio / temp_std_jan if temp_std_jan > 0 else 0
        
        anomalia = "NORMAL"
        if abs(n_desvios) > 1.5:
            anomalia = "ANOMALO!"
        elif abs(n_desvios) > 1.0:
            anomalia = "Atipico"
        
        print(f"    {data.date()}: {temp_dia:>6.2f} C (min={temp_min:>5.2f}, max={temp_max:>5.2f}) | Desvio={desvio:>+6.2f} C ({n_desvios:>+4.1f} std) | {anomalia}")

# ============================================================================
# GRÁFICOS DETALHADOS
# ============================================================================
print("\n[4/4] GERANDO GRAFICOS DETALHADOS...")

# Gráfico 1: Série temporal do período
fig, axes = plt.subplots(3, 1, figsize=(18, 14))

# 1.1: Carga Real vs Simulado
ax1 = axes[0]
ax1.plot(df_periodo['timestamp'], df_periodo['carga_real'], 
        label='Real', color='blue', linewidth=2.5, marker='o', markersize=4)
ax1.plot(df_periodo['timestamp'], df_periodo['carga_sim'], 
        label='Simulado', color='green', linewidth=2.5, marker='s', markersize=4, linestyle='--')

# Destacar dias da semana
for data in pd.date_range(data_inicio, data_fim):
    df_dia = df_periodo[df_periodo['data'] == data.date()]
    if len(df_dia) > 0:
        tipo = df_dia['tipo_dia'].iloc[0]
        cor = 'lightblue' if tipo == 'DU' else 'lightcoral'
        ax1.axvspan(df_dia['timestamp'].min(), df_dia['timestamp'].max(), 
                   alpha=0.2, color=cor, label=f'{data.strftime("%d/%m")} - {tipo}' if data.date() == data_inicio else "")

ax1.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax1.set_title('Periodo 21-24 Janeiro 2025: Real vs Simulado', fontsize=14, fontweight='bold')
ax1.legend(fontsize=10, loc='upper right')
ax1.grid(True, alpha=0.3)
ax1.set_xticklabels([])

# 1.2: Erro (MW)
ax2 = axes[1]
colors = ['red' if e < 0 else 'green' for e in df_periodo['erro_mw']]
ax2.bar(df_periodo['timestamp'], df_periodo['erro_mw'], color=colors, alpha=0.6, width=0.03)
ax2.axhline(0, color='black', linestyle='-', linewidth=1)
ax2.set_ylabel('Erro (MW)', fontsize=12, fontweight='bold')
ax2.set_title('Erro por Hora (Negativo = Subestima)', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_xticklabels([])

# 1.3: Temperatura
if len(df_temp_periodo) > 0:
    ax3 = axes[2]
    ax3.plot(df_temp_periodo['timestamp'], df_temp_periodo['temp_brasil_c'], 
            color='orangered', linewidth=2.5, marker='o', markersize=4, label='Temperatura')
    ax3.axhline(temp_media_jan, color='blue', linestyle='--', linewidth=2, 
               alpha=0.7, label=f'Media Jan ({temp_media_jan:.1f} C)')
    ax3.fill_between(df_temp_periodo['timestamp'], 
                     temp_media_jan - temp_std_jan, 
                     temp_media_jan + temp_std_jan,
                     alpha=0.2, color='blue', label='1 std')
    
    ax3.set_xlabel('Data/Hora', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Temperatura (C)', fontsize=12, fontweight='bold')
    ax3.set_title('Temperatura ao Longo do Periodo', fontsize=13, fontweight='bold')
    ax3.legend(fontsize=10, loc='best')
    ax3.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '51_investigacao_21_24_jan_2025.png', dpi=150, bbox_inches='tight')
print(f"  [1/3] Salvo: 51_investigacao_21_24_jan_2025.png")
plt.close()

# Gráfico 2: Perfil horário médio do período vs Janeiro completo
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 2.1: Perfil horário de carga
ax1 = axes[0, 0]
perfil_periodo = df_periodo.groupby('hora').agg({
    'carga_real': 'mean',
    'carga_sim': 'mean'
}).reset_index()

perfil_jan = df_jan2025.groupby('hora').agg({
    'carga_real': 'mean',
    'carga_sim': 'mean'
}).reset_index()

ax1.plot(perfil_periodo['hora'], perfil_periodo['carga_real'], 
        label='Real (21-24 Jan)', color='blue', linewidth=2.5, marker='o')
ax1.plot(perfil_periodo['hora'], perfil_periodo['carga_sim'], 
        label='Simulado (21-24 Jan)', color='green', linewidth=2.5, marker='s', linestyle='--')
ax1.plot(perfil_jan['hora'], perfil_jan['carga_real'], 
        label='Real (Jan completo)', color='lightblue', linewidth=2, alpha=0.6)
ax1.plot(perfil_jan['hora'], perfil_jan['carga_sim'], 
        label='Simulado (Jan completo)', color='lightgreen', linewidth=2, alpha=0.6, linestyle='--')

ax1.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
ax1.set_ylabel('Carga Media (MW)', fontsize=11, fontweight='bold')
ax1.set_title('Perfil Horario: Periodo vs Janeiro Completo', fontsize=13, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_xticks(range(0, 24, 2))

# 2.2: Erro por hora
ax2 = axes[0, 1]
erro_hora_periodo = df_periodo.groupby('hora')['erro_mw'].mean()
erro_hora_jan = df_jan2025.groupby('hora')['erro_mw'].mean()

x = np.arange(24)
width = 0.35

ax2.bar(x - width/2, erro_hora_periodo, width, label='21-24 Jan', alpha=0.7, color='red')
ax2.bar(x + width/2, erro_hora_jan, width, label='Jan completo', alpha=0.7, color='orange')
ax2.axhline(0, color='black', linestyle='-', linewidth=1)

ax2.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
ax2.set_ylabel('Erro Medio (MW)', fontsize=11, fontweight='bold')
ax2.set_title('Erro por Hora: Periodo vs Janeiro', fontsize=13, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_xticks(range(0, 24, 2))

# 2.3: Perfil de temperatura
ax3 = axes[1, 0]
if len(df_temp_periodo) > 0:
    perfil_temp_periodo = df_temp_periodo.groupby('hora')['temp_brasil_c'].mean()
    perfil_temp_jan = df_temp_jan.groupby('hora')['temp_brasil_c'].mean()
    
    ax3.plot(perfil_temp_periodo.index, perfil_temp_periodo.values, 
            label='21-24 Jan', color='orangered', linewidth=2.5, marker='o')
    ax3.plot(perfil_temp_jan.index, perfil_temp_jan.values, 
            label='Jan completo', color='coral', linewidth=2, marker='s', alpha=0.6)
    
    ax3.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Temperatura Media (C)', fontsize=11, fontweight='bold')
    ax3.set_title('Perfil de Temperatura: Periodo vs Janeiro', fontsize=13, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(range(0, 24, 2))

# 2.4: Scatter Temperatura vs Erro
ax4 = axes[1, 1]
if len(df_temp_periodo) > 0:
    # Merge temperatura com backtest
    df_merged = df_periodo.merge(
        df_temp_periodo[['timestamp', 'temp_brasil_c']], 
        on='timestamp', 
        how='left'
    )
    
    scatter = ax4.scatter(df_merged['temp_brasil_c'], df_merged['erro_mw'], 
                         c=df_merged['hora'], cmap='viridis', s=50, alpha=0.6)
    ax4.axhline(0, color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    # Linha de tendência
    if len(df_merged.dropna()) > 0:
        z = np.polyfit(df_merged['temp_brasil_c'].dropna(), 
                      df_merged['erro_mw'].dropna(), 1)
        p = np.poly1d(z)
        ax4.plot(df_merged['temp_brasil_c'].dropna(), 
                p(df_merged['temp_brasil_c'].dropna()), 
                "r--", linewidth=2, alpha=0.5, label=f'Tendencia: y={z[0]:.1f}x+{z[1]:.1f}')
    
    ax4.set_xlabel('Temperatura (C)', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Erro (MW)', fontsize=11, fontweight='bold')
    ax4.set_title('Temperatura vs Erro (cor = hora)', fontsize=13, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax4, label='Hora')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '52_comparacao_perfis_21_24_jan.png', dpi=150, bbox_inches='tight')
print(f"  [2/3] Salvo: 52_comparacao_perfis_21_24_jan.png")
plt.close()

# Gráfico 3: Análise dia a dia
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

datas = pd.date_range(data_inicio, data_fim)
for idx, data in enumerate(datas):
    ax = axes[idx // 2, idx % 2]
    
    df_dia = df_periodo[df_periodo['data'] == data.date()].sort_values('hora')
    
    if len(df_dia) > 0:
        ax.plot(df_dia['hora'], df_dia['carga_real'], 
               label='Real', color='blue', linewidth=2.5, marker='o', markersize=6)
        ax.plot(df_dia['hora'], df_dia['carga_sim'], 
               label='Simulado', color='green', linewidth=2.5, marker='s', markersize=6, linestyle='--')
        
        # Informações do dia
        tipo = df_dia['tipo_dia'].iloc[0]
        mape = df_dia['erro_pct'].abs().mean()
        erro_medio = df_dia['erro_mw'].mean()
        
        dia_semana = data.strftime('%A')
        
        ax.set_xlabel('Hora do Dia', fontsize=11, fontweight='bold')
        ax.set_ylabel('Carga (MW)', fontsize=11, fontweight='bold')
        ax.set_title(f'{data.date()} ({dia_semana}, {tipo})\nMAPE={mape:.2f}%, Erro Medio={erro_medio:,.0f} MW', 
                    fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 3))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '53_analise_dia_a_dia_21_24_jan.png', dpi=150, bbox_inches='tight')
print(f"  [3/3] Salvo: 53_analise_dia_a_dia_21_24_jan.png")
plt.close()

# ============================================================================
# RESUMO E DIAGNÓSTICO
# ============================================================================
print("\n" + "="*100)
print("  DIAGNOSTICO")
print("="*100)

print(f"""
PERIODO ANALISADO: 21-24 Janeiro 2025
======================================

METRICAS DO PERIODO:
  MAPE:        {mape_periodo:.2f}%
  Erro medio:  {df_periodo['erro_mw'].mean():,.0f} MW
  Erro std:    {df_periodo['erro_mw'].std():,.0f} MW

COMPARACAO COM JANEIRO COMPLETO:
  MAPE Jan completo:  {mape_jan:.2f}%
  MAPE Periodo:       {mape_periodo:.2f}%
  Diferenca:          {mape_periodo - mape_jan:+.2f}% {"[PIOR]" if mape_periodo > mape_jan else "[MELHOR]"}

TEMPERATURA:
  Media Jan:          {temp_media_jan:.2f} C
  Media Periodo:      {df_temp_periodo['temp_brasil_c'].mean():.2f} C
  Desvio:             {df_temp_periodo['temp_brasil_c'].mean() - temp_media_jan:+.2f} C

TIPO DE DIAS NO PERIODO:
""")

for data in pd.date_range(data_inicio, data_fim):
    df_dia = df_periodo[df_periodo['data'] == data.date()]
    if len(df_dia) > 0:
        tipo = df_dia['tipo_dia'].iloc[0]
        dia_semana = data.strftime('%A')
        print(f"  {data.date()} - {dia_semana:>10} - {tipo}")

print(f"""

GRAFICOS GERADOS:
  51_investigacao_21_24_jan_2025.png    - Serie temporal detalhada
  52_comparacao_perfis_21_24_jan.png    - Comparacao de perfis
  53_analise_dia_a_dia_21_24_jan.png    - Analise individual por dia
""")

print("="*100)





