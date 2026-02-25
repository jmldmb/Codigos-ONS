"""
Comparação Completa por Ano - Modelo V4
========================================

Compara carga líquida histórica vs simulada (com modelo v4)
Gera análises separadas por ano: 2023, 2024, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuração visual
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 10

# Diretórios
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "comparacao_v4"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def carregar_dados():
    """Carrega dados históricos e simulados."""
    
    print("\n" + "="*80)
    print("  CARREGANDO DADOS")
    print("="*80)
    
    # 1. Histórico
    print("\n[1/2] Carga líquida HISTÓRICA...")
    path_hist = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
    df_hist = pd.read_parquet(path_hist)
    print(f"     Período: {df_hist['din_instante'].min()} até {df_hist['din_instante'].max()}")
    print(f"     Registros: {len(df_hist):,}")
    
    # 2. Simulado (arquivo mais recente com v4)
    print("\n[2/2] Carga líquida SIMULADA (mini_dessem v4)...")
    resultados_dir = MINI_DESSEM_DIR / "output" / "resultados"
    arquivos = sorted(resultados_dir.glob("resultados_simulacao_*.parquet"))
    
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo de resultado em {resultados_dir}")
    
    path_sim = arquivos[-1]  # Mais recente
    print(f"     Arquivo: {path_sim.name}")
    
    df_sim = pd.read_parquet(path_sim)
    
    # Criar timestamp
    df_sim['din_instante'] = pd.to_datetime(
        df_sim['ano'].astype(str) + '-' + 
        df_sim['mes'].astype(str).str.zfill(2) + '-' + 
        df_sim['dia'].astype(str).str.zfill(2) + ' ' + 
        df_sim['hora'].astype(str).str.zfill(2) + ':00:00'
    )
    
    print(f"     Período: {df_sim['din_instante'].min()} até {df_sim['din_instante'].max()}")
    print(f"     Registros: {len(df_sim):,}")
    print(f"     Cenários: {df_sim['simulacao'].nunique()}")
    
    return df_hist, df_sim

def merge_e_calcular(df_hist, df_sim):
    """Faz merge e calcula diferenças."""
    
    print("\n" + "="*80)
    print("  PROCESSANDO DADOS")
    print("="*80)
    
    # Agregar simulações por hora (média dos cenários)
    print("\n[1/2] Agregando cenários...")
    df_sim_agg = df_sim.groupby('din_instante').agg({
        'carga_liquida': 'mean',
        'val_gerhidro_reservatorio': 'mean',
        'val_term_despacho': 'mean',
        'ano': 'first',
        'mes': 'first',
        'hora': 'first'
    }).reset_index()
    
    # Merge
    print("[2/2] Fazendo merge temporal...")
    df = pd.merge(
        df_hist[['din_instante', 'ano', 'mes', 'hora', 'carga_liquida_historica', 'R', 'termica_flexivel']],
        df_sim_agg,
        on='din_instante',
        how='inner',
        suffixes=('_hist', '_sim')
    )
    
    # Calcular diferenças
    df['diff_carga_liq'] = df['carga_liquida'] - df['carga_liquida_historica']
    df['diff_carga_liq_pct'] = (df['diff_carga_liq'] / df['carga_liquida_historica'].abs()) * 100
    df['diff_abs'] = df['diff_carga_liq'].abs()
    
    print(f"\nRegistros após merge: {len(df):,}")
    print(f"Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    
    return df

def analisar_por_ano(df, ano):
    """Análise detalhada para um ano específico."""
    
    print(f"\n{'='*80}")
    print(f"  ANÁLISE: {ano}")
    print(f"{'='*80}")
    
    df_ano = df[df['ano_hist'] == ano].copy()
    
    if len(df_ano) == 0:
        print(f"\n[AVISO] Nenhum dado para {ano}")
        return
    
    print(f"\nRegistros: {len(df_ano):,}")
    print(f"\nCarga Líquida - Estatísticas:")
    print(f"  Histórica: {df_ano['carga_liquida_historica'].mean():,.0f} MW (±{df_ano['carga_liquida_historica'].std():,.0f})")
    print(f"  Simulada:  {df_ano['carga_liquida'].mean():,.0f} MW (±{df_ano['carga_liquida'].std():,.0f})")
    print(f"\nErro:")
    print(f"  Média:     {df_ano['diff_carga_liq'].mean():,.0f} MW ({df_ano['diff_carga_liq_pct'].mean():.2f}%)")
    print(f"  MAE:       {df_ano['diff_abs'].mean():,.0f} MW ({(df_ano['diff_abs'] / df_ano['carga_liquida_historica'].abs()).mean() * 100:.2f}%)")
    print(f"  RMSE:      {np.sqrt((df_ano['diff_carga_liq']**2).mean()):,.0f} MW")
    
    # Erro por mês
    print(f"\nErro por Mês ({ano}):")
    erro_mensal = df_ano.groupby('mes_hist').agg({
        'diff_carga_liq': 'mean',
        'diff_abs': 'mean',
        'carga_liquida_historica': 'mean'
    })
    erro_mensal['mae_pct'] = (erro_mensal['diff_abs'] / erro_mensal['carga_liquida_historica'].abs()) * 100
    
    for mes in range(1, 13):
        if mes in erro_mensal.index:
            row = erro_mensal.loc[mes]
            print(f"  {mes:2d}: MAE = {row['diff_abs']:6,.0f} MW ({row['mae_pct']:5.2f}%) | Viés = {row['diff_carga_liq']:+7,.0f} MW")
    
    # Gerar gráficos
    gerar_graficos_ano(df_ano, ano)

def gerar_graficos_ano(df, ano):
    """Gera gráficos para um ano específico."""
    
    print(f"\nGerando gráficos para {ano}...")
    
    # 1. Scatter: Real vs Simulado
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'Comparação Carga Líquida: Histórico vs Simulado (V4) - {ano}', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1.1 Scatter geral
    ax = axes[0, 0]
    ax.scatter(df['carga_liquida_historica'], df['carga_liquida'], 
               alpha=0.3, s=10, c=df['mes_hist'], cmap='tab20')
    
    lims = [
        min(df['carga_liquida_historica'].min(), df['carga_liquida'].min()),
        max(df['carga_liquida_historica'].max(), df['carga_liquida'].max())
    ]
    ax.plot(lims, lims, 'r--', alpha=0.5, lw=2, label='Ideal (1:1)')
    ax.set_xlabel('Carga Líquida Histórica (MW)', fontsize=11)
    ax.set_ylabel('Carga Líquida Simulada V4 (MW)', fontsize=11)
    ax.set_title('Scatter: Real vs Simulado', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Correlação
    corr = df['carga_liquida_historica'].corr(df['carga_liquida'])
    ax.text(0.05, 0.95, f'R² = {corr**2:.4f}', transform=ax.transAxes, 
            fontsize=11, verticalalignment='top', 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 1.2 Distribuição do erro
    ax = axes[0, 1]
    ax.hist(df['diff_carga_liq'], bins=50, alpha=0.7, edgecolor='black')
    ax.axvline(0, color='red', linestyle='--', lw=2, label='Zero')
    ax.axvline(df['diff_carga_liq'].mean(), color='green', linestyle='--', lw=2, 
               label=f'Média = {df["diff_carga_liq"].mean():.0f} MW')
    ax.set_xlabel('Erro (Simulado - Real) [MW]', fontsize=11)
    ax.set_ylabel('Frequência', fontsize=11)
    ax.set_title('Distribuição do Erro', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 1.3 Erro por hora
    ax = axes[1, 0]
    erro_hora = df.groupby('hora_hist')['diff_carga_liq'].agg(['mean', 'std'])
    ax.plot(erro_hora.index, erro_hora['mean'], 'o-', lw=2, label='Média')
    ax.fill_between(erro_hora.index, 
                     erro_hora['mean'] - erro_hora['std'],
                     erro_hora['mean'] + erro_hora['std'],
                     alpha=0.3, label='±1σ')
    ax.axhline(0, color='red', linestyle='--', lw=1)
    ax.set_xlabel('Hora', fontsize=11)
    ax.set_ylabel('Erro (Simulado - Real) [MW]', fontsize=11)
    ax.set_title('Erro por Hora do Dia', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # 1.4 MAE por mês
    ax = axes[1, 1]
    erro_mensal = df.groupby('mes_hist')['diff_abs'].mean()
    bars = ax.bar(erro_mensal.index, erro_mensal.values, alpha=0.7, edgecolor='black')
    
    # Colorir meses críticos (jun, set, dez)
    for i, mes in enumerate(erro_mensal.index):
        if mes in [6, 9, 12]:
            bars[i-1].set_color('salmon')
            bars[i-1].set_label('Mês Crítico' if mes == 6 else '')
    
    ax.set_xlabel('Mês', fontsize=11)
    ax.set_ylabel('MAE (MW)', fontsize=11)
    ax.set_title('Erro Absoluto Médio por Mês', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(1, 13))
    if 6 in erro_mensal.index or 9 in erro_mensal.index or 12 in erro_mensal.index:
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f'comparacao_{ano}.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Heatmap de erro por hora e mês
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    pivot = df.pivot_table(
        values='diff_carga_liq',
        index='hora_hist',
        columns='mes_hist',
        aggfunc='mean'
    )
    
    sns.heatmap(pivot, annot=True, fmt='.0f', cmap='RdBu_r', center=0,
                cbar_kws={'label': 'Erro (MW)'}, ax=ax, linewidths=0.5)
    ax.set_xlabel('Mês', fontsize=12)
    ax.set_ylabel('Hora', fontsize=12)
    ax.set_title(f'Heatmap de Erro: Simulado - Real ({ano})', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f'heatmap_erro_{ano}.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"     [OK] comparacao_{ano}.png")
    print(f"     [OK] heatmap_erro_{ano}.png")

def gerar_comparacao_anos(df):
    """Gera comparação entre anos."""
    
    print(f"\n{'='*80}")
    print(f"  COMPARAÇÃO ENTRE ANOS")
    print(f"{'='*80}")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Comparação Multi-Ano: V4 vs Histórico', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    anos_disponiveis = sorted(df['ano_hist'].unique())
    cores = plt.cm.Set2(np.linspace(0, 1, len(anos_disponiveis)))
    
    # 1. MAE por ano
    ax = axes[0, 0]
    mae_por_ano = df.groupby('ano_hist')['diff_abs'].mean()
    bars = ax.bar(mae_por_ano.index, mae_por_ano.values, color=cores, 
                   alpha=0.7, edgecolor='black', width=0.6)
    ax.set_xlabel('Ano', fontsize=12)
    ax.set_ylabel('MAE (MW)', fontsize=12)
    ax.set_title('Erro Absoluto Médio por Ano', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars, mae_por_ano.values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 2. Distribuição do erro por ano
    ax = axes[0, 1]
    for i, ano in enumerate(anos_disponiveis):
        df_ano = df[df['ano_hist'] == ano]
        ax.hist(df_ano['diff_carga_liq'], bins=40, alpha=0.5, 
                label=f'{ano}', color=cores[i], edgecolor='black')
    ax.axvline(0, color='red', linestyle='--', lw=2)
    ax.set_xlabel('Erro (MW)', fontsize=12)
    ax.set_ylabel('Frequência', fontsize=12)
    ax.set_title('Distribuição do Erro por Ano', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Erro por mês (todos os anos)
    ax = axes[1, 0]
    for i, ano in enumerate(anos_disponiveis):
        df_ano = df[df['ano_hist'] == ano]
        erro_mensal = df_ano.groupby('mes_hist')['diff_abs'].mean()
        ax.plot(erro_mensal.index, erro_mensal.values, 'o-', 
                label=f'{ano}', color=cores[i], lw=2, markersize=6)
    
    # Destacar meses críticos
    for mes in [6, 9, 12]:
        ax.axvline(mes, color='red', alpha=0.2, linestyle='--', lw=1)
    
    ax.set_xlabel('Mês', fontsize=12)
    ax.set_ylabel('MAE (MW)', fontsize=12)
    ax.set_title('Erro por Mês (Todos os Anos)', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(1, 13))
    
    # 4. Boxplot por ano
    ax = axes[1, 1]
    data_box = [df[df['ano_hist'] == ano]['diff_carga_liq'].values 
                for ano in anos_disponiveis]
    bp = ax.boxplot(data_box, labels=anos_disponiveis, patch_artist=True)
    
    for patch, cor in zip(bp['boxes'], cores):
        patch.set_facecolor(cor)
        patch.set_alpha(0.7)
    
    ax.axhline(0, color='red', linestyle='--', lw=2)
    ax.set_xlabel('Ano', fontsize=12)
    ax.set_ylabel('Erro (MW)', fontsize=12)
    ax.set_title('Distribuição do Erro por Ano (Boxplot)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'comparacao_multi_ano.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n     [OK] comparacao_multi_ano.png")

def main():
    """Função principal."""
    
    print("\n" + "="*80)
    print("  COMPARAÇÃO COMPLETA POR ANO - MODELO V4")
    print("="*80)
    
    # Carregar dados
    df_hist, df_sim = carregar_dados()
    
    # Merge e calcular
    df = merge_e_calcular(df_hist, df_sim)
    
    # Salvar CSV completo
    csv_path = OUTPUT_DIR / "comparacao_completa_v4.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n[OK] Dados salvos: {csv_path}")
    
    # Análise por ano
    anos_disponiveis = sorted(df['ano_hist'].unique())
    print(f"\nAnos disponíveis: {anos_disponiveis}")
    
    for ano in anos_disponiveis:
        analisar_por_ano(df, ano)
    
    # Comparação entre anos
    if len(anos_disponiveis) > 1:
        gerar_comparacao_anos(df)
    
    print("\n" + "="*80)
    print(f"  ANÁLISE CONCLUÍDA!")
    print("="*80)
    print(f"\nResultados salvos em: {OUTPUT_DIR}")
    print("\nArquivos gerados:")
    print(f"  - comparacao_completa_v4.csv")
    for ano in anos_disponiveis:
        print(f"  - comparacao_{ano}.png")
        print(f"  - heatmap_erro_{ano}.png")
    if len(anos_disponiveis) > 1:
        print(f"  - comparacao_multi_ano.png")
    
    print("\n[OK] Concluido!")

if __name__ == "__main__":
    main()

