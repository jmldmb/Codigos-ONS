"""
ANÁLISE: PERFIL TÍPICO DE TEMPERATURA HORÁRIA
==============================================

Investigar se existe um padrão típico de variação horária de temperatura
dado a temperatura média mensal
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

print("="*100)
print("  ANÁLISE: PERFIL TÍPICO DE TEMPERATURA HORÁRIA POR MÊS")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1/4] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

print(f"  [OK] {len(df):,} registros com temperatura")

# ============================================================================
# 2. CALCULAR PERFIL HORÁRIO DE TEMPERATURA POR MÊS/ANO
# ============================================================================
print("\n[2/4] CALCULANDO PERFIL HORÁRIO DE TEMPERATURA...")

# Temperatura média mensal
df['temp_media_mensal'] = df.groupby(['ano', 'mes'])['temp_brasil_c'].transform('mean')

# Desvio horário em relação à média mensal
df['temp_desvio_mensal'] = df['temp_brasil_c'] - df['temp_media_mensal']

# Temperatura média diária
df['temp_media_diaria'] = df.groupby('data')['temp_brasil_c'].transform('mean')

# Desvio horário em relação à média diária
df['temp_desvio_diario'] = df['temp_brasil_c'] - df['temp_media_diaria']

print(f"\n  Estatísticas de desvio horário vs média MENSAL:")
print(f"    Média:   {df['temp_desvio_mensal'].mean():.4f}°C (deveria ser ~0)")
print(f"    Std:     {df['temp_desvio_mensal'].std():.4f}°C")
print(f"    Min:     {df['temp_desvio_mensal'].min():.4f}°C")
print(f"    Max:     {df['temp_desvio_mensal'].max():.4f}°C")

print(f"\n  Estatísticas de desvio horário vs média DIÁRIA:")
print(f"    Média:   {df['temp_desvio_diario'].mean():.4f}°C (deveria ser ~0)")
print(f"    Std:     {df['temp_desvio_diario'].std():.4f}°C")
print(f"    Min:     {df['temp_desvio_diario'].min():.4f}°C")
print(f"    Max:     {df['temp_desvio_diario'].max():.4f}°C")

# ============================================================================
# 3. PERFIL TÍPICO POR MÊS
# ============================================================================
print("\n[3/4] CALCULANDO PERFIL TÍPICO POR MÊS...")

# Para cada mês, calcular perfil horário médio
perfis_mes = []

for mes in range(1, 13):
    df_mes = df[df['mes'] == mes]
    
    perfil_hora = df_mes.groupby('hora').agg({
        'temp_desvio_mensal': ['mean', 'std'],
        'temp_brasil_c': ['mean', 'std'],
        'temp_media_mensal': 'mean'
    }).reset_index()
    
    perfil_hora.columns = ['hora', 'desvio_mean', 'desvio_std', 'temp_abs_mean', 'temp_abs_std', 'temp_mes_mean']
    perfil_hora['mes'] = mes
    
    perfis_mes.append(perfil_hora)

df_perfis = pd.concat(perfis_mes, ignore_index=True)

# Calcular consistência: quanto o perfil varia entre anos?
print(f"\n  Consistência do perfil horário por mês:")
print(f"  {'Mês':>4} | {'Temp Média':>11} | {'Desvio Std':>12} | {'Amplitude':>11} | {'Consistência':>13}")
print("-"*65)

for mes in range(1, 13):
    df_mes_perfil = df_perfis[df_perfis['mes'] == mes]
    temp_media = df_mes_perfil['temp_mes_mean'].mean()
    desvio_std_medio = df_mes_perfil['desvio_std'].mean()
    amplitude = df_mes_perfil['desvio_mean'].max() - df_mes_perfil['desvio_mean'].min()
    consistencia = amplitude / desvio_std_medio if desvio_std_medio > 0 else 0
    
    print(f"  {mes:>4} | {temp_media:>9.1f}°C | {desvio_std_medio:>10.2f}°C | {amplitude:>9.2f}°C | {consistencia:>12.2f}")

# ============================================================================
# 4. ANÁLISE POR ANO: Perfil é consistente?
# ============================================================================
print("\n[4/4] ANALISANDO CONSISTÊNCIA ENTRE ANOS...")

# Para cada mês, comparar perfil entre anos diferentes
for mes in [1, 4, 7, 10]:  # Jan, Abr, Jul, Out
    df_mes = df[df['mes'] == mes]
    
    anos = df_mes['ano'].unique()
    if len(anos) >= 2:
        perfis_anos = []
        for ano in anos:
            perfil = df_mes[df_mes['ano'] == ano].groupby('hora')['temp_desvio_mensal'].mean()
            perfis_anos.append(perfil)
        
        # Correlação entre perfis de anos diferentes
        if len(perfis_anos) >= 2:
            from scipy.stats import pearsonr
            correlacoes = []
            for i in range(len(perfis_anos)):
                for j in range(i+1, len(perfis_anos)):
                    corr, _ = pearsonr(perfis_anos[i], perfis_anos[j])
                    correlacoes.append(corr)
            
            if correlacoes:
                print(f"\n  Mês {mes}: Correlação média entre perfis de anos diferentes: {np.mean(correlacoes):.4f}")

# ============================================================================
# VISUALIZAÇÕES
# ============================================================================
print("\n" + "="*100)
print("  GERANDO VISUALIZAÇÕES...")
print("="*100)

# Figura 1: Perfil horário típico por mês (desvio vs média mensal)
fig, axes = plt.subplots(3, 4, figsize=(20, 15))
axes = axes.flatten()

for i, mes in enumerate(range(1, 13)):
    ax = axes[i]
    df_mes_perfil = df_perfis[df_perfis['mes'] == mes]
    
    # Linha do desvio médio
    ax.plot(df_mes_perfil['hora'], df_mes_perfil['desvio_mean'], 
           'o-', linewidth=3, markersize=8, color='darkblue', label='Desvio médio')
    
    # Banda de desvio padrão
    ax.fill_between(df_mes_perfil['hora'],
                    df_mes_perfil['desvio_mean'] - df_mes_perfil['desvio_std'],
                    df_mes_perfil['desvio_mean'] + df_mes_perfil['desvio_std'],
                    alpha=0.3, color='blue', label='±1 std')
    
    ax.axhline(0, color='red', linewidth=1, linestyle='--', alpha=0.7)
    ax.set_xlabel('Hora', fontsize=10)
    ax.set_ylabel('Desvio vs Média Mensal (°C)', fontsize=10)
    ax.set_title(f'Mês {mes} (Média: {df_mes_perfil["temp_mes_mean"].mean():.1f}°C)', 
                fontsize=11, fontweight='bold')
    ax.set_xticks(range(0, 24, 3))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='best')

plt.suptitle('Perfil Horário Típico de Temperatura por Mês\n(Desvio em relação à média mensal)', 
            fontsize=15, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '30_perfil_temperatura_horario_por_mes.png', dpi=150, bbox_inches='tight')
print(f"\n[1/4] Salvo: 30_perfil_temperatura_horario_por_mes.png")

# Figura 2: Heatmap do desvio horário por mês
fig, ax = plt.subplots(figsize=(14, 10))
df_pivot = df_perfis.pivot(index='hora', columns='mes', values='desvio_mean')
sns.heatmap(df_pivot, annot=True, fmt='.2f', cmap='RdBu_r', center=0,
            vmin=-4, vmax=4, ax=ax, cbar_kws={'label': 'Desvio vs Média Mensal (°C)'})
ax.set_xlabel('Mês', fontsize=13, fontweight='bold')
ax.set_ylabel('Hora do Dia', fontsize=13, fontweight='bold')
ax.set_title('Heatmap: Desvio de Temperatura Horária vs Média Mensal\n(Padrão típico por mês e hora)', 
            fontsize=15, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '31_heatmap_desvio_temperatura.png', dpi=150, bbox_inches='tight')
print(f"[2/4] Salvo: 31_heatmap_desvio_temperatura.png")

# Figura 3: Comparação de perfis entre estações
fig, axes = plt.subplots(2, 2, figsize=(18, 14))

estacoes = {
    'Verão (Jan)': [1],
    'Outono (Abr)': [4],
    'Inverno (Jul)': [7],
    'Primavera (Out)': [10]
}

cores = {'Verão (Jan)': 'red', 'Outono (Abr)': 'orange', 
         'Inverno (Jul)': 'blue', 'Primavera (Out)': 'green'}

for idx, (estacao, meses) in enumerate(estacoes.items()):
    ax = axes[idx // 2, idx % 2]
    
    for mes in meses:
        df_mes_perfil = df_perfis[df_perfis['mes'] == mes]
        
        ax.plot(df_mes_perfil['hora'], df_mes_perfil['desvio_mean'], 
               'o-', linewidth=3, markersize=8, color=cores[estacao],
               label=f'Mês {mes}')
        
        ax.fill_between(df_mes_perfil['hora'],
                        df_mes_perfil['desvio_mean'] - df_mes_perfil['desvio_std'],
                        df_mes_perfil['desvio_mean'] + df_mes_perfil['desvio_std'],
                        alpha=0.2, color=cores[estacao])
    
    ax.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.5)
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('Desvio vs Média Mensal (°C)', fontsize=12, fontweight='bold')
    ax.set_title(estacao, fontsize=13, fontweight='bold')
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

plt.suptitle('Perfil de Temperatura Horária por Estação', 
            fontsize=15, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '32_perfil_temperatura_estacoes.png', dpi=150, bbox_inches='tight')
print(f"[3/4] Salvo: 32_perfil_temperatura_estacoes.png")

# Figura 4: Temperatura absoluta (não desvio) por mês
fig, axes = plt.subplots(3, 4, figsize=(20, 15))
axes = axes.flatten()

for i, mes in enumerate(range(1, 13)):
    ax = axes[i]
    df_mes_perfil = df_perfis[df_perfis['mes'] == mes]
    
    ax.plot(df_mes_perfil['hora'], df_mes_perfil['temp_abs_mean'], 
           'o-', linewidth=3, markersize=8, color='darkred')
    
    ax.fill_between(df_mes_perfil['hora'],
                    df_mes_perfil['temp_abs_mean'] - df_mes_perfil['temp_abs_std'],
                    df_mes_perfil['temp_abs_mean'] + df_mes_perfil['temp_abs_std'],
                    alpha=0.3, color='red')
    
    temp_media = df_mes_perfil['temp_mes_mean'].mean()
    ax.axhline(temp_media, color='blue', linewidth=2, linestyle='--', 
              alpha=0.7, label=f'Média: {temp_media:.1f}°C')
    
    ax.set_xlabel('Hora', fontsize=10)
    ax.set_ylabel('Temperatura (°C)', fontsize=10)
    ax.set_title(f'Mês {mes}', fontsize=11, fontweight='bold')
    ax.set_xticks(range(0, 24, 3))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='best')

plt.suptitle('Perfil de Temperatura ABSOLUTA por Mês', 
            fontsize=15, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '33_perfil_temperatura_absoluta_mes.png', dpi=150, bbox_inches='tight')
print(f"[4/4] Salvo: 33_perfil_temperatura_absoluta_mes.png")

# ============================================================================
# RESUMO ESTATÍSTICO
# ============================================================================
print("\n" + "="*100)
print("  RESUMO: PERFIL TÍPICO DE TEMPERATURA HORÁRIA")
print("="*100)

# Amplitude típica do perfil
amplitudes = []
for mes in range(1, 13):
    df_mes_perfil = df_perfis[df_perfis['mes'] == mes]
    amplitude = df_mes_perfil['desvio_mean'].max() - df_mes_perfil['desvio_mean'].min()
    amplitudes.append(amplitude)

print(f"""
CARACTERÍSTICAS DO PERFIL HORÁRIO:

