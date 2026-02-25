"""
ANÁLISE EXPLORATÓRIA: DADOS DE CARGA ELÉTRICA
==============================================

Objetivo: Avaliar dados históricos de carga (Mai/2023+) para definir 
          modelo de predição hora a hora.

Autor: Sistema V6 - Começando do Zero
Data: 2025-11-05
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*100)
print("  ANÁLISE EXPLORATÓRIA: DADOS DE CARGA ELÉTRICA (Mai/2023 em diante)")
print("="*100)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 1. CARREGAR DADOS DE CARGA
# ============================================================================
print("\n[1/7] CARREGANDO DADOS DE CARGA...")

# Tentar primeiro comparacao_completa, senão usar BALANCO_ENERGIA
comparacao_path = BASE_DIR / "carga_liquida" / "Output" / "analise_completa" / "comparacao_completa.csv"

if comparacao_path.exists():
    df = pd.read_csv(comparacao_path)
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    df = df.rename(columns={'din_instante': 'timestamp', 'val_carga_real': 'carga_mw'})
    print(f"  [OK] Carregado de comparacao_completa.csv")
else:
    # Carregar de BALANCO_ENERGIA
    print(f"  [INFO] Carregando de arquivos BALANCO_ENERGIA...")
    raw_data_dir = BASE_DIR / "Data" / "raw_data"
    balanco_files = list(raw_data_dir.glob("BALANCO_ENERGIA_SUBSISTEMA_*.xlsx"))
    
    if len(balanco_files) == 0:
        print(f"  [ERRO] Nenhum arquivo BALANCO_ENERGIA encontrado em {raw_data_dir}")
        exit(1)
    
    dfs = []
    for file in sorted(balanco_files):
        print(f"    Lendo: {file.name}")
        df_temp = pd.read_excel(file)
        
        # FILTRAR APENAS SISTEMA INTERLIGADO NACIONAL
        if 'nom_subsistema' in df_temp.columns:
            df_temp = df_temp[df_temp['nom_subsistema'] == 'SISTEMA INTERLIGADO NACIONAL'].copy()
            print(f"      -> Filtrado SIN: {len(df_temp)} registros")
        
        if 'din_instante' in df_temp.columns and 'val_carga' in df_temp.columns:
            dfs.append(df_temp[['din_instante', 'val_carga']])
    
    df = pd.concat(dfs, ignore_index=True)
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    df = df.rename(columns={'din_instante': 'timestamp', 'val_carga': 'carga_mw'})
    df = df.sort_values('timestamp').drop_duplicates(subset='timestamp').reset_index(drop=True)
    print(f"  [OK] Carregado de {len(balanco_files)} arquivos BALANCO_ENERGIA (apenas SIN)")

# Filtrar apenas dados confiáveis (Mai/2023+)
df = df[df['timestamp'] >= '2023-05-01'].copy()
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n  Período: {df['timestamp'].min()} até {df['timestamp'].max()}")
print(f"  Total de registros: {len(df):,}")
print(f"  Total de dias: {len(df) / 24:.0f}")
print(f"  Total de meses: {(df['timestamp'].max() - df['timestamp'].min()).days / 30:.1f}")

# ============================================================================
# 2. CARREGAR DADOS DE TEMPERATURA
# ============================================================================
print("\n[2/7] CARREGANDO DADOS DE TEMPERATURA...")

temp_path = BASE_DIR / "Data" / "temperatura" / "temperatura_processada.parquet"

if temp_path.exists():
    temp = pd.read_parquet(temp_path)
    temp['timestamp'] = pd.to_datetime(temp['timestamp'])
    temp = temp[temp['timestamp'] >= '2023-05-01'].copy()
    print(f"  [OK] Carregado: {len(temp):,} registros")
    print(f"  Período: {temp['timestamp'].min()} até {temp['timestamp'].max()}")
else:
    print(f"  [AVISO] Temperatura não encontrada")
    temp = pd.DataFrame()

# ============================================================================
# 3. PREPARAR FEATURES
# ============================================================================
print("\n[3/7] PREPARANDO FEATURES...")

# Features temporais
df['ano'] = df['timestamp'].dt.year
df['mes'] = df['timestamp'].dt.month
df['dia'] = df['timestamp'].dt.day
df['hora'] = df['timestamp'].dt.hour
df['dia_semana'] = df['timestamp'].dt.dayofweek
df['tipo_dia'] = df['dia_semana'].map({
    0: 'DU', 1: 'DU', 2: 'DU', 3: 'DU', 4: 'DU',
    5: 'SAB', 6: 'DOM'
})
df['data'] = df['timestamp'].dt.date

# Merge temperatura
if len(temp) > 0:
    df = df.merge(temp[['timestamp', 'temp_brasil_c']], on='timestamp', how='left')
    print(f"  [OK] Temperatura merged: {df['temp_brasil_c'].notna().sum() / len(df) * 100:.1f}% cobertura")
else:
    df['temp_brasil_c'] = np.nan

# Carga média mensal (MWmedios)
df_mensal = df.groupby(['ano', 'mes'])['carga_mw'].mean().reset_index()
df_mensal.columns = ['ano', 'mes', 'carga_mensal_mwmed']
df = df.merge(df_mensal, on=['ano', 'mes'], how='left')

print(f"\n  Features criadas:")
print(f"    - ano, mes, dia, hora")
print(f"    - dia_semana (0=Seg, 6=Dom)")
print(f"    - tipo_dia (DU/SAB/DOM)")
print(f"    - carga_mensal_mwmed (MWmedios)")
print(f"    - temp_brasil_c")

# Estatísticas básicas
print(f"\n  Estatísticas de Carga:")
print(f"    Média:   {df['carga_mw'].mean():>12,.0f} MW")
print(f"    Mediana: {df['carga_mw'].median():>12,.0f} MW")
print(f"    Std:     {df['carga_mw'].std():>12,.0f} MW")
print(f"    Min:     {df['carga_mw'].min():>12,.0f} MW")
print(f"    Max:     {df['carga_mw'].max():>12,.0f} MW")

if df['temp_brasil_c'].notna().sum() > 0:
    print(f"\n  Estatísticas de Temperatura:")
    print(f"    Média:   {df['temp_brasil_c'].mean():>12.1f} C")
    print(f"    Mediana: {df['temp_brasil_c'].median():>12.1f} C")
    print(f"    Std:     {df['temp_brasil_c'].std():>12.1f} C")
    print(f"    Min:     {df['temp_brasil_c'].min():>12.1f} C")
    print(f"    Max:     {df['temp_brasil_c'].max():>12.1f} C")

# ============================================================================
# 4. ANÁLISE POR MÊS
# ============================================================================
print("\n[4/7] ANÁLISE POR MÊS...")

df_mes_stats = df.groupby(['ano', 'mes']).agg({
    'carga_mw': ['mean', 'std', 'min', 'max'],
    'temp_brasil_c': ['mean', 'std'],
    'timestamp': 'count'
}).reset_index()

df_mes_stats.columns = ['ano', 'mes', 'carga_media', 'carga_std', 'carga_min', 'carga_max',
                        'temp_media', 'temp_std', 'n_registros']

print(f"\n{'Ano':>6} | {'Mês':>4} | {'Carga Média':>12} | {'Carga Std':>10} | {'Temp Média':>11} | {'N Horas':>8}")
print("-"*75)
for _, row in df_mes_stats.iterrows():
    print(f"{row['ano']:>6} | {row['mes']:>4} | {row['carga_media']:>10,.0f} MW | "
          f"{row['carga_std']:>8,.0f} MW | {row['temp_media']:>9.1f} C | {row['n_registros']:>8.0f}")

# ============================================================================
# 5. ANÁLISE POR HORA DO DIA
# ============================================================================
print("\n[5/7] ANÁLISE POR HORA DO DIA...")

df_hora_stats = df.groupby('hora').agg({
    'carga_mw': ['mean', 'std', 'min', 'max']
}).reset_index()
df_hora_stats.columns = ['hora', 'carga_media', 'carga_std', 'carga_min', 'carga_max']

print(f"\n{'Hora':>6} | {'Carga Média':>12} | {'Carga Std':>10} | {'Carga Min':>11} | {'Carga Max':>11}")
print("-"*65)
for _, row in df_hora_stats.iterrows():
    print(f"{row['hora']:>6} | {row['carga_media']:>10,.0f} MW | {row['carga_std']:>8,.0f} MW | "
          f"{row['carga_min']:>9,.0f} MW | {row['carga_max']:>9,.0f} MW")

# ============================================================================
# 6. ANÁLISE POR TIPO DE DIA
# ============================================================================
print("\n[6/7] ANÁLISE POR TIPO DE DIA...")

df_tipo_stats = df.groupby('tipo_dia').agg({
    'carga_mw': ['mean', 'std', 'min', 'max', 'count']
}).reset_index()
df_tipo_stats.columns = ['tipo_dia', 'carga_media', 'carga_std', 'carga_min', 'carga_max', 'n_registros']

print(f"\n{'Tipo':>8} | {'Carga Média':>12} | {'Carga Std':>10} | {'N Horas':>8}")
print("-"*50)
for _, row in df_tipo_stats.iterrows():
    print(f"{row['tipo_dia']:>8} | {row['carga_media']:>10,.0f} MW | "
          f"{row['carga_std']:>8,.0f} MW | {row['n_registros']:>8.0f}")

# ============================================================================
# 7. CORRELAÇÕES
# ============================================================================
print("\n[7/7] ANÁLISE DE CORRELAÇÕES...")

if df['temp_brasil_c'].notna().sum() > 0:
    corr_temp_carga = df[['carga_mw', 'temp_brasil_c']].corr().iloc[0, 1]
    print(f"\n  Correlação Temperatura x Carga: {corr_temp_carga:+.4f}")

corr_hora_carga = df[['carga_mw', 'hora']].corr().iloc[0, 1]
print(f"  Correlação Hora x Carga: {corr_hora_carga:+.4f}")

corr_mes_carga = df[['carga_mw', 'mes']].corr().iloc[0, 1]
print(f"  Correlação Mês x Carga: {corr_mes_carga:+.4f}")
# ============================================================================
# VISUALIZAÇÕES
# ============================================================================
print("\n" + "="*100)
print("  GERANDO VISUALIZAÇÕES...")
print("="*100)

# Figura 1: Série temporal geral
print("\n[1/8] Série temporal geral...")
fig, axes = plt.subplots(2, 1, figsize=(18, 10))

ax = axes[0]
df_plot = df.groupby('timestamp')['carga_mw'].mean().reset_index()
ax.plot(df_plot['timestamp'], df_plot['carga_mw'], linewidth=0.8, alpha=0.7, color='darkblue')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Série Temporal: Carga Horária (Mai/2023 - Presente)', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

ax = axes[1]
if df['temp_brasil_c'].notna().sum() > 0:
    df_plot = df.groupby('timestamp')['temp_brasil_c'].mean().reset_index()
    ax.plot(df_plot['timestamp'], df_plot['temp_brasil_c'], linewidth=0.8, alpha=0.7, color='red')
    ax.set_ylabel('Temperatura (C)', fontsize=12, fontweight='bold')
    ax.set_title('Temperatura Horária', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '01_serie_temporal_geral.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 01_serie_temporal_geral.png")

# Figura 2: Carga média mensal
print("[2/8] Carga média mensal...")
fig, ax = plt.subplots(figsize=(14, 7))
df_mes_plot = df.groupby(['ano', 'mes']).agg({'carga_mw': 'mean', 'carga_mensal_mwmed': 'first'}).reset_index()
df_mes_plot['ano_mes'] = df_mes_plot['ano'].astype(str) + '-' + df_mes_plot['mes'].astype(str).str.zfill(2)
ax.bar(range(len(df_mes_plot)), df_mes_plot['carga_mw'], color='steelblue', alpha=0.8, edgecolor='black')
ax.set_xticks(range(len(df_mes_plot)))
ax.set_xticklabels(df_mes_plot['ano_mes'], rotation=45, ha='right')
ax.set_ylabel('Carga Média (MW)', fontsize=12, fontweight='bold')
ax.set_title('Carga Média Mensal (MWmedios)', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
for i, v in enumerate(df_mes_plot['carga_mw']):
    ax.text(i, v + 500, f'{v:,.0f}', ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '02_carga_media_mensal.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 02_carga_media_mensal.png")

# Figura 3: Perfil horário médio
print("[3/8] Perfil horário médio...")
fig, ax = plt.subplots(figsize=(14, 7))
df_hora_plot = df.groupby('hora')['carga_mw'].mean().reset_index()
ax.plot(df_hora_plot['hora'], df_hora_plot['carga_mw'], 'o-', linewidth=3, markersize=10, color='darkblue')
ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Média (MW)', fontsize=12, fontweight='bold')
ax.set_title('Perfil Horário Médio (Todas as Horas)', fontsize=14, fontweight='bold')
ax.set_xticks(range(0, 24))
ax.grid(True, alpha=0.3)
for i, row in df_hora_plot.iterrows():
    ax.text(row['hora'], row['carga_mw'] + 800, f"{row['carga_mw']:,.0f}", ha='center', fontsize=9)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '03_perfil_horario_medio.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 03_perfil_horario_medio.png")

# Figura 4: Perfil por tipo de dia
print("[4/8] Perfil por tipo de dia...")
fig, ax = plt.subplots(figsize=(14, 7))
for tipo in ['DU', 'SAB', 'DOM']:
    df_tipo = df[df['tipo_dia'] == tipo].groupby('hora')['carga_mw'].mean().reset_index()
    ax.plot(df_tipo['hora'], df_tipo['carga_mw'], 'o-', linewidth=2.5, markersize=8, label=tipo, alpha=0.8)
ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Média (MW)', fontsize=12, fontweight='bold')
ax.set_title('Perfil Horário por Tipo de Dia', fontsize=14, fontweight='bold')
ax.set_xticks(range(0, 24))
ax.legend(fontsize=12, loc='best')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '04_perfil_por_tipo_dia.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 04_perfil_por_tipo_dia.png")

# Figura 5: Perfil por mês
print("[5/8] Perfil por mês...")
fig, ax = plt.subplots(figsize=(16, 8))
meses_unicos = sorted(df['mes'].unique())
cores = plt.cm.tab10(np.linspace(0, 1, 12))
for mes in meses_unicos:
    df_mes = df[df['mes'] == mes].groupby('hora')['carga_mw'].mean().reset_index()
    ax.plot(df_mes['hora'], df_mes['carga_mw'], 'o-', linewidth=2, markersize=6, 
            label=f'Mês {mes}', alpha=0.7, color=cores[mes-1])
ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Média (MW)', fontsize=12, fontweight='bold')
ax.set_title('Perfil Horário por Mês', fontsize=14, fontweight='bold')
ax.set_xticks(range(0, 24))
ax.legend(fontsize=10, loc='best', ncol=2)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '05_perfil_por_mes.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 05_perfil_por_mes.png")

# Figura 6: Temperatura x Carga (scatter)
if df['temp_brasil_c'].notna().sum() > 0:
    print("[6/8] Scatter Temperatura x Carga...")
    fig, ax = plt.subplots(figsize=(12, 8))
    sample = df[df['temp_brasil_c'].notna()].sample(min(5000, len(df)), random_state=42)
    scatter = ax.scatter(sample['temp_brasil_c'], sample['carga_mw'], 
                        c=sample['hora'], cmap='viridis', alpha=0.5, s=20)
    ax.set_xlabel('Temperatura (C)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Relação Temperatura x Carga (cor = hora do dia)', fontsize=14, fontweight='bold')
    plt.colorbar(scatter, ax=ax, label='Hora')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '06_scatter_temp_carga.png', dpi=150, bbox_inches='tight')
    print(f"  [OK] Salvo: 06_scatter_temp_carga.png")
else:
    print("[6/8] [PULADO] Sem dados de temperatura")

# Figura 7: Heatmap Mês x Hora
print("[7/8] Heatmap Mês x Hora...")
df_heatmap = df.groupby(['mes', 'hora'])['carga_mw'].mean().reset_index()
df_pivot = df_heatmap.pivot(index='mes', columns='hora', values='carga_mw')
fig, ax = plt.subplots(figsize=(16, 8))
sns.heatmap(df_pivot, annot=False, fmt='.0f', cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Carga (MW)'})
ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
ax.set_ylabel('Mês', fontsize=12, fontweight='bold')
ax.set_title('Heatmap: Carga Média por Mês e Hora', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '07_heatmap_mes_hora.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 07_heatmap_mes_hora.png")

# Figura 8: Boxplot por tipo de dia
print("[8/8] Boxplot por tipo de dia e hora...")
fig, axes = plt.subplots(1, 3, figsize=(20, 6), sharey=True)
for i, tipo in enumerate(['DU', 'SAB', 'DOM']):
    ax = axes[i]
    df_tipo = df[df['tipo_dia'] == tipo]
    df_tipo.boxplot(column='carga_mw', by='hora', ax=ax)
    ax.set_title(f'{tipo}', fontsize=13, fontweight='bold')
    ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
    if i == 0:
        ax.set_ylabel('Carga (MW)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.sca(ax)
    plt.xticks(range(1, 25), range(0, 24))
plt.suptitle('Distribuição de Carga por Hora e Tipo de Dia', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '08_boxplot_tipo_dia_hora.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 08_boxplot_tipo_dia_hora.png")

# ============================================================================
# SALVAR DADOS PROCESSADOS
# ============================================================================
print("\n" + "="*100)
print("  SALVANDO DADOS PROCESSADOS...")
print("="*100)

df.to_parquet(OUTPUT_DIR / 'dados_processados_mai2023.parquet', index=False)
print(f"\n[OK] Dados salvos: dados_processados_mai2023.parquet")

df_mes_stats.to_csv(OUTPUT_DIR / 'estatisticas_mensais.csv', index=False)
print(f"[OK] Estatísticas mensais salvas")

df_hora_stats.to_csv(OUTPUT_DIR / 'estatisticas_horarias.csv', index=False)
print(f"[OK] Estatísticas horárias salvas")

df_tipo_stats.to_csv(OUTPUT_DIR / 'estatisticas_tipo_dia.csv', index=False)
print(f"[OK] Estatísticas por tipo de dia salvas")

# ============================================================================
# RELATÓRIO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RELATÓRIO FINAL: RECOMENDAÇÕES PARA MODELAGEM")
print("="*100)

print(f"""
RESUMO DOS DADOS (Mai/2023+):
  • Total de horas analisadas: {len(df):,}
  • Período: {df['timestamp'].min().date()} até {df['timestamp'].max().date()}
  • Carga média: {df['carga_mw'].mean():,.0f} MW
  • Variação: {df['carga_mw'].min():,.0f} MW até {df['carga_mw'].max():,.0f} MW

