"""
Comparação: Carga Líquida Histórica vs Simulada (Mini DESSEM)
==============================================================

Compara dois conceitos de carga líquida:

1. HISTÓRICA (dados reais detalhados):
   Carga Líquida = Hidro Reservatório + Térmica Flexível

2. SIMULADA (modelo mini_dessem):
   Carga Líquida = Carga - Renováveis - Inflexível - Hidro FD
   
Ambas devem ser iguais, pois:
   Carga = Renováveis + Inflexível + Hidro FD + Hidro Reserv + Térmica Flex
   
   Portanto:
   Carga - Renováveis - Inflexível - Hidro FD = Hidro Reserv + Térmica Flex
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Diretórios
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")

def carregar_historica():
    """Carrega carga líquida histórica (dados reais)."""
    print("\n[1/3] Carregando carga líquida HISTÓRICA...")
    
    path = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
    df = pd.read_parquet(path)
    
    print(f"     Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    print(f"     Registros: {len(df):,}")
    print(f"     Média: {df['carga_liquida_historica'].mean():,.0f} MW")
    
    return df

def carregar_simulada():
    """Carrega carga líquida simulada (mini_dessem)."""
    print("\n[2/3] Carregando carga líquida SIMULADA (mini_dessem)...")
    
    # Buscar arquivo mais recente automaticamente
    resultados_dir = MINI_DESSEM_DIR / "output" / "resultados"
    arquivos_parquet = sorted(resultados_dir.glob("resultados_simulacao_*.parquet"))
    
    if not arquivos_parquet:
        raise FileNotFoundError(f"Nenhum arquivo de resultado encontrado em {resultados_dir}")
    
    path = arquivos_parquet[-1]  # Pegar o mais recente
    print(f"     Arquivo: {path.name}")
    
    df = pd.read_parquet(path)
    
    # Criar timestamp para merge
    df['din_instante'] = pd.to_datetime(
        df['ano'].astype(str) + '-' + 
        df['mes'].astype(str).str.zfill(2) + '-' + 
        df['dia'].astype(str).str.zfill(2) + ' ' + 
        df['hora'].astype(str).str.zfill(2) + ':00:00'
    )
    
    print(f"     Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    print(f"     Registros: {len(df):,}")
    print(f"     Média: {df['carga_liquida'].mean():,.0f} MW")
    
    return df

def comparar():
    """Compara as duas bases."""
    print("\n" + "="*80)
    print("  COMPARAÇÃO: Histórica vs Simulada")
    print("="*80)
    
    df_hist = carregar_historica()
    df_sim = carregar_simulada()
    
    # Merge nas timestamps
    print("\n[3/3] Fazendo merge temporal...")
    
    df_merged = pd.merge(
        df_hist[['din_instante', 'ano', 'mes', 'hora', 'FD', 'R', 'termica_flexivel', 'carga_liquida_historica']],
        df_sim[['din_instante', 'simulacao', 'carga_liquida', 'val_gerhidro_reservatorio', 'val_term_despacho']],
        on='din_instante',
        how='inner'
    )
    
    print(f"     Registros com overlap: {len(df_merged):,}")
    
    if len(df_merged) == 0:
        print("\n[!] Sem overlap temporal entre bases!")
        print(f"    Histórica: {df_hist['din_instante'].min()} - {df_hist['din_instante'].max()}")
        print(f"    Simulada:  {df_sim['din_instante'].min()} - {df_sim['din_instante'].max()}")
        return
    
    # Agrupar simulações (pegar média)
    df_merged_avg = df_merged.groupby('din_instante').agg({
        'ano': 'first',
        'mes': 'first',
        'hora': 'first',
        'FD': 'first',
        'R': 'first',
        'termica_flexivel': 'first',
        'carga_liquida_historica': 'first',
        'carga_liquida': 'mean',  # Média dos cenários
        'val_gerhidro_reservatorio': 'mean',
        'val_term_despacho': 'mean'
    }).reset_index()
    
    # Calcular diferenças
    df_merged_avg['diff_absoluta'] = df_merged_avg['carga_liquida'] - df_merged_avg['carga_liquida_historica']
    df_merged_avg['diff_percentual'] = (df_merged_avg['diff_absoluta'] / df_merged_avg['carga_liquida_historica']) * 100
    
    # Estatísticas
    print("\n" + "="*80)
    print("  ESTATÍSTICAS DA COMPARAÇÃO")
    print("="*80)
    
    print(f"\nCarga Líquida Histórica:")
    print(f"  Média: {df_merged_avg['carga_liquida_historica'].mean():,.0f} MW")
    print(f"  Std:   {df_merged_avg['carga_liquida_historica'].std():,.0f} MW")
    
    print(f"\nCarga Líquida Simulada (média cenários):")
    print(f"  Média: {df_merged_avg['carga_liquida'].mean():,.0f} MW")
    print(f"  Std:   {df_merged_avg['carga_liquida'].std():,.0f} MW")
    
    print(f"\nDiferença Absoluta (Simulada - Histórica):")
    print(f"  Média: {df_merged_avg['diff_absoluta'].mean():,.0f} MW")
    print(f"  Std:   {df_merged_avg['diff_absoluta'].std():,.0f} MW")
    print(f"  Min/Max: {df_merged_avg['diff_absoluta'].min():,.0f} / {df_merged_avg['diff_absoluta'].max():,.0f} MW")
    
    print(f"\nDiferença Percentual:")
    print(f"  Média: {df_merged_avg['diff_percentual'].mean():.1f}%")
    print(f"  Std:   {df_merged_avg['diff_percentual'].std():.1f}%")
    
    # Gráficos
    output_dir = CARGA_LIQ_DIR / "Output" / "comparacao"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Scatter Plot: Histórica vs Simulada
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle('Comparação: Carga Líquida Histórica vs Simulada', fontsize=16, fontweight='bold')
    
    ax = axes[0]
    ax.scatter(df_merged_avg['carga_liquida_historica'], df_merged_avg['carga_liquida'], 
              alpha=0.5, s=20, edgecolor='k', linewidth=0.3)
    
    # Linha x=y
    lim_min = min(df_merged_avg['carga_liquida_historica'].min(), df_merged_avg['carga_liquida'].min())
    lim_max = max(df_merged_avg['carga_liquida_historica'].max(), df_merged_avg['carga_liquida'].max())
    ax.plot([lim_min, lim_max], [lim_min, lim_max], 'r--', linewidth=2, label='x=y (perfeito)')
    
    ax.set_xlabel('Carga Líquida Histórica (MW)', fontsize=12)
    ax.set_ylabel('Carga Líquida Simulada (MW)', fontsize=12)
    ax.set_title('Scatter Plot', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. Distribuição das diferenças
    ax = axes[1]
    ax.hist(df_merged_avg['diff_absoluta'], bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(df_merged_avg['diff_absoluta'].mean(), color='red', linestyle='--', linewidth=2, 
              label=f'Média: {df_merged_avg["diff_absoluta"].mean():.0f} MW')
    ax.axvline(0, color='green', linestyle=':', linewidth=2, label='Zero')
    ax.set_xlabel('Diferença (Simulada - Histórica) [MW]', fontsize=12)
    ax.set_ylabel('Frequência', fontsize=12)
    ax.set_title('Distribuição das Diferenças', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'comparacao_scatter_diff.png', dpi=150, bbox_inches='tight')
    print(f"\n[OK] Gráfico salvo: comparacao_scatter_diff.png")
    plt.close()
    
    # 3. Série temporal
    fig, axes = plt.subplots(2, 1, figsize=(18, 10))
    fig.suptitle('Evolução Temporal: Histórica vs Simulada', fontsize=16, fontweight='bold')
    
    # Pegar amostra (últimos 30 dias)
    df_sample = df_merged_avg.sort_values('din_instante').tail(24*30)
    
    ax = axes[0]
    ax.plot(df_sample['din_instante'], df_sample['carga_liquida_historica'], 
           label='Histórica (Real)', linewidth=1.5, alpha=0.8)
    ax.plot(df_sample['din_instante'], df_sample['carga_liquida'], 
           label='Simulada (Mini DESSEM)', linewidth=1.5, alpha=0.8)
    ax.set_ylabel('MW', fontsize=12)
    ax.set_title('Séries Temporais (últimos 30 dias)', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    ax = axes[1]
    ax.plot(df_sample['din_instante'], df_sample['diff_absoluta'], 
           color='red', linewidth=1.5, alpha=0.8)
    ax.axhline(0, color='green', linestyle=':', linewidth=1)
    ax.set_xlabel('Data', fontsize=12)
    ax.set_ylabel('Diferença (MW)', fontsize=12)
    ax.set_title('Diferença (Simulada - Histórica)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'comparacao_temporal.png', dpi=150, bbox_inches='tight')
    print(f"[OK] Gráfico salvo: comparacao_temporal.png")
    plt.close()
    
    # 4. Por mês
    fig, ax = plt.subplots(1, 1, figsize=(16, 7))
    
    comp_mes = df_merged_avg.groupby('mes').agg({
        'carga_liquida_historica': 'mean',
        'carga_liquida': 'mean',
        'diff_absoluta': 'mean'
    })
    
    x = np.arange(len(comp_mes))
    width = 0.35
    
    ax.bar(x - width/2, comp_mes['carga_liquida_historica'], width, 
          label='Histórica', alpha=0.8, color='steelblue')
    ax.bar(x + width/2, comp_mes['carga_liquida'], width, 
          label='Simulada', alpha=0.8, color='orange')
    
    ax.set_xlabel('Mês', fontsize=12)
    ax.set_ylabel('Carga Líquida Média (MW)', fontsize=12)
    ax.set_title('Comparação Média por Mês', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(comp_mes.index)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'comparacao_mensal.png', dpi=150, bbox_inches='tight')
    print(f"[OK] Gráfico salvo: comparacao_mensal.png")
    plt.close()
    
    # Salvar CSV com comparação
    csv_path = output_dir / 'comparacao_detalhada.csv'
    df_merged_avg.to_csv(csv_path, index=False)
    print(f"\n[OK] CSV detalhado salvo: comparacao_detalhada.csv")
    
    print("\n" + "="*80)
    print("  [OK] COMPARAÇÃO CONCLUÍDA!")
    print("="*80)
    print(f"\nResultados em: {output_dir}")
    
    return df_merged_avg

if __name__ == '__main__':
    df_comp = comparar()