1. AMPLITUDE (diferença min-max no dia):
   Média:    {np.mean(amplitudes):.2f}°C
   Mínima:   {np.min(amplitudes):.2f}°C (mês {np.argmin(amplitudes)+1})
   Máxima:   {np.max(amplitudes):.2f}°C (mês {np.argmax(amplitudes)+1})

2. PADRÃO GERAL:
   - Temperatura MÍNIMA:  ~6h (amanhecer)
   - Temperatura MÁXIMA:  ~14-15h (início da tarde)
   - Amplitude típica:    {np.mean(amplitudes):.1f}°C

3. VARIABILIDADE (std médio):
   Por hora: {df_perfis['desvio_std'].mean():.2f}°C
   
4. CONSISTÊNCIA:
   O perfil horário é CONSISTENTE entre meses?
   {'SIM - pode ser usado para estimar temp horária!' if np.std(amplitudes) < 2 else 'VARIÁVEL - usar com cuidado'}
""")

# Tabela resumo
print(f"\nTABELA RESUMO: Desvio típico por hora (média de todos os meses)")
print(f"\n{'Hora':>4} | {'Desvio Médio':>13} | {'Std':>8} | {'Interpretação':>30}")
print("-"*65)

perfil_geral = df_perfis.groupby('hora').agg({
    'desvio_mean': 'mean',
    'desvio_std': 'mean'
}).reset_index()

for _, row in perfil_geral.iterrows():
    hora = int(row['hora'])
    desvio = row['desvio_mean']
    std = row['desvio_std']
    
    if hora in [5, 6, 7]:
        interp = "Amanhecer (mais frio)"
    elif hora in [14, 15, 16]:
        interp = "Tarde (mais quente)"
    elif hora in [0, 1, 23]:
        interp = "Noite (intermediário)"
    else:
        interp = ""
    
    print(f"{hora:>4} | {desvio:>+11.2f}°C | {std:>6.2f}°C | {interp:>30}")

print("\n" + "="*100)
print(f"Gráficos salvos em: {OUTPUT_DIR}")
print("="*100)

# Salvar dados
df_perfis.to_csv(OUTPUT_DIR / 'perfil_temperatura_horario_por_mes.csv', index=False)
perfil_geral.to_csv(OUTPUT_DIR / 'perfil_temperatura_horario_geral.csv', index=False)
print(f"\n[OK] Dados salvos")





