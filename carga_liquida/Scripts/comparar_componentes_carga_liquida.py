"""
Comparação Direta das Componentes de Carga Líquida
===================================================

Compara diretamente:
1. Hidro Reservatório: Real vs Simulado
2. Térmica Flexível: Real vs Simulado

Carga Líquida = Hidro R + Térmica Flex (em ambas as bases)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")

def carregar_dados():
    """Carrega dados históricos processados - BASE COMPLETA."""
    
    print("="*80)
    print("  COMPARACAO COMPLETA: Hidro R e Termica Flex (Real vs Simulado)")
    print("="*80)
    
    # Usar base completa (33k registros)
    csv_path = CARGA_LIQ_DIR / "Output" / "comparacao" / "comparacao_detalhada.csv"
    
    if not csv_path.exists():
        print("\n[!] Execute primeiro: comparar_carga_liquida.py")
        return None
    
    print("\n[1/1] Carregando BASE COMPLETA (33k registros)...")
    df = pd.read_csv(csv_path)
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    
    # Renomear para padronizar
    rename_map = {
        'carga_liquida_historica': 'carga_liq_real',
        'carga_liquida': 'carga_liq_sim',
        'R': 'hidro_r_real',
        'FD': 'hidro_fd_real',
        'termica_flexivel': 'termica_flex_real',
        'val_gerhidro_reservatorio': 'hidro_r_sim',
        'val_term_despacho': 'termica_flex_sim'
    }
    df = df.rename(columns=rename_map)
    
    print(f"     Registros: {len(df):,}")
    print(f"     Periodo: {df['din_instante'].min()} ate {df['din_instante'].max()}")
    
    return df

def analisar_componentes(df):
    """Analisa Hidro R e Térmica Flex separadamente."""
    
    print("\n" + "="*80)
    print("  ANALISE DAS COMPONENTES")
    print("="*80)
    
    # Calcular diferenças
    df['diff_hidro_r'] = df['hidro_r_sim'] - df['hidro_r_real']
    df['diff_termica_flex'] = df['termica_flex_sim'] - df['termica_flex_real']
    df['diff_carga_liq'] = df['carga_liq_sim'] - df['carga_liq_real']
    
    # Estatísticas
    print(f"\nHIDRO RESERVATORIO:")
    print(f"  Real Media:      {df['hidro_r_real'].mean():>10,.0f} MW")
    print(f"  Simulado Media:  {df['hidro_r_sim'].mean():>10,.0f} MW")
    print(f"  Diferenca:       {df['diff_hidro_r'].mean():>10,.0f} MW ({df['diff_hidro_r'].mean() / df['hidro_r_real'].mean() * 100:>6.1f}%)")
    print(f"  Std Diferenca:   {df['diff_hidro_r'].std():>10,.0f} MW")
    
    print(f"\nTERMICA FLEXIVEL:")
    print(f"  Real Media:      {df['termica_flex_real'].mean():>10,.0f} MW")
    print(f"  Simulado Media:  {df['termica_flex_sim'].mean():>10,.0f} MW")
    print(f"  Diferenca:       {df['diff_termica_flex'].mean():>10,.0f} MW ({df['diff_termica_flex'].mean() / df['termica_flex_real'].mean() * 100:>6.1f}%)")
    print(f"  Std Diferenca:   {df['diff_termica_flex'].std():>10,.0f} MW")
    
    print(f"\nCARGA LIQUIDA (TOTAL):")
    print(f"  Real Media:      {df['carga_liq_real'].mean():>10,.0f} MW")
    print(f"  Simulado Media:  {df['carga_liq_sim'].mean():>10,.0f} MW")
    print(f"  Diferenca:       {df['diff_carga_liq'].mean():>10,.0f} MW ({df['diff_carga_liq'].mean() / df['carga_liq_real'].mean() * 100:>6.1f}%)")
    
    # Decomposição do erro
    print(f"\n" + "-"*80)
    print(f"  DECOMPOSICAO DO ERRO DE CARGA LIQUIDA:")
    print("-"*80)
    
    contrib_hidro_r_pct = df['diff_hidro_r'].mean() / df['diff_carga_liq'].mean() * 100 if df['diff_carga_liq'].mean() != 0 else 0
    contrib_termica_pct = df['diff_termica_flex'].mean() / df['diff_carga_liq'].mean() * 100 if df['diff_carga_liq'].mean() != 0 else 0
    
    print(f"  Hidro R:        {df['diff_hidro_r'].mean():>10,.0f} MW ({contrib_hidro_r_pct:>6.1f}%)")
    print(f"  Termica Flex:   {df['diff_termica_flex'].mean():>10,.0f} MW ({contrib_termica_pct:>6.1f}%)")
    print(f"  Total:          {(df['diff_hidro_r'] + df['diff_termica_flex']).mean():>10,.0f} MW")
    
    return df

def gerar_graficos(df):
    """Gera gráficos de comparação direta."""
    
    print("\n" + "="*80)
    print("  GERANDO GRAFICOS")
    print("="*80)
    
    output_dir = CARGA_LIQ_DIR / "Output" / "analise_extremos"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Scatter das componentes
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle('Componentes de Carga Liquida: Real vs Simulado', fontsize=16, fontweight='bold')
    
    # Hidro R
    ax = axes[0]
    ax.scatter(df['hidro_r_real'], df['hidro_r_sim'], alpha=0.6, s=50, 
              color='steelblue', edgecolor='k', linewidth=0.5)
    lim = [0, max(df['hidro_r_real'].max(), df['hidro_r_sim'].max())]
    ax.plot(lim, lim, 'r--', linewidth=2, label='x=y')
    
    # Estatísticas no gráfico
    diff_mean = df['diff_hidro_r'].mean()
    diff_pct = (diff_mean / df['hidro_r_real'].mean() * 100)
    ax.text(0.05, 0.95, f'Erro medio: {diff_mean:,.0f} MW ({diff_pct:.1f}%)',
           transform=ax.transAxes, fontsize=11, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.set_xlabel('Hidro R Real (MW)', fontsize=12)
    ax.set_ylabel('Hidro R Simulado (MW)', fontsize=12)
    ax.set_title('Hidro Reservatorio', fontweight='bold', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Térmica Flex
    ax = axes[1]
    ax.scatter(df['termica_flex_real'], df['termica_flex_sim'], alpha=0.6, s=50,
              color='orange', edgecolor='k', linewidth=0.5)
    lim = [0, max(df['termica_flex_real'].max(), df['termica_flex_sim'].max())]
    ax.plot(lim, lim, 'r--', linewidth=2, label='x=y')
    
    diff_mean = df['diff_termica_flex'].mean()
    diff_pct = (diff_mean / df['termica_flex_real'].mean() * 100) if df['termica_flex_real'].mean() != 0 else 0
    ax.text(0.05, 0.95, f'Erro medio: {diff_mean:,.0f} MW ({diff_pct:.1f}%)',
           transform=ax.transAxes, fontsize=11, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.set_xlabel('Termica Flex Real (MW)', fontsize=12)
    ax.set_ylabel('Termica Flex Simulado (MW)', fontsize=12)
    ax.set_title('Termica Flexivel', fontweight='bold', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'componentes_carga_liquida.png', dpi=150, bbox_inches='tight')
    print(f"\n[OK] componentes_carga_liquida.png")
    plt.close()
    
    # 2. Decomposição por tipo
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Decomposicao do Erro: Hidro R vs Termica Flex', fontsize=16, fontweight='bold')
    
    # Histogramas das diferenças
    ax = axes[0, 0]
    ax.hist(df['diff_hidro_r'], bins=40, color='steelblue', alpha=0.7, edgecolor='black', label='Hidro R')
    ax.axvline(df['diff_hidro_r'].mean(), color='red', linestyle='--', linewidth=2,
              label=f'Media: {df["diff_hidro_r"].mean():.0f} MW')
    ax.axvline(0, color='green', linestyle=':', linewidth=1.5)
    ax.set_xlabel('Diferenca Hidro R (MW)', fontsize=11)
    ax.set_ylabel('Frequencia', fontsize=11)
    ax.set_title('Distribuicao do Erro - Hidro R', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    ax = axes[0, 1]
    ax.hist(df['diff_termica_flex'], bins=40, color='orange', alpha=0.7, edgecolor='black')
    ax.axvline(df['diff_termica_flex'].mean(), color='red', linestyle='--', linewidth=2,
              label=f'Media: {df["diff_termica_flex"].mean():.0f} MW')
    ax.axvline(0, color='green', linestyle=':', linewidth=1.5)
    ax.set_xlabel('Diferenca Termica Flex (MW)', fontsize=11)
    ax.set_ylabel('Frequencia', fontsize=11)
    ax.set_title('Distribuicao do Erro - Termica Flex', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Contribuição relativa
    ax = axes[1, 0]
    categorias = ['Hidro R', 'Termica Flex']
    contribuicoes = [df['diff_hidro_r'].mean(), df['diff_termica_flex'].mean()]
    cores = ['steelblue', 'orange']
    
    bars = ax.bar(categorias, contribuicoes, color=cores, alpha=0.7, edgecolor='black')
    ax.axhline(0, color='black', linewidth=1.5)
    ax.set_ylabel('Diferenca Media (MW)', fontsize=11)
    ax.set_title('Contribuicao Media ao Erro de Carga Liquida', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Anotações
    for bar, val in zip(bars, contribuicoes):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{val:,.0f} MW', ha='center', va='bottom' if val > 0 else 'top',
               fontsize=11, fontweight='bold')
    
    # Correlação entre erros
    ax = axes[1, 1]
    ax.scatter(df['diff_hidro_r'], df['diff_termica_flex'], alpha=0.6, s=50,
              edgecolor='k', linewidth=0.5)
    
    # Linha de correlação
    if len(df) > 1:
        corr = df[['diff_hidro_r', 'diff_termica_flex']].corr().iloc[0, 1]
        ax.text(0.05, 0.95, f'Correlacao: {corr:.3f}',
               transform=ax.transAxes, fontsize=12, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    ax.axhline(0, color='green', linestyle=':', linewidth=1)
    ax.axvline(0, color='green', linestyle=':', linewidth=1)
    ax.set_xlabel('Erro Hidro R (MW)', fontsize=11)
    ax.set_ylabel('Erro Termica Flex (MW)', fontsize=11)
    ax.set_title('Correlacao entre Erros', fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'decomposicao_carga_liquida.png', dpi=150, bbox_inches='tight')
    print(f"[OK] decomposicao_carga_liquida.png")
    plt.close()
    
    # 3. Série temporal (se top N extremos)
    df_sorted = df.sort_values('diff_abs' if 'diff_abs' in df.columns else 'diff_absoluta', ascending=False).head(100).copy()
    df_sorted = df_sorted.sort_values('din_instante')
    
    fig, axes = plt.subplots(3, 1, figsize=(18, 12))
    fig.suptitle('Serie Temporal: Top 100 Extremos (ordenado por tempo)', fontsize=16, fontweight='bold')
    
    # Hidro R
    ax = axes[0]
    ax.plot(df_sorted['din_instante'], df_sorted['hidro_r_real'], 
           label='Real', linewidth=2, alpha=0.8, color='blue')
    ax.plot(df_sorted['din_instante'], df_sorted['hidro_r_sim'], 
           label='Simulado', linewidth=2, alpha=0.8, color='orange')
    ax.fill_between(df_sorted['din_instante'], 
                    df_sorted['hidro_r_real'], df_sorted['hidro_r_sim'],
                    alpha=0.3, color='red', label='Diferenca')
    ax.set_ylabel('Hidro R (MW)', fontsize=11)
    ax.set_title('Hidro Reservatorio: Real vs Simulado', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Térmica Flex
    ax = axes[1]
    ax.plot(df_sorted['din_instante'], df_sorted['termica_flex_real'], 
           label='Real', linewidth=2, alpha=0.8, color='blue')
    ax.plot(df_sorted['din_instante'], df_sorted['termica_flex_sim'], 
           label='Simulado', linewidth=2, alpha=0.8, color='orange')
    ax.fill_between(df_sorted['din_instante'], 
                    df_sorted['termica_flex_real'], df_sorted['termica_flex_sim'],
                    alpha=0.3, color='red', label='Diferenca')
    ax.set_ylabel('Termica Flex (MW)', fontsize=11)
    ax.set_title('Termica Flexivel: Real vs Simulado', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Carga Líquida (soma)
    ax = axes[2]
    ax.plot(df_sorted['din_instante'], df_sorted['carga_liq_real'], 
           label='Real', linewidth=2, alpha=0.8, color='blue')
    ax.plot(df_sorted['din_instante'], df_sorted['carga_liq_sim'], 
           label='Simulado', linewidth=2, alpha=0.8, color='orange')
    ax.fill_between(df_sorted['din_instante'], 
                    df_sorted['carga_liq_real'], df_sorted['carga_liq_sim'],
                    alpha=0.3, color='red', label='Diferenca')
    ax.set_xlabel('Data', fontsize=11)
    ax.set_ylabel('Carga Liquida (MW)', fontsize=11)
    ax.set_title('Carga Liquida Total (Hidro R + Termica Flex)', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_componentes.png', dpi=150, bbox_inches='tight')
    print(f"[OK] temporal_componentes.png")
    plt.close()
    
    # 4. Waterfall/Decomposição
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    
    real_total = df['carga_liq_real'].mean()
    hidro_r_contrib = df['diff_hidro_r'].mean()
    termica_contrib = df['diff_termica_flex'].mean()
    sim_total = df['carga_liq_sim'].mean()
    
    categorias = ['Carga Liq\nReal', 'Erro\nHidro R', 'Erro\nTermica', 'Carga Liq\nSimulada']
    valores = [real_total, hidro_r_contrib, termica_contrib, sim_total]
    cores = ['blue', 'red' if hidro_r_contrib < 0 else 'green',
            'red' if termica_contrib < 0 else 'green', 'orange']
    
    x_pos = np.arange(len(categorias))
    bars = ax.bar(x_pos, valores, color=cores, alpha=0.7, edgecolor='black', linewidth=2)
    
    ax.axhline(0, color='black', linewidth=1)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categorias, fontsize=11)
    ax.set_ylabel('MW', fontsize=12)
    ax.set_title('Decomposicao: Real → Simulado', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Anotações
    for bar, val in zip(bars, valores):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{val:,.0f}', ha='center', va='bottom' if val > 0 else 'top',
               fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'waterfall_componentes.png', dpi=150, bbox_inches='tight')
    print(f"[OK] waterfall_componentes.png")
    plt.close()
    
    print("\n" + "="*80)
    print("  [OK] ANALISE CONCLUIDA!")
    print("="*80)
    print(f"\nResultados em: {output_dir}")
    
    return df

if __name__ == '__main__':
    df = carregar_dados()
    if df is not None:
        df = analisar_componentes(df)
        df = gerar_graficos(df)
        
        print(f"\n{'='*80}")
        print("  CONCLUSAO")
        print("="*80)
        
        # Identificar componente dominante
        erro_hidro = abs(df['diff_hidro_r'].mean())
        erro_termica = abs(df['diff_termica_flex'].mean())
        
        if erro_hidro > erro_termica:
            print(f"\n  >> ERRO DOMINANTE: Hidro Reservatorio")
            print(f"     Hidro R: {df['diff_hidro_r'].mean():,.0f} MW")
            print(f"     Termica: {df['diff_termica_flex'].mean():,.0f} MW")
        else:
            print(f"\n  >> ERRO DOMINANTE: Termica Flexivel")
            print(f"     Termica: {df['diff_termica_flex'].mean():,.0f} MW")
            print(f"     Hidro R: {df['diff_hidro_r'].mean():,.0f} MW")

