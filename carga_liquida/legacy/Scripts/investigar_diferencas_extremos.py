"""
Investigação das Diferenças nos Extremos
=========================================

Analisa os casos onde há maior diferença entre:
- Carga Líquida Histórica (dados reais)
- Carga Líquida Simulada (mini_dessem)

Decompõe cada componente para identificar a fonte do erro.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Diretórios
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")

def carregar_bases_completas():
    """Carrega ambas as bases com todas as componentes."""
    
    print("\n" + "="*80)
    print("  CARREGANDO BASES PARA ANÁLISE DETALHADA")
    print("="*80)
    
    # Base histórica
    print("\n[1/2] Carga Líquida Histórica...")
    hist_path = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
    df_hist = pd.read_parquet(hist_path)
    df_hist = df_hist.rename(columns={
        'carga_liquida_historica': 'carga_liq_hist',
        'R': 'hidro_reserv_hist',
        'FD': 'hidro_fd_hist',
        'termica_flexivel': 'termica_flex_hist'
    })
    print(f"     Registros: {len(df_hist):,}")
    
    # Base simulada
    print("\n[2/2] Carga Líquida Simulada (mini_dessem)...")
    sim_path = MINI_DESSEM_DIR / "output" / "resultados" / "resultados_simulacao_20251103_193327.parquet"
    df_sim = pd.read_parquet(sim_path)
    
    # Criar timestamp
    df_sim['din_instante'] = pd.to_datetime(
        df_sim['ano'].astype(str) + '-' + 
        df_sim['mes'].astype(str).str.zfill(2) + '-' + 
        df_sim['dia'].astype(str).str.zfill(2) + ' ' + 
        df_sim['hora'].astype(str).str.zfill(2) + ':00:00'
    )
    
    # Selecionar colunas relevantes
    df_sim = df_sim[[
        'din_instante', 'simulacao', 'ano', 'mes', 'hora',
        'val_carga', 'carga_liquida',
        'val_gereolica', 'val_gereolica_depois_corte',
        'val_gersolar', 'val_gersolar_depois_corte',
        'val_inflexterm',
        'val_gerhidro_fd', 'val_gerhidro_reservatorio',
        'val_term_despacho',
        'curtailment', 'curtailment_eolica', 'curtailment_solar_cent'
    ]].copy()
    
    print(f"     Registros: {len(df_sim):,}")
    
    return df_hist, df_sim

def merge_e_analisar():
    """Merge e identifica extremos."""
    
    df_hist, df_sim = carregar_bases_completas()
    
    # Merge
    print("\n[3/4] Fazendo merge...")
    df_merged = pd.merge(
        df_hist,
        df_sim,
        on='din_instante',
        how='inner',
        suffixes=('_hist', '_sim')
    )
    
    print(f"     Registros overlap: {len(df_merged):,}")
    
    # Agrupar por timestamp (média dos cenários)
    print("\n[4/4] Agregando cenários...")
    
    # Usar colunas com sufixo correto
    df_agg = df_merged.groupby('din_instante').agg({
        'ano_sim': 'first',
        'mes_sim': 'first',
        'hora_sim': 'first',
        # Histórico (único valor)
        'carga_liq_hist': 'first',
        'hidro_reserv_hist': 'first',
        'hidro_fd_hist': 'first',
        'termica_flex_hist': 'first',
        # Simulado (média dos cenários)
        'val_carga': 'mean',
        'carga_liquida': 'mean',
        'val_gereolica': 'mean',
        'val_gereolica_depois_corte': 'mean',
        'val_gersolar': 'mean',
        'val_gersolar_depois_corte': 'mean',
        'val_inflexterm': 'mean',
        'val_gerhidro_fd': 'mean',
        'val_gerhidro_reservatorio': 'mean',
        'val_term_despacho': 'mean',
        'curtailment': 'mean',
        'curtailment_eolica': 'mean',
        'curtailment_solar_cent': 'mean'
    }).reset_index()
    
    # Renomear de volta (remover sufixos)
    df_agg = df_agg.rename(columns={
        'ano_sim': 'ano',
        'mes_sim': 'mes',
        'hora_sim': 'hora'
    })
    
    # Calcular diferenças de todas as componentes
    df_agg['diff_carga_liq'] = df_agg['carga_liquida'] - df_agg['carga_liq_hist']
    df_agg['diff_abs'] = df_agg['diff_carga_liq'].abs()
    df_agg['diff_hidro_fd'] = df_agg['val_gerhidro_fd'] - df_agg['hidro_fd_hist']
    df_agg['diff_hidro_r'] = df_agg['val_gerhidro_reservatorio'] - df_agg['hidro_reserv_hist']
    df_agg['diff_termica'] = df_agg['val_term_despacho'] - df_agg['termica_flex_hist']
    
    print(f"     Registros agregados: {len(df_agg):,}")
    print(f"     Diferença média: {df_agg['diff_carga_liq'].mean():,.0f} MW")
    print(f"     Diferença std: {df_agg['diff_carga_liq'].std():,.0f} MW")
    
    return df_agg

def analisar_extremos(df_agg, n_extremos=100):
    """Analisa os N casos com maiores diferenças."""
    
    print("\n" + "="*80)
    print(f"  ANÁLISE DOS {n_extremos} MAIORES EXTREMOS")
    print("="*80)
    
    # Identificar extremos
    df_extremos = df_agg.nlargest(n_extremos, 'diff_abs').copy()
    
    print(f"\nExtremos selecionados:")
    print(f"  Diferença mínima: {df_extremos['diff_abs'].min():,.0f} MW")
    print(f"  Diferença máxima: {df_extremos['diff_abs'].max():,.0f} MW")
    print(f"  Diferença média: {df_extremos['diff_abs'].mean():,.0f} MW")
    
    # Estatísticas dos componentes nos extremos
    print(f"\n" + "-"*80)
    print(f"  COMPONENTES NOS EXTREMOS (média):")
    print("-"*80)
    
    print(f"\nGERAÇÃO RENOVÁVEL:")
    print(f"  Eólica simulada:          {df_extremos['val_gereolica'].mean():>10,.0f} MW")
    print(f"  Eólica pós-curtailment:   {df_extremos['val_gereolica_depois_corte'].mean():>10,.0f} MW")
    print(f"  Curtailment eólica:       {df_extremos['curtailment_eolica'].mean():>10,.0f} MW")
    print(f"\n  Solar simulada:           {df_extremos['val_gersolar'].mean():>10,.0f} MW")
    print(f"  Solar pós-curtailment:    {df_extremos['val_gersolar_depois_corte'].mean():>10,.0f} MW")
    print(f"  Curtailment solar:        {df_extremos['curtailment_solar_cent'].mean():>10,.0f} MW")
    
    print(f"\nHIDRELETRICA:")
    print(f"  Hidro FD historica:       {df_extremos['hidro_fd_hist'].mean():>10,.0f} MW")
    print(f"  Hidro FD simulada:        {df_extremos['val_gerhidro_fd'].mean():>10,.0f} MW")
    print(f"  DIFERENCA FD:             {(df_extremos['val_gerhidro_fd'] - df_extremos['hidro_fd_hist']).mean():>10,.0f} MW <<")
    
    print(f"\n  Hidro R historica:        {df_extremos['hidro_reserv_hist'].mean():>10,.0f} MW")
    print(f"  Hidro R simulada:         {df_extremos['val_gerhidro_reservatorio'].mean():>10,.0f} MW")
    print(f"  DIFERENCA R:              {(df_extremos['val_gerhidro_reservatorio'] - df_extremos['hidro_reserv_hist']).mean():>10,.0f} MW <<")
    
    print(f"\nTERMICA:")
    print(f"  Inflexivel simulada:      {df_extremos['val_inflexterm'].mean():>10,.0f} MW")
    print(f"  Flexivel historica:       {df_extremos['termica_flex_hist'].mean():>10,.0f} MW")
    print(f"  Flexivel simulada:        {df_extremos['val_term_despacho'].mean():>10,.0f} MW")
    print(f"  DIFERENCA TERMICA FLEX:   {(df_extremos['val_term_despacho'] - df_extremos['termica_flex_hist']).mean():>10,.0f} MW <<")
    
    # Calcular contribuições para a diferença
    print(f"\n" + "-"*80)
    print(f"  DECOMPOSIÇÃO DA DIFERENÇA:")
    print("-"*80)
    
    df_extremos['contrib_hidro_fd'] = df_extremos['val_gerhidro_fd'] - df_extremos['hidro_fd_hist']
    df_extremos['contrib_hidro_r'] = df_extremos['val_gerhidro_reservatorio'] - df_extremos['hidro_reserv_hist']
    df_extremos['contrib_termica'] = df_extremos['val_term_despacho'] - df_extremos['termica_flex_hist']
    
    # Como carga líquida = hidro R + térmica flex, a diferença vem de:
    # diff_carga_liq_sim = (hidro_r_sim + termica_sim) - (hidro_r_hist + termica_hist)
    #                    = (hidro_r_sim - hidro_r_hist) + (termica_sim - termica_hist)
    
    print(f"\nContribuição para a diferença de Carga Líquida:")
    print(f"  Hidro Reservatório:  {df_extremos['contrib_hidro_r'].mean():>10,.0f} MW ({df_extremos['contrib_hidro_r'].mean() / df_extremos['diff_carga_liq'].mean() * 100:.1f}%)")
    print(f"  Térmica Flexível:    {df_extremos['contrib_termica'].mean():>10,.0f} MW ({df_extremos['contrib_termica'].mean() / df_extremos['diff_carga_liq'].mean() * 100:.1f}%)")
    print(f"  Total:               {(df_extremos['contrib_hidro_r'] + df_extremos['contrib_termica']).mean():>10,.0f} MW")
    
    return df_agg, df_extremos

def gerar_graficos_decomposicao(df_agg, df_extremos):
    """Gera gráficos detalhados de decomposição."""
    
    print("\n" + "="*80)
    print("  GERANDO GRÁFICOS DE DECOMPOSIÇÃO")
    print("="*80)
    
    output_dir = CARGA_LIQ_DIR / "Output" / "analise_extremos"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Scatter das componentes nos extremos
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('Componentes nos Extremos: Histórica vs Simulada', fontsize=16, fontweight='bold')
    
    # Hidro FD
    ax = axes[0, 0]
    ax.scatter(df_extremos['hidro_fd_hist'], df_extremos['val_gerhidro_fd'], 
              alpha=0.6, s=50, edgecolor='k', linewidth=0.5)
    lim = [0, max(df_extremos['hidro_fd_hist'].max(), df_extremos['val_gerhidro_fd'].max())]
    ax.plot(lim, lim, 'r--', linewidth=2, label='x=y')
    ax.set_xlabel('Hidro FD Histórica (MW)', fontsize=11)
    ax.set_ylabel('Hidro FD Simulada (MW)', fontsize=11)
    ax.set_title('Hidro Fio d\'Água', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Hidro R
    ax = axes[0, 1]
    ax.scatter(df_extremos['hidro_reserv_hist'], df_extremos['val_gerhidro_reservatorio'], 
              alpha=0.6, s=50, edgecolor='k', linewidth=0.5, color='steelblue')
    lim = [0, max(df_extremos['hidro_reserv_hist'].max(), df_extremos['val_gerhidro_reservatorio'].max())]
    ax.plot(lim, lim, 'r--', linewidth=2, label='x=y')
    ax.set_xlabel('Hidro Reserv Histórica (MW)', fontsize=11)
    ax.set_ylabel('Hidro Reserv Simulada (MW)', fontsize=11)
    ax.set_title('Hidro Reservatório', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Térmica Flexível
    ax = axes[0, 2]
    ax.scatter(df_extremos['termica_flex_hist'], df_extremos['val_term_despacho'], 
              alpha=0.6, s=50, edgecolor='k', linewidth=0.5, color='orange')
    lim = [0, max(df_extremos['termica_flex_hist'].max(), df_extremos['val_term_despacho'].max())]
    ax.plot(lim, lim, 'r--', linewidth=2, label='x=y')
    ax.set_xlabel('Térmica Flex Histórica (MW)', fontsize=11)
    ax.set_ylabel('Térmica Flex Simulada (MW)', fontsize=11)
    ax.set_title('Térmica Flexível', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Renováveis (apenas simulado tem)
    ax = axes[1, 0]
    ax.hist(df_extremos['val_gereolica_depois_corte'], bins=30, alpha=0.7, color='blue', edgecolor='black')
    ax.set_xlabel('Eólica pós-curtailment (MW)', fontsize=11)
    ax.set_ylabel('Frequência', fontsize=11)
    ax.set_title('Distribuição Eólica nos Extremos', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    ax = axes[1, 1]
    ax.hist(df_extremos['val_gersolar_depois_corte'], bins=30, alpha=0.7, color='orange', edgecolor='black')
    ax.set_xlabel('Solar pós-curtailment (MW)', fontsize=11)
    ax.set_ylabel('Frequência', fontsize=11)
    ax.set_title('Distribuição Solar nos Extremos', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    ax = axes[1, 2]
    ax.hist(df_extremos['curtailment'], bins=30, alpha=0.7, color='red', edgecolor='black')
    ax.set_xlabel('Curtailment (MW)', fontsize=11)
    ax.set_ylabel('Frequência', fontsize=11)
    ax.set_title('Distribuição Curtailment nos Extremos', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'decomposicao_componentes_extremos.png', dpi=150, bbox_inches='tight')
    print(f"\n[OK] decomposicao_componentes_extremos.png")
    plt.close()
    
    # 2. Contribuição para a diferença
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Contribuição de Cada Componente para a Diferença', fontsize=16, fontweight='bold')
    
    # Diferenças por componente
    df_extremos['diff_hidro_fd'] = df_extremos['val_gerhidro_fd'] - df_extremos['hidro_fd_hist']
    df_extremos['diff_hidro_r'] = df_extremos['val_gerhidro_reservatorio'] - df_extremos['hidro_reserv_hist']
    df_extremos['diff_termica'] = df_extremos['val_term_despacho'] - df_extremos['termica_flex_hist']
    
    # Boxplot das diferenças
    ax = axes[0, 0]
    data_box = [
        df_extremos['diff_hidro_fd'],
        df_extremos['diff_hidro_r'],
        df_extremos['diff_termica']
    ]
    bp = ax.boxplot(data_box, labels=['Hidro FD', 'Hidro R', 'Térmica Flex'], patch_artist=True)
    for patch, color in zip(bp['boxes'], ['skyblue', 'steelblue', 'orange']):
        patch.set_facecolor(color)
    ax.axhline(0, color='red', linestyle=':', linewidth=1)
    ax.set_ylabel('Diferença (Sim - Hist) [MW]', fontsize=11)
    ax.set_title('Boxplot das Diferenças por Componente', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Quando ocorrem os extremos (hora do dia)
    ax = axes[0, 1]
    hora_counts = df_extremos['hora'].value_counts().sort_index()
    ax.bar(hora_counts.index, hora_counts.values, color='purple', alpha=0.7, edgecolor='black')
    ax.set_xlabel('Hora do Dia', fontsize=11)
    ax.set_ylabel('Frequência de Extremos', fontsize=11)
    ax.set_title('Quando Ocorrem os Maiores Erros?', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24))
    
    # Quando ocorrem os extremos (mês)
    ax = axes[1, 0]
    mes_counts = df_extremos['mes'].value_counts().sort_index()
    ax.bar(mes_counts.index, mes_counts.values, color='green', alpha=0.7, edgecolor='black')
    ax.set_xlabel('Mês', fontsize=11)
    ax.set_ylabel('Frequência de Extremos', fontsize=11)
    ax.set_title('Meses com Maiores Erros', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(1, 13))
    
    # Correlação curtailment vs diferença
    ax = axes[1, 1]
    ax.scatter(df_extremos['curtailment'], df_extremos['diff_abs'], 
              alpha=0.6, s=50, edgecolor='k', linewidth=0.5, color='red')
    ax.set_xlabel('Curtailment (MW)', fontsize=11)
    ax.set_ylabel('|Diferença| (MW)', fontsize=11)
    ax.set_title('Curtailment vs Magnitude do Erro', fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'analise_extremos.png', dpi=150, bbox_inches='tight')
    print(f"[OK] analise_extremos.png")
    plt.close()
    
    # 3. Série temporal dos extremos
    fig, axes = plt.subplots(3, 1, figsize=(18, 12))
    fig.suptitle('Série Temporal: Top 500 Maiores Diferenças', fontsize=16, fontweight='bold')
    
    df_top500 = df_agg.nlargest(500, 'diff_abs').sort_values('din_instante').copy()
    
    # Calcular diferenças nos top500
    df_top500['diff_hidro_fd'] = df_top500['val_gerhidro_fd'] - df_top500['hidro_fd_hist']
    df_top500['diff_hidro_r'] = df_top500['val_gerhidro_reservatorio'] - df_top500['hidro_reserv_hist']
    df_top500['diff_termica'] = df_top500['val_term_despacho'] - df_top500['termica_flex_hist']
    
    # Carga Líquida
    ax = axes[0]
    ax.plot(df_top500['din_instante'], df_top500['carga_liq_hist'], 
           label='Histórica', linewidth=2, alpha=0.8, color='blue')
    ax.plot(df_top500['din_instante'], df_top500['carga_liquida'], 
           label='Simulada', linewidth=2, alpha=0.8, color='orange')
    ax.set_ylabel('Carga Líquida (MW)', fontsize=11)
    ax.set_title('Carga Líquida: Histórica vs Simulada', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Diferença
    ax = axes[1]
    ax.plot(df_top500['din_instante'], df_top500['diff_carga_liq'], 
           color='red', linewidth=2, alpha=0.8)
    ax.axhline(0, color='green', linestyle=':', linewidth=1.5)
    ax.set_ylabel('Diferença (MW)', fontsize=11)
    ax.set_title('Diferença (Simulada - Histórica)', fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Componentes de diferença
    ax = axes[2]
    ax.plot(df_top500['din_instante'], df_top500['diff_hidro_r'], 
           label='Δ Hidro R', linewidth=1.5, alpha=0.8)
    ax.plot(df_top500['din_instante'], df_top500['diff_termica'], 
           label='Δ Térmica', linewidth=1.5, alpha=0.8)
    ax.plot(df_top500['din_instante'], df_top500['diff_hidro_fd'], 
           label='Δ Hidro FD', linewidth=1.5, alpha=0.8)
    ax.axhline(0, color='black', linestyle=':', linewidth=1)
    ax.set_xlabel('Data', fontsize=11)
    ax.set_ylabel('Diferença (MW)', fontsize=11)
    ax.set_title('Decomposição da Diferença por Componente', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_extremos.png', dpi=150, bbox_inches='tight')
    print(f"[OK] temporal_extremos.png")
    plt.close()
    
    # Salvar CSV dos extremos
    csv_path = output_dir / 'extremos_detalhados.csv'
    df_extremos.to_csv(csv_path, index=False)
    print(f"\n[OK] CSV dos extremos salvo: extremos_detalhados.csv")
    
    print("\n" + "="*80)
    print("  [OK] ANÁLISE CONCLUÍDA!")
    print("="*80)
    print(f"\nResultados em: {output_dir}")
    
    return df_extremos

if __name__ == '__main__':
    df_agg = merge_e_analisar()
    df_agg, df_extremos = analisar_extremos(df_agg, n_extremos=100)
    df_extremos = gerar_graficos_decomposicao(df_agg, df_extremos)
    
    print(f"\n{'='*80}")
    print("  RESUMO EXECUTIVO")
    print("="*80)
    print(f"\nNos {len(df_extremos)} maiores extremos:")
    print(f"  - Diferença média: {df_extremos['diff_carga_liq'].mean():,.0f} MW")
    print(f"  - Principal causa: {'Hidro Reservatório' if df_extremos['diff_hidro_r'].abs().mean() > df_extremos['diff_termica'].abs().mean() else 'Térmica Flexível'}")
    print(f"  - Ocorrem principalmente em: Hora {df_extremos['hora'].mode()[0]}h, Mês {df_extremos['mes'].mode()[0]}")

