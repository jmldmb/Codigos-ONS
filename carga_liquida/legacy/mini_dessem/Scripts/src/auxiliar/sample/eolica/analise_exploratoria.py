"""
Análise Exploratória - Geração Eólica
======================================

Objetivo: Entender os padrões de geração eólica para propor o melhor modelo

Autor: ONS
Data: Novembro 2024
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configurar estilo
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Carregar dados
DATA_PATH = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\output\curtailment\eolica\comparacao_perfil_curtailment\por_mes\perfil_hora_por_mes.csv")

print("="*70)
print("ANÁLISE EXPLORATÓRIA - GERAÇÃO EÓLICA")
print("="*70)

df = pd.read_csv(DATA_PATH)
df['mes'] = pd.to_datetime(df['mes'])
df['mes_num'] = df['mes'].dt.month
df['ano'] = df['mes'].dt.year

print(f"\n[1] DADOS CARREGADOS:")
print(f"  • Registros: {len(df)}")
print(f"  • Meses únicos: {df['mes'].nunique()}")
print(f"  • Período: {df['mes'].min().strftime('%Y-%m')} a {df['mes'].max().strftime('%Y-%m')}")
print(f"  • Anos: {df['ano'].unique()}")

# Análise 1: Perfil Horário Médio
print(f"\n[2] PERFIL HORÁRIO MÉDIO GERAL:")
perfil_medio = df.groupby('hora')['potencial_total_mwh_media'].mean()
print(f"  • Hora de menor geração: {perfil_medio.idxmin()}h ({perfil_medio.min():,.0f} MWh)")
print(f"  • Hora de maior geração: {perfil_medio.idxmax()}h ({perfil_medio.max():,.0f} MWh)")
print(f"  • Variação: {((perfil_medio.max() - perfil_medio.min()) / perfil_medio.mean() * 100):.1f}%")

# Análise 2: Comparação Solar vs Eólica
print(f"\n[3] DIFERENÇA SOLAR vs EÓLICA:")
print(f"  SOLAR:")
print(f"    - Padrão: Curva de sino (pico ao meio-dia)")
print(f"    - Geração noturna: ~0 MWh")
print(f"    - Variação intradiária: ALTA (~100%)")
print(f"  ")
print(f"  EÓLICA:")
print(f"    - Padrão: {perfil_medio.idxmin()}h-{perfil_medio.idxmax()}h")
print(f"    - Geração noturna: {perfil_medio[0]:,.0f} MWh (significativa!)")
print(f"    - Variação intradiária: {((perfil_medio.max() - perfil_medio.min()) / perfil_medio.mean() * 100):.1f}%")

# Análise 3: Sazonalidade
print(f"\n[4] SAZONALIDADE MENSAL:")
sazonalidade = df.groupby('mes_num')['potencial_total_mwh_media'].sum().sort_values(ascending=False)
print(f"  • Mês com MAIOR geração: Mês {sazonalidade.idxmax()} ({sazonalidade.max():,.0f} MWh)")
print(f"  • Mês com MENOR geração: Mês {sazonalidade.idxmin()} ({sazonalidade.min():,.0f} MWh)")
print(f"  • Razão Máx/Mín: {sazonalidade.max() / sazonalidade.min():.2f}x")

# Análise 4: Variabilidade
print(f"\n[5] VARIABILIDADE:")
for mes_num in range(1, 13):
    dados_mes = df[df['mes_num'] == mes_num]
    if len(dados_mes) == 0:
        continue
    
    perfil_mes = dados_mes.groupby('hora')['potencial_total_mwh_media']
    cv = perfil_mes.std() / perfil_mes.mean() * 100  # Coeficiente de variação
    
    print(f"  • Mês {mes_num:02d}: CV médio = {cv.mean():.1f}%")

# Análise 5: Comparação entre anos
print(f"\n[6] VARIAÇÃO INTERANUAL:")
for ano in sorted(df['ano'].unique()):
    dados_ano = df[df['ano'] == ano]
    total_ano = dados_ano['potencial_total_mwh_media'].sum()
    n_meses = dados_ano['mes'].nunique()
    print(f"  • {ano}: {total_ano:,.0f} MWh ({n_meses} meses)")

# Análise 6: Autocorrelação Horária
print(f"\n[7] AUTOCORRELAÇÃO:")
perfil_medio_array = perfil_medio.values
autocorr_lag1 = np.corrcoef(perfil_medio_array[:-1], perfil_medio_array[1:])[0, 1]
print(f"  • Autocorrelação (lag=1h): {autocorr_lag1:.3f}")
if autocorr_lag1 > 0.8:
    print(f"    → ALTA autocorrelação (geração de uma hora prediz a próxima)")
else:
    print(f"    → BAIXA autocorrelação (geração mais aleatória)")

print("\n" + "="*70)
print("RECOMENDAÇÃO DE MODELAGEM:")
print("="*70)

if perfil_medio.max() / perfil_medio.min() < 2:
    print("\n✓ Perfil horário UNIFORME (variação < 2x)")
    print("  → Sugestão: Usar perfil FLAT (distribuição uniforme)")
    print("  → Ou: Perfil médio simples por mês")
else:
    print("\n✓ Perfil horário com PADRÃO CLARO")
    print("  → Sugestão: Usar perfil horário médio por mês (igual ao solar)")

if sazonalidade.max() / sazonalidade.min() > 2:
    print("\n✓ ALTA sazonalidade")
    print("  → Importante: Criar 12 perfis distintos (um por mês)")
else:
    print("\n✓ BAIXA sazonalidade")
    print("  → Opcional: Perfil único pode ser suficiente")

if autocorr_lag1 > 0.8:
    print("\n✓ ALTA persistência temporal")
    print("  → Considerar: Modelo estocástico (AR, ARMA) para simular variabilidade")
else:
    print("\n✓ BAIXA persistência")
    print("  → OK: Perfil determinístico é adequado")

print("\n" + "="*70)








