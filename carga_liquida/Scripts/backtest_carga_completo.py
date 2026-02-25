"""
Backtest Completo: Carga Real vs Simulada
==========================================

Analisa sistematicamente as diferenças de carga entre:
- Real (BALANCO_ENERGIA)
- Simulada (mini_dessem)

Por hora, mês, ano, dia da semana, etc.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")

def carregar_comparacao():
    """Carrega dados já processados - BASE COMPLETA."""
    
    print("="*80)
    print("  BACKTEST COMPLETO: Carga Real vs Simulada")
    print("="*80)
    
    # Usar base completa, não apenas extremos
    csv_path = CARGA_LIQ_DIR / "Output" / "comparacao" / "comparacao_detalhada.csv"
    
    if not csv_path.exists():
        print("\n[!] Execute primeiro: comparar_carga_liquida.py")
        return None
    
    print("\n[1/2] Carregando BASE COMPLETA...")
    df = pd.read_csv(csv_path)
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    
    # Extrair info temporal
    df['ano'] = df['din_instante'].dt.year
    df['mes'] = df['din_instante'].dt.month
    df['hora'] = df['din_instante'].dt.hour
    df['dia_semana'] = df['din_instante'].dt.dayofweek
    
    # Renomear colunas para padronizar
    rename_map = {}
    if 'carga_liquida_historica' in df.columns:
        rename_map['carga_liquida_historica'] = 'carga_liq_real'
    if 'carga_liquida' in df.columns:
        rename_map['carga_liquida'] = 'carga_liq_sim'
    if 'R' in df.columns:
        rename_map['R'] = 'hidro_r_real'
    if 'FD' in df.columns:
        rename_map['FD'] = 'hidro_fd_real'
    if 'termica_flexivel' in df.columns:
        rename_map['termica_flexivel'] = 'termica_flex_real'
    if 'val_gerhidro_reservatorio' in df.columns:
        rename_map['val_gerhidro_reservatorio'] = 'hidro_r_sim'
    if 'val_term_despacho' in df.columns:
        rename_map['val_term_despacho'] = 'termica_flex_sim'
    
    df = df.rename(columns=rename_map)
    
    # Calcular diferenças
    df['diff_carga_liq'] = df['carga_liq_sim'] - df['carga_liq_real']
    df['diff_carga_liq_pct'] = (df['diff_carga_liq'] / df['carga_liq_real']) * 100
    
    print(f"     Registros: {len(df):,}")
    print(f"     Periodo: {df['din_instante'].min()} ate {df['din_instante'].max()}")
    print(f"     Diferenca media: {df['diff_carga_liq'].mean():,.0f} MW ({df['diff_carga_liq_pct'].mean():.1f}%)")
    
    return df

def analisar_backtest(df):
    """Analisa diferenças por dimensão temporal."""
    
    print("\n[2/2] Analisando por dimensão...")
    
    print("\n" + "="*80)
    print("  ESTATÍSTICAS DE BACKTEST - CARGA")
    print("="*80)
    
    print(f"\nGERAL:")
    print(f"  Carga Liq Real Media:      {df['carga_liq_real'].mean():>10,.0f} MW")
    print(f"  Carga Liq Simulada Media:  {df['carga_liq_sim'].mean():>10,.0f} MW")
    print(f"  Diferenca Media:           {df['diff_carga_liq'].mean():>10,.0f} MW ({df['diff_carga_liq_pct'].mean():>6.1f}%)")
    print(f"  Desvio Padrao:             {df['diff_carga_liq'].std():>10,.0f} MW")
    print(f"  Min/Max:                   {df['diff_carga_liq'].min():>10,.0f} / {df['diff_carga_liq'].max():.0f} MW")
    
    # Por hora
    if 'hora' in df.columns:
        print(f"\nPOR HORA:")
        hora_stats = df.groupby('hora').agg({
            'carga_liq_real': 'mean',
            'carga_liq_sim': 'mean',
            'diff_carga_liq': ['mean', 'std', 'min', 'max'],
            'diff_carga_liq_pct': 'mean'
        })
        
        hora_stats.columns = ['_'.join(col).strip() for col in hora_stats.columns.values]
        
        print(f"  Hora com maior erro: {hora_stats['diff_carga_liq_mean'].idxmin()}h ({hora_stats['diff_carga_liq_mean'].min():,.0f} MW)")
        print(f"  Hora com menor erro: {hora_stats['diff_carga_liq_mean'].idxmax()}h ({hora_stats['diff_carga_liq_mean'].max():,.0f} MW)")
    
    # Por mês
    if 'mes' in df.columns:
        print(f"\nPOR MES:")
        mes_stats = df.groupby('mes').agg({
            'carga_liq_real': 'mean',
            'carga_liq_sim': 'mean',
            'diff_carga_liq': ['mean', 'std', 'count'],
            'diff_carga_liq_pct': 'mean'
        })
        
        mes_stats.columns = ['_'.join(col).strip() for col in mes_stats.columns.values]
        
        print(f"  Mes com maior erro: {mes_stats['diff_carga_liq_mean'].idxmin()} ({mes_stats['diff_carga_liq_mean'].min():,.0f} MW)")
        print(f"  Mes com menor erro: {mes_stats['diff_carga_liq_mean'].idxmax()} ({mes_stats['diff_carga_liq_mean'].max():,.0f} MW)")
    
    # Por ano
    if 'ano' in df.columns:
        print(f"\nPOR ANO:")
        ano_stats = df.groupby('ano').agg({
            'carga_liq_real': 'mean',
            'carga_liq_sim': 'mean',
            'diff_carga_liq': ['mean', 'std', 'count'],
            'diff_carga_liq_pct': 'mean'
        })
        
        ano_stats.columns = ['_'.join(col).strip() for col in ano_stats.columns.values]
        
        for ano in ano_stats.index:
            print(f"  {ano}: {ano_stats.loc[ano, 'diff_carga_liq_mean']:>10,.0f} MW ({ano_stats.loc[ano, 'diff_carga_liq_pct_mean']:>6.1f}%) - {int(ano_stats.loc[ano, 'diff_carga_liq_count'])} casos")
    
    return df

def gerar_graficos_backtest(df):
    """Gera gráficos completos de backtest."""
    
    print("\n" + "="*80)
    print("  GERANDO GRAFICOS DE BACKTEST")
    print("="*80)
    
    output_dir = CARGA_LIQ_DIR / "Output" / "backtest_carga"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Diferenças por hora e mês
    if 'hora' in df.columns and 'mes' in df.columns:
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle('Backtest: Diferenças de Carga por Dimensão Temporal', fontsize=16, fontweight='bold')
        
        # Por hora - média
        ax = axes[0, 0]
        hora_mean = df.groupby('hora')['diff_carga_liq'].mean()
        hora_std = df.groupby('hora')['diff_carga_liq'].std()
        
        ax.bar(hora_mean.index, hora_mean.values, color='steelblue', alpha=0.7, edgecolor='black')
        ax.errorbar(hora_mean.index, hora_mean.values, yerr=hora_std.values, 
                   fmt='none', ecolor='red', capsize=3, linewidth=1.5, alpha=0.7)
        ax.axhline(0, color='green', linestyle=':', linewidth=1.5)
        ax.set_xlabel('Hora', fontsize=11)
        ax.set_ylabel('Diferenca (Sim - Real) [MW]', fontsize=11)
        ax.set_title('Erro Medio por Hora (com +/-sigma)', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(range(0, 24))
        
        # Por hora - boxplot
        ax = axes[0, 1]
        data_hora = [df[df['hora']==h]['diff_carga_liq'].values for h in range(24)]
        bp = ax.boxplot(data_hora, positions=range(24), patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
        ax.axhline(0, color='green', linestyle=':', linewidth=1.5)
        ax.set_xlabel('Hora', fontsize=11)
        ax.set_ylabel('Diferenca (MW)', fontsize=11)
        ax.set_title('Distribuicao do Erro por Hora', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(range(0, 24, 3))
        
        # Por mês - média
        ax = axes[1, 0]
        mes_mean = df.groupby('mes')['diff_carga_liq'].mean()
        mes_std = df.groupby('mes')['diff_carga_liq'].std()
        
        ax.bar(mes_mean.index, mes_mean.values, color='orange', alpha=0.7, edgecolor='black')
        ax.errorbar(mes_mean.index, mes_mean.values, yerr=mes_std.values,
                   fmt='none', ecolor='red', capsize=5, linewidth=2, alpha=0.7)
        ax.axhline(0, color='green', linestyle=':', linewidth=1.5)
        ax.set_xlabel('Mes', fontsize=11)
        ax.set_ylabel('Diferenca (MW)', fontsize=11)
        ax.set_title('Erro Medio por Mes (com +/-sigma)', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(range(1, 13))
        
        # Por mês - percentual
        ax = axes[1, 1]
        mes_pct = df.groupby('mes')['diff_carga_liq_pct'].mean()
        
        ax.bar(mes_pct.index, mes_pct.values, color='purple', alpha=0.7, edgecolor='black')
        ax.axhline(0, color='green', linestyle=':', linewidth=1.5)
        ax.set_xlabel('Mes', fontsize=11)
        ax.set_ylabel('Diferenca (%)', fontsize=11)
        ax.set_title('Erro Percentual por Mes', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(range(1, 13))
        
        plt.tight_layout()
        plt.savefig(output_dir / 'backtest_temporal.png', dpi=150, bbox_inches='tight')
        print(f"\n[OK] backtest_temporal.png")
        plt.close()
    
    # 2. Heatmap hora x mês
    if 'hora' in df.columns and 'mes' in df.columns:
        fig, axes = plt.subplots(1, 2, figsize=(18, 7))
        fig.suptitle('Heatmap: Erro de Carga por Hora e Mes', fontsize=16, fontweight='bold')
        
        # Erro absoluto
        ax = axes[0]
        pivot_abs = df.pivot_table(values='diff_carga_liq', index='hora', columns='mes', aggfunc='mean')
        sns.heatmap(pivot_abs, annot=True, fmt='.0f', cmap='RdBu_r', center=0, ax=ax,
                   cbar_kws={'label': 'Diferenca (MW)'})
        ax.set_title('Erro Medio (MW)', fontweight='bold', fontsize=12)
        ax.set_xlabel('Mes', fontsize=11)
        ax.set_ylabel('Hora', fontsize=11)
        
        # Erro percentual
        ax = axes[1]
        pivot_pct = df.pivot_table(values='diff_carga_liq_pct', index='hora', columns='mes', aggfunc='mean')
        sns.heatmap(pivot_pct, annot=True, fmt='.1f', cmap='RdBu_r', center=0, ax=ax,
                   cbar_kws={'label': 'Diferenca (%)'})
        ax.set_title('Erro Percentual (%)', fontweight='bold', fontsize=12)
        ax.set_xlabel('Mes', fontsize=11)
        ax.set_ylabel('Hora', fontsize=11)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'heatmap_erro_hora_mes.png', dpi=150, bbox_inches='tight')
        print(f"[OK] heatmap_erro_hora_mes.png")
        plt.close()
    
    # 3. Scatter Real vs Simulado
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle('Scatter: Carga Liquida Real vs Simulada', fontsize=16, fontweight='bold')
    
    # Scatter geral
    ax = axes[0]
    ax.scatter(df['carga_liq_real'], df['carga_liq_sim'], alpha=0.5, s=30, edgecolor='k', linewidth=0.3)
    lim = [df[['carga_liq_real', 'carga_liq_sim']].min().min(), df[['carga_liq_real', 'carga_liq_sim']].max().max()]
    ax.plot(lim, lim, 'r--', linewidth=2, label='x=y (perfeito)')
    ax.set_xlabel('Carga Liquida Real (MW)', fontsize=12)
    ax.set_ylabel('Carga Liquida Simulada (MW)', fontsize=12)
    ax.set_title('Todos os Dados', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Scatter colorido por erro absoluto
    ax = axes[1]
    scatter = ax.scatter(df['carga_liq_real'], df['carga_liq_sim'], 
                        c=df['diff_carga_liq'].abs(), cmap='YlOrRd',
                        alpha=0.7, s=50, edgecolor='k', linewidth=0.3)
    ax.plot(lim, lim, 'b--', linewidth=2, label='x=y')
    ax.set_xlabel('Carga Liquida Real (MW)', fontsize=12)
    ax.set_ylabel('Carga Liquida Simulada (MW)', fontsize=12)
    ax.set_title('Colorido por |Erro|', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax, label='|Diferenca| (MW)')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'scatter_carga.png', dpi=150, bbox_inches='tight')
    print(f"[OK] scatter_carga.png")
    plt.close()
    
    # 4. Distribuição dos erros
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Distribuicao dos Erros de Carga', fontsize=16, fontweight='bold')
    
    # Histograma erro absoluto
    ax = axes[0, 0]
    ax.hist(df['diff_carga_liq'], bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(df['diff_carga_liq'].mean(), color='red', linestyle='--', linewidth=2,
              label=f'Media: {df["diff_carga_liq"].mean():.0f} MW')
    ax.axvline(0, color='green', linestyle=':', linewidth=2, label='Zero')
    ax.set_xlabel('Diferenca (MW)', fontsize=11)
    ax.set_ylabel('Frequencia', fontsize=11)
    ax.set_title('Distribuicao do Erro Absoluto', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Histograma erro percentual
    ax = axes[0, 1]
    ax.hist(df['diff_carga_liq_pct'], bins=50, color='orange', alpha=0.7, edgecolor='black')
    ax.axvline(df['diff_carga_liq_pct'].mean(), color='red', linestyle='--', linewidth=2,
              label=f'Media: {df["diff_carga_liq_pct"].mean():.1f}%')
    ax.axvline(0, color='green', linestyle=':', linewidth=2, label='Zero')
    ax.set_xlabel('Diferenca (%)', fontsize=11)
    ax.set_ylabel('Frequencia', fontsize=11)
    ax.set_title('Distribuicao do Erro Percentual', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # QQ-plot
    ax = axes[1, 0]
    from scipy import stats
    stats.probplot(df['diff_carga_liq'], dist="norm", plot=ax)
    ax.set_title('Q-Q Plot (normalidade dos erros)', fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Resíduos vs Carga Líquida Real
    ax = axes[1, 1]
    ax.scatter(df['carga_liq_real'], df['diff_carga_liq'], alpha=0.5, s=20)
    ax.axhline(0, color='green', linestyle=':', linewidth=1.5)
    # Tendência
    z = np.polyfit(df['carga_liq_real'], df['diff_carga_liq'], 1)
    p = np.poly1d(z)
    ax.plot(df['carga_liq_real'].sort_values(), p(df['carga_liq_real'].sort_values()), 
           'r--', linewidth=2, label=f'Tendencia: {z[0]:.3f}x + {z[1]:.0f}')
    ax.set_xlabel('Carga Liquida Real (MW)', fontsize=11)
    ax.set_ylabel('Erro (MW)', fontsize=11)
    ax.set_title('Erro vs Magnitude da Carga', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'distribuicao_erros.png', dpi=150, bbox_inches='tight')
    print(f"[OK] distribuicao_erros.png")
    plt.close()
    
    print("\n" + "="*80)
    print("  [OK] BACKTEST CONCLUIDO!")
    print("="*80)
    print(f"\nResultados em: {output_dir}")
    
    return df

if __name__ == '__main__':
    df = carregar_comparacao()
    if df is not None:
        df = analisar_backtest(df)
        df = gerar_graficos_backtest(df)