ANÁLISE DOS FATORES:

1. HORA DO DIA:
   • Correlação com carga: {corr_hora_carga:+.4f}
   • Padrão MUITO CLARO: Mínimo às 4-5h, Máximo às 18-19h
   • Amplitude: ~{df_hora_stats['carga_media'].max() - df_hora_stats['carga_media'].min():,.0f} MW

2. TIPO DE DIA:
   • DU:  {df_tipo_stats[df_tipo_stats['tipo_dia']=='DU']['carga_media'].values[0]:,.0f} MW (baseline)
   • SAB: {df_tipo_stats[df_tipo_stats['tipo_dia']=='SAB']['carga_media'].values[0]:,.0f} MW ({(df_tipo_stats[df_tipo_stats['tipo_dia']=='SAB']['carga_media'].values[0] / df_tipo_stats[df_tipo_stats['tipo_dia']=='DU']['carga_media'].values[0] - 1) * 100:+.1f}%)
   • DOM: {df_tipo_stats[df_tipo_stats['tipo_dia']=='DOM']['carga_media'].values[0]:,.0f} MW ({(df_tipo_stats[df_tipo_stats['tipo_dia']=='DOM']['carga_media'].values[0] / df_tipo_stats[df_tipo_stats['tipo_dia']=='DU']['carga_media'].values[0] - 1) * 100:+.1f}%)
   • Diferença DU vs DOM: {df_tipo_stats[df_tipo_stats['tipo_dia']=='DU']['carga_media'].values[0] - df_tipo_stats[df_tipo_stats['tipo_dia']=='DOM']['carga_media'].values[0]:,.0f} MW

