"""
Análise Detalhada: Hidrelétricas FD (Fio d'água) vs R (Reservatório)
======================================================================

Gera análises completas dos valores históricos de geração hidrelétrica
separadas por tipo: Fio d'água (FD) e Reservatório (R).

Análises incluídas:
- Valores médios por mês
- Perfil diário (por dia da semana)
- Perfil horário
- Distribuições estatísticas
- Séries temporais
- Comparações FD vs R
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import calendar
import warnings
warnings.filterwarnings('ignore')

# Configuração visual
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

# Diretórios
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "hidro_reservatorio"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Nomes de meses em português
MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

DIAS_SEMANA_PT = {
    0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sab', 6: 'Dom'
}

def carregar_dados():
    """Carrega dados históricos de carga líquida com FD e R."""
    
    print("\n" + "="*80)
    print("  CARREGANDO DADOS HISTÓRICOS")
    print("="*80 + "\n")
    
    # Tentar carregar do arquivo histórico processado
    path_hist = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
    
    if path_hist.exists():
        print(f"Carregando arquivo: {path_hist.name}")
        df = pd.read_parquet(path_hist)
        print(f"  [OK] {len(df):,} registros carregados")
    else:
        print(f"[ERRO] Arquivo não encontrado: {path_hist}")
        print("Por favor, execute o script carga_liquida.py primeiro para gerar os dados.")
        return None
    
    # Verificar se as colunas FD e R existem
    if 'FD' not in df.columns or 'R' not in df.columns:
        print("\n[ERRO] Colunas 'FD' e 'R' não encontradas no arquivo.")
        print(f"Colunas disponíveis: {list(df.columns)}")
        return None
    
    # Converter din_instante para datetime
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    
    # Extrair componentes temporais
    df['ano'] = df['din_instante'].dt.year
    df['mes'] = df['din_instante'].dt.month
    df['dia'] = df['din_instante'].dt.day
    df['hora'] = df['din_instante'].dt.hour
    df['dia_semana'] = df['din_instante'].dt.dayofweek  # 0=Segunda, 6=Domingo
    df['dia_ano'] = df['din_instante'].dt.dayofyear
    
    # Garantir que FD e R sejam numéricos
    df['FD'] = pd.to_numeric(df['FD'], errors='coerce')
    df['R'] = pd.to_numeric(df['R'], errors='coerce')
    
    # Remover valores NaN
    df = df.dropna(subset=['FD', 'R'])
    
    print(f"\nPeríodo: {df['din_instante'].min()} até {df['din_instante'].max()}")
    print(f"Anos disponíveis: {sorted(df['ano'].unique())}")
    print(f"\nEstatísticas gerais:")
    print(f"  FD (Fio d'água):")
    print(f"    Média: {df['FD'].mean():,.0f} MW")
    print(f"    Mín:   {df['FD'].min():,.0f} MW")
    print(f"    Máx:   {df['FD'].max():,.0f} MW")
    print(f"  R (Reservatório):")
    print(f"    Média: {df['R'].mean():,.0f} MW")
    print(f"    Mín:   {df['R'].min():,.0f} MW")
    print(f"    Máx:   {df['R'].max():,.0f} MW")
    
    return df

def gerar_analise_mensal(df):
    """Gera análise de valores médios por mês."""
    
    print("\n" + "="*80)
    print("  ANÁLISE 1: VALORES MÉDIOS POR MÊS")
    print("="*80 + "\n")
    
    # Agrupar por ano e mês
    df_mensal = df.groupby(['ano', 'mes']).agg({
        'FD': 'mean',
        'R': 'mean'
    }).reset_index()
    
    # Criar figura com 3 subplots
    fig, axes = plt.subplots(3, 1, figsize=(16, 14))
    fig.suptitle('Análise Mensal: Hidrelétricas FD vs R', fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Série temporal mensal
    ax = axes[0]
    anos_unicos = sorted(df_mensal['ano'].unique())
    
    for ano in anos_unicos:
        df_ano = df_mensal[df_mensal['ano'] == ano]
        ax.plot(df_ano['mes'], df_ano['FD'], 'o-', label=f'FD {ano}', linewidth=2, markersize=6)
        ax.plot(df_ano['mes'], df_ano['R'], 's--', label=f'R {ano}', linewidth=2, markersize=6)
    
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Geração Média (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Série Temporal: Geração Média Mensal', fontsize=13, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([MESES_PT[i] for i in range(1, 13)])
    
    # 2. Média por mês (todos os anos agregados)
    ax = axes[1]
    media_mensal = df.groupby('mes').agg({
        'FD': 'mean',
        'R': 'mean'
    }).reset_index()
    
    x = np.arange(len(media_mensal))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, media_mensal['FD'], width, label='FD (Fio d\'água)', 
                   alpha=0.8, color='steelblue', edgecolor='black')
    bars2 = ax.bar(x + width/2, media_mensal['R'], width, label='R (Reservatório)', 
                   alpha=0.8, color='coral', edgecolor='black')
    
    # Adicionar valores nas barras
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}',
                   ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Geração Média (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Média Histórica por Mês (Todos os Anos)', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([MESES_PT[i+1] for i in range(12)])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3. Razão FD/R por mês
    ax = axes[2]
    media_mensal['razao_FD_R'] = media_mensal['FD'] / media_mensal['R']
    
    colors = ['green' if r > 1 else 'red' for r in media_mensal['razao_FD_R']]
    bars = ax.bar(x, media_mensal['razao_FD_R'], color=colors, alpha=0.7, edgecolor='black')
    
    ax.axhline(y=1, color='black', linestyle='--', linewidth=2, label='FD = R')
    
    # Adicionar valores nas barras
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.2f}',
               ha='center', va='bottom' if height > 1 else 'top', fontsize=9)
    
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Razão FD/R', fontsize=12, fontweight='bold')
    ax.set_title('Razão Fio d\'água / Reservatório por Mês', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([MESES_PT[i+1] for i in range(12)])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_mensal.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] Gráfico salvo: analise_mensal.png")
    
    # Salvar dados em CSV
    df_mensal.to_csv(OUTPUT_DIR / 'valores_mensais.csv', index=False)
    media_mensal.to_csv(OUTPUT_DIR / 'media_por_mes.csv', index=False)
    print("  [OK] CSVs salvos: valores_mensais.csv, media_por_mes.csv")

def gerar_perfil_diario(df):
    """Gera perfil por dia da semana."""
    
    print("\n" + "="*80)
    print("  ANÁLISE 2: PERFIL POR DIA DA SEMANA")
    print("="*80 + "\n")
    
    # Agrupar por dia da semana
    perfil_semanal = df.groupby('dia_semana').agg({
        'FD': ['mean', 'std', 'min', 'max'],
        'R': ['mean', 'std', 'min', 'max']
    }).reset_index()
    
    # Criar figura
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Perfil por Dia da Semana: Hidrelétricas FD vs R', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Valores médios com desvio padrão
    ax = axes[0]
    dias = perfil_semanal['dia_semana'].values
    
    ax.plot(dias, perfil_semanal['FD']['mean'], 'o-', label='FD (Fio d\'água)', 
           linewidth=3, markersize=8, color='steelblue')
    ax.fill_between(dias,
                     perfil_semanal['FD']['mean'] - perfil_semanal['FD']['std'],
                     perfil_semanal['FD']['mean'] + perfil_semanal['FD']['std'],
                     alpha=0.3, color='steelblue')
    
    ax.plot(dias, perfil_semanal['R']['mean'], 's-', label='R (Reservatório)', 
           linewidth=3, markersize=8, color='coral')
    ax.fill_between(dias,
                     perfil_semanal['R']['mean'] - perfil_semanal['R']['std'],
                     perfil_semanal['R']['mean'] + perfil_semanal['R']['std'],
                     alpha=0.3, color='coral')
    
    ax.set_xlabel('Dia da Semana', fontsize=12, fontweight='bold')
    ax.set_ylabel('Geração Média (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Geração Média por Dia da Semana (com desvio padrão)', 
                fontsize=13, fontweight='bold')
    ax.set_xticks(range(7))
    ax.set_xticklabels([DIAS_SEMANA_PT[i] for i in range(7)])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # 2. Boxplot por dia da semana
    ax = axes[1]
    
    df_plot = df[['dia_semana', 'FD', 'R']].copy()
    df_plot['dia_semana_nome'] = df_plot['dia_semana'].map(DIAS_SEMANA_PT)
    
    # Preparar dados para boxplot lado a lado
    positions_fd = np.arange(7) - 0.2
    positions_r = np.arange(7) + 0.2
    
    bp_fd = ax.boxplot([df_plot[df_plot['dia_semana']==i]['FD'].values for i in range(7)],
                        positions=positions_fd, widths=0.35,
                        patch_artist=True, showfliers=False)
    bp_r = ax.boxplot([df_plot[df_plot['dia_semana']==i]['R'].values for i in range(7)],
                       positions=positions_r, widths=0.35,
                       patch_artist=True, showfliers=False)
    
    # Colorir boxplots
    for patch in bp_fd['boxes']:
        patch.set_facecolor('steelblue')
        patch.set_alpha(0.7)
    for patch in bp_r['boxes']:
        patch.set_facecolor('coral')
        patch.set_alpha(0.7)
    
    ax.set_xlabel('Dia da Semana', fontsize=12, fontweight='bold')
    ax.set_ylabel('Geração (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Distribuição por Dia da Semana (Boxplot)', fontsize=13, fontweight='bold')
    ax.set_xticks(range(7))
    ax.set_xticklabels([DIAS_SEMANA_PT[i] for i in range(7)])
    ax.grid(True, alpha=0.3, axis='y')
    
    # Legenda manual
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='steelblue', alpha=0.7, label='FD (Fio d\'água)'),
        Patch(facecolor='coral', alpha=0.7, label='R (Reservatório)')
    ]
    ax.legend(handles=legend_elements, fontsize=11)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'perfil_dia_semana.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] Gráfico salvo: perfil_dia_semana.png")

def gerar_perfil_horario(df):
    """Gera perfil horário médio."""
    
    print("\n" + "="*80)
    print("  ANÁLISE 3: PERFIL HORÁRIO")
    print("="*80 + "\n")
    
    # Agrupar por hora
    perfil_horario = df.groupby('hora').agg({
        'FD': ['mean', 'std', 'min', 'max'],
        'R': ['mean', 'std', 'min', 'max']
    }).reset_index()
    
    # Criar figura
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Perfil Horário: Hidrelétricas FD vs R', fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Perfil horário médio
    ax = axes[0, 0]
    horas = perfil_horario['hora'].values
    
    ax.plot(horas, perfil_horario['FD']['mean'], 'o-', label='FD (Fio d\'água)', 
           linewidth=2.5, markersize=6, color='steelblue')
    ax.fill_between(horas,
                     perfil_horario['FD']['mean'] - perfil_horario['FD']['std'],
                     perfil_horario['FD']['mean'] + perfil_horario['FD']['std'],
                     alpha=0.3, color='steelblue')
    
    ax.plot(horas, perfil_horario['R']['mean'], 's-', label='R (Reservatório)', 
           linewidth=2.5, markersize=6, color='coral')
    ax.fill_between(horas,
                     perfil_horario['R']['mean'] - perfil_horario['R']['std'],
                     perfil_horario['R']['mean'] + perfil_horario['R']['std'],
                     alpha=0.3, color='coral')
    
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('Geração Média (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Geração Média por Hora (com desvio padrão)', fontsize=13, fontweight='bold')
    ax.set_xticks(range(0, 24, 2))
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # 2. Variabilidade horária (coeficiente de variação)
    ax = axes[0, 1]
    cv_fd = (perfil_horario['FD']['std'] / perfil_horario['FD']['mean']) * 100
    cv_r = (perfil_horario['R']['std'] / perfil_horario['R']['mean']) * 100
    
    ax.plot(horas, cv_fd, 'o-', label='FD (Fio d\'água)', 
           linewidth=2.5, markersize=6, color='steelblue')
    ax.plot(horas, cv_r, 's-', label='R (Reservatório)', 
           linewidth=2.5, markersize=6, color='coral')
    
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('Coeficiente de Variação (%)', fontsize=12, fontweight='bold')
    ax.set_title('Variabilidade por Hora', fontsize=13, fontweight='bold')
    ax.set_xticks(range(0, 24, 2))
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # 3. Heatmap: Hora vs Mês (FD)
    ax = axes[1, 0]
    pivot_fd = df.pivot_table(values='FD', index='hora', columns='mes', aggfunc='mean')
    im = ax.imshow(pivot_fd.values, aspect='auto', cmap='YlOrRd', interpolation='nearest')
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
    ax.set_title('Heatmap: FD (Fio d\'água) - Hora vs Mês', fontsize=13, fontweight='bold')
    ax.set_xticks(range(12))
    ax.set_xticklabels([MESES_PT[i+1] for i in range(12)])
    ax.set_yticks(range(0, 24, 2))
    ax.set_yticklabels(range(0, 24, 2))
    plt.colorbar(im, ax=ax, label='Geração Média (MW)')
    
    # 4. Heatmap: Hora vs Mês (R)
    ax = axes[1, 1]
    pivot_r = df.pivot_table(values='R', index='hora', columns='mes', aggfunc='mean')
    im = ax.imshow(pivot_r.values, aspect='auto', cmap='YlGnBu', interpolation='nearest')
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
    ax.set_title('Heatmap: R (Reservatório) - Hora vs Mês', fontsize=13, fontweight='bold')
    ax.set_xticks(range(12))
    ax.set_xticklabels([MESES_PT[i+1] for i in range(12)])
    ax.set_yticks(range(0, 24, 2))
    ax.set_yticklabels(range(0, 24, 2))
    plt.colorbar(im, ax=ax, label='Geração Média (MW)')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'perfil_horario.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] Gráfico salvo: perfil_horario.png")
    
    # Salvar dados
    perfil_horario_flat = perfil_horario.copy()
    perfil_horario_flat.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col 
                                    for col in perfil_horario_flat.columns.values]
    perfil_horario_flat.to_csv(OUTPUT_DIR / 'perfil_horario.csv', index=False)
    print("  [OK] CSV salvo: perfil_horario.csv")

def gerar_distribuicoes(df):
    """Gera análise de distribuições estatísticas."""
    
    print("\n" + "="*80)
    print("  ANÁLISE 4: DISTRIBUIÇÕES ESTATÍSTICAS")
    print("="*80 + "\n")
    
    # Criar figura
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Distribuições Estatísticas: FD vs R', fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Histogramas
    ax = axes[0, 0]
    ax.hist(df['FD'], bins=50, alpha=0.7, color='steelblue', edgecolor='black', label='FD')
    ax.hist(df['R'], bins=50, alpha=0.7, color='coral', edgecolor='black', label='R')
    ax.set_xlabel('Geração (MW)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequência', fontsize=11, fontweight='bold')
    ax.set_title('Histograma', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 2. Densidade (KDE)
    ax = axes[0, 1]
    df['FD'].plot.kde(ax=ax, color='steelblue', linewidth=2.5, label='FD')
    df['R'].plot.kde(ax=ax, color='coral', linewidth=2.5, label='R')
    ax.set_xlabel('Geração (MW)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Densidade', fontsize=11, fontweight='bold')
    ax.set_title('Densidade (KDE)', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 3. Boxplot comparativo
    ax = axes[0, 2]
    bp = ax.boxplot([df['FD'], df['R']], labels=['FD', 'R'], patch_artist=True, showfliers=False)
    bp['boxes'][0].set_facecolor('steelblue')
    bp['boxes'][0].set_alpha(0.7)
    bp['boxes'][1].set_facecolor('coral')
    bp['boxes'][1].set_alpha(0.7)
    ax.set_ylabel('Geração (MW)', fontsize=11, fontweight='bold')
    ax.set_title('Boxplot Comparativo', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. Q-Q Plot FD
    ax = axes[1, 0]
    from scipy import stats
    stats.probplot(df['FD'], dist="norm", plot=ax)
    ax.set_title('Q-Q Plot: FD (Fio d\'água)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 5. Q-Q Plot R
    ax = axes[1, 1]
    stats.probplot(df['R'], dist="norm", plot=ax)
    ax.set_title('Q-Q Plot: R (Reservatório)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 6. Scatter FD vs R
    ax = axes[1, 2]
    # Sample para não sobrecarregar o gráfico
    df_sample = df.sample(min(10000, len(df)))
    ax.scatter(df_sample['FD'], df_sample['R'], alpha=0.3, s=10, color='purple')
    
    # Linha de tendência
    z = np.polyfit(df['FD'], df['R'], 1)
    p = np.poly1d(z)
    ax.plot(df['FD'].sort_values(), p(df['FD'].sort_values()), 
           "r--", linewidth=2, label=f'y={z[0]:.2f}x+{z[1]:.0f}')
    
    # Correlação
    corr = df['FD'].corr(df['R'])
    ax.text(0.05, 0.95, f'Correlação: {corr:.3f}', 
           transform=ax.transAxes, fontsize=11,
           verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.set_xlabel('FD (MW)', fontsize=11, fontweight='bold')
    ax.set_ylabel('R (MW)', fontsize=11, fontweight='bold')
    ax.set_title('Scatter: FD vs R', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'distribuicoes.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] Gráfico salvo: distribuicoes.png")
    
    # Salvar estatísticas descritivas
    stats_df = df[['FD', 'R']].describe().T
    stats_df.to_csv(OUTPUT_DIR / 'estatisticas_descritivas.csv')
    print("  [OK] CSV salvo: estatisticas_descritivas.csv")

def gerar_series_temporais(df):
    """Gera gráficos de séries temporais."""
    
    print("\n" + "="*80)
    print("  ANÁLISE 5: SÉRIES TEMPORAIS")
    print("="*80 + "\n")
    
    # Criar figura
    fig, axes = plt.subplots(3, 1, figsize=(18, 14))
    fig.suptitle('Séries Temporais: FD vs R', fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Série temporal completa (agregada diariamente)
    ax = axes[0]
    df_diario = df.groupby(df['din_instante'].dt.date).agg({
        'FD': 'mean',
        'R': 'mean'
    }).reset_index()
    df_diario.columns = ['data', 'FD', 'R']
    df_diario['data'] = pd.to_datetime(df_diario['data'])
    
    ax.plot(df_diario['data'], df_diario['FD'], label='FD (Fio d\'água)', 
           linewidth=1.5, color='steelblue', alpha=0.8)
    ax.plot(df_diario['data'], df_diario['R'], label='R (Reservatório)', 
           linewidth=1.5, color='coral', alpha=0.8)
    
    ax.set_xlabel('Data', fontsize=12, fontweight='bold')
    ax.set_ylabel('Geração Média Diária (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Série Temporal Completa (Média Diária)', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # 2. Médias móveis de 30 dias
    ax = axes[1]
    df_diario['FD_MA30'] = df_diario['FD'].rolling(window=30, center=True).mean()
    df_diario['R_MA30'] = df_diario['R'].rolling(window=30, center=True).mean()
    
    ax.plot(df_diario['data'], df_diario['FD_MA30'], label='FD (Média Móvel 30d)', 
           linewidth=2.5, color='steelblue')
    ax.plot(df_diario['data'], df_diario['R_MA30'], label='R (Média Móvel 30d)', 
           linewidth=2.5, color='coral')
    
    ax.set_xlabel('Data', fontsize=12, fontweight='bold')
    ax.set_ylabel('Geração (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Tendência: Média Móvel de 30 Dias', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # 3. Razão FD/R ao longo do tempo
    ax = axes[2]
    df_diario['razao_FD_R'] = df_diario['FD'] / df_diario['R']
    df_diario['razao_MA30'] = df_diario['razao_FD_R'].rolling(window=30, center=True).mean()
    
    ax.plot(df_diario['data'], df_diario['razao_FD_R'], 
           linewidth=1, alpha=0.3, color='gray', label='Razão diária')
    ax.plot(df_diario['data'], df_diario['razao_MA30'], 
           linewidth=2.5, color='purple', label='Razão (MA 30d)')
    ax.axhline(y=1, color='red', linestyle='--', linewidth=2, label='FD = R')
    
    ax.set_xlabel('Data', fontsize=12, fontweight='bold')
    ax.set_ylabel('Razão FD/R', fontsize=12, fontweight='bold')
    ax.set_title('Razão Fio d\'água / Reservatório ao Longo do Tempo', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'series_temporais.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] Gráfico salvo: series_temporais.png")
    
    # Salvar dados diários
    df_diario.to_csv(OUTPUT_DIR / 'dados_diarios.csv', index=False)
    print("  [OK] CSV salvo: dados_diarios.csv")

def gerar_relatorio_resumo(df):
    """Gera relatório resumo em texto."""
    
    print("\n" + "="*80)
    print("  GERANDO RELATÓRIO RESUMO")
    print("="*80 + "\n")
    
    relatorio = []
    relatorio.append("="*80)
    relatorio.append("RELATÓRIO DE ANÁLISE: HIDRELÉTRICAS FD vs R")
    relatorio.append("="*80)
    relatorio.append("")
    
    # Informações gerais
    relatorio.append("1. INFORMAÇÕES GERAIS")
    relatorio.append("-" * 80)
    relatorio.append(f"Período analisado: {df['din_instante'].min()} até {df['din_instante'].max()}")
    relatorio.append(f"Total de registros: {len(df):,}")
    relatorio.append(f"Anos analisados: {', '.join(map(str, sorted(df['ano'].unique())))}")
    relatorio.append("")
    
    # Estatísticas FD
    relatorio.append("2. FIOS D'ÁGUA (FD)")
    relatorio.append("-" * 80)
    relatorio.append(f"Média:       {df['FD'].mean():>12,.2f} MW")
    relatorio.append(f"Desvio:      {df['FD'].std():>12,.2f} MW")
    relatorio.append(f"Mínimo:      {df['FD'].min():>12,.2f} MW")
    relatorio.append(f"Máximo:      {df['FD'].max():>12,.2f} MW")
    relatorio.append(f"Mediana:     {df['FD'].median():>12,.2f} MW")
    relatorio.append("")
    
    # Estatísticas R
    relatorio.append("3. RESERVATÓRIOS (R)")
    relatorio.append("-" * 80)
    relatorio.append(f"Média:       {df['R'].mean():>12,.2f} MW")
    relatorio.append(f"Desvio:      {df['R'].std():>12,.2f} MW")
    relatorio.append(f"Mínimo:      {df['R'].min():>12,.2f} MW")
    relatorio.append(f"Máximo:      {df['R'].max():>12,.2f} MW")
    relatorio.append(f"Mediana:     {df['R'].median():>12,.2f} MW")
    relatorio.append("")
    
    # Comparações
    relatorio.append("4. COMPARAÇÕES")
    relatorio.append("-" * 80)
    razao_media = df['FD'].mean() / df['R'].mean()
    corr = df['FD'].corr(df['R'])
    relatorio.append(f"Razão média FD/R:         {razao_media:.3f}")
    relatorio.append(f"Correlação FD vs R:       {corr:.3f}")
    relatorio.append(f"Contribuição FD (média):  {df['FD'].mean() / (df['FD'].mean() + df['R'].mean()) * 100:.1f}%")
    relatorio.append(f"Contribuição R (média):   {df['R'].mean() / (df['FD'].mean() + df['R'].mean()) * 100:.1f}%")
    relatorio.append("")
    
    # Top 5 meses
    relatorio.append("5. TOP 5 MESES - MAIORES VALORES MÉDIOS")
    relatorio.append("-" * 80)
    df_mensal = df.groupby(['ano', 'mes']).agg({'FD': 'mean', 'R': 'mean'}).reset_index()
    df_mensal = df_mensal.sort_values('FD', ascending=False)
    
    relatorio.append("FD (Fio d'água):")
    for i, row in df_mensal.head(5).iterrows():
        relatorio.append(f"  {int(row['ano'])}-{int(row['mes']):02d}: {row['FD']:,.0f} MW")
    relatorio.append("")
    
    df_mensal = df_mensal.sort_values('R', ascending=False)
    relatorio.append("R (Reservatório):")
    for i, row in df_mensal.head(5).iterrows():
        relatorio.append(f"  {int(row['ano'])}-{int(row['mes']):02d}: {row['R']:,.0f} MW")
    relatorio.append("")
    
    relatorio.append("="*80)
    relatorio.append("FIM DO RELATÓRIO")
    relatorio.append("="*80)
    
    # Salvar relatório
    relatorio_texto = '\n'.join(relatorio)
    with open(OUTPUT_DIR / 'RELATORIO_RESUMO.txt', 'w', encoding='utf-8') as f:
        f.write(relatorio_texto)
    
    print("  [OK] Relatório salvo: RELATORIO_RESUMO.txt")
    print("\n" + relatorio_texto)

def main():
    """Função principal."""
    
    print("\n" + "="*80)
    print("  ANÁLISE DETALHADA: HIDRELÉTRICAS FD vs R")
    print("="*80)
    
    # Carregar dados
    df = carregar_dados()
    
    if df is None:
        return
    
    # Gerar análises
    gerar_analise_mensal(df)
    gerar_perfil_diario(df)
    gerar_perfil_horario(df)
    gerar_distribuicoes(df)
    gerar_series_temporais(df)
    gerar_relatorio_resumo(df)
    
    print("\n" + "="*80)
    print("  ANÁLISE CONCLUÍDA!")
    print("="*80)
    print(f"\nTodos os arquivos foram salvos em:")
    print(f"  {OUTPUT_DIR}")
    print("\nArquivos gerados:")
    for arquivo in sorted(OUTPUT_DIR.glob('*')):
        print(f"  - {arquivo.name}")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()