3. SAZONALIDADE MENSAL:
   • Correlação mês x carga: {corr_mes_carga:+.4f}
   • Variação entre meses: {df_mes_stats['carga_media'].max() - df_mes_stats['carga_media'].min():,.0f} MW
   • Mês mais alto: {df_mes_stats.loc[df_mes_stats['carga_media'].idxmax(), 'mes']:.0f} ({df_mes_stats['carga_media'].max():,.0f} MW)
   • Mês mais baixo: {df_mes_stats.loc[df_mes_stats['carga_media'].idxmin(), 'mes']:.0f} ({df_mes_stats['carga_media'].min():,.0f} MW)
""")

if df['temp_brasil_c'].notna().sum() > 0:
    print(f"""
4. TEMPERATURA:
   • Correlação temp x carga: {corr_temp_carga:+.4f}
   • Temperatura média: {df['temp_brasil_c'].mean():.1f}C
   • Variação: {df['temp_brasil_c'].min():.1f}C até {df['temp_brasil_c'].max():.1f}C
""")

print("""
="*100

PRÓXIMOS PASSOS:

Com base nesta análise, vamos definir JUNTOS:

1. Qual a estrutura matemática do modelo?
   - Aditivo? Multiplicativo? Misto?
   
2. Como modelar cada componente?
   - Perfil horário: lookup table? função suave?
   - Carga mensal: como normalizar?
   - Temperatura: linear? não-linear? por faixa?
   - Tipo de dia: fator multiplicativo?

3. Precisamos de variabilidade estocástica?
   - Determinístico puro?
   - Adicionar ruído?

Todos os gráficos foram salvos em:
""")
print(f"  {OUTPUT_DIR}")
print("\n" + "="*100)

