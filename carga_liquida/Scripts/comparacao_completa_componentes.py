"""
Comparação Completa: Componente por Componente
===============================================

Compara TODAS as componentes entre:
1. Dados Reais (BALANCO_ENERGIA + Geração por Usina)
2. Modelo Simulado (Mini DESSEM)

Para identificar exatamente onde está o erro nos extremos.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Diretórios
MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")

def carregar_balanco_energia():
    """Carrega dados do BALANCO_ENERGIA (carga, renováveis)."""
    
    print("\n[1/3] Carregando BALANCO_ENERGIA (SIN)...")
    
    raw_dir = MINI_DESSEM_DIR / "Data" / "raw_data"
    arquivos = sorted(raw_dir.glob("BALANCO_ENERGIA_SUBSISTEMA_*.xlsx"))
    
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo BALANCO encontrado em {raw_dir}")
    
    dfs = []
    for arquivo in arquivos:
        try:
            df = pd.read_excel(arquivo, sheet_name=0)
            
            # Identificar coluna de subsistema
            id_col = None
            for cand in ["id_subsistema", "id_subsistena", "nom_subsistema"]:
                if cand in df.columns:
                    id_col = cand
                    break
            
            if id_col is not None:
                df[id_col] = df[id_col].astype(str).str.upper().str.strip()
                df = df[df[id_col] == "SIN"].copy()
            
            # Filtrar colunas essenciais
            colunas_essenciais = ['din_instante', 'val_carga', 'val_gereolica', 'val_gersolar', 
                                 'val_gerhidraulica', 'val_gertermica']
            colunas_presentes = [c for c in colunas_essenciais if c in df.columns]
            
            if 'din_instante' in colunas_presentes:
                df = df[colunas_presentes].copy()
                df['din_instante'] = pd.to_datetime(df['din_instante'], errors='coerce')
                df = df.dropna(subset=['din_instante'])
                
                # Converter para numérico
                for col in colunas_presentes:
                    if col != 'din_instante':
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                dfs.append(df)
        except Exception as e:
            print(f"     [!] Erro em {arquivo.name}: {e}")
            continue
    
    if not dfs:
        raise ValueError("Nenhum dado válido encontrado nos arquivos BALANCO")
    
    df_balanco = pd.concat(dfs, ignore_index=True)
    df_balanco = df_balanco.sort_values('din_instante').drop_duplicates(subset=['din_instante'])
    
    print(f"     [OK] {len(arquivos)} arquivos processados")
    print(f"     Período: {df_balanco['din_instante'].min()} até {df_balanco['din_instante'].max()}")
    print(f"     Registros: {len(df_balanco):,}")
    
    return df_balanco

def carregar_hidro_detalhada():
    """Carrega dados de hidro por usina (FD vs R)."""
    
    print("\n[2/3] Carregando Hidro detalhada (FD vs R)...")
    
    # Já processado anteriormente
    path = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
    df = pd.read_parquet(path)
    
    print(f"     [OK] Carregado ({len(df):,} registros)")
    
    return df[['din_instante', 'FD', 'R', 'termica_flexivel']].copy()

def carregar_simulado():
    """Carrega dados simulados do mini_dessem."""
    
    print("\n[3/3] Carregando Simulação (Mini DESSEM)...")
    
    # Buscar arquivo mais recente automaticamente
    resultados_dir = MINI_DESSEM_DIR / "output" / "resultados"
    arquivos = sorted(resultados_dir.glob("resultados_simulacao_*.parquet"))
    
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo de resultado em {resultados_dir}")
    
    path = arquivos[-1]  # Mais recente
    print(f"     Arquivo: {path.name}")
    
    df = pd.read_parquet(path)
    
    # Criar timestamp
    df['din_instante'] = pd.to_datetime(
        df['ano'].astype(str) + '-' + 
        df['mes'].astype(str).str.zfill(2) + '-' + 
        df['dia'].astype(str).str.zfill(2) + ' ' + 
        df['hora'].astype(str).str.zfill(2) + ':00:00'
    )
    
    print(f"     [OK] Carregado ({len(df):,} registros)")
    
    return df

def merge_completo():
    """Faz merge de todas as bases."""
    
    print("\n" + "="*80)
    print("  MERGE COMPLETO DAS BASES")
    print("="*80)
    
    df_balanco = carregar_balanco_energia()
    df_hidro = carregar_hidro_detalhada()
    df_sim = carregar_simulado()
    
    # Merge BALANCO + Hidro detalhada
    print("\n[1/2] Merge BALANCO + Hidro...")
    df_real = pd.merge(df_balanco, df_hidro, on='din_instante', how='inner')
    print(f"     Registros: {len(df_real):,}")
    
    # Merge com simulado
    print("\n[2/2] Merge com Simulação...")
    df_completo = pd.merge(
        df_real,
        df_sim,
        on='din_instante',
        how='inner',
        suffixes=('_real', '_sim')
    )
    print(f"     Registros overlap: {len(df_completo):,}")
    
    # Agrupar simulações (média)
    print("\n[3/3] Agregando cenários...")
    
    # Colunas do histórico (BALANCO - com sufixo _real)
    cols_balanco_real = ['val_carga_real', 'val_gereolica_real', 'val_gersolar_real']
    # Colunas do histórico (Hidro detalhada - sem sufixo, não conflitam)
    cols_hidro_hist = ['FD', 'R', 'termica_flexivel', 'carga_liquida_historica']
    # Colunas temporais com sufixo
    cols_temporais = ['ano_sim', 'mes_sim', 'hora_sim', 'dia_sim']
    # Colunas do simulado sem sufixo (não conflitam com hidro detalhada)
    cols_sim_sem_sufixo = ['val_gerhidro_fd', 'val_gerhidro_reservatorio',
                          'val_term_despacho', 'curtailment', 'curtailment_eolica',
                          'curtailment_solar_cent', 'carga_liquida',
                          'val_inflexterm', 'val_gereolica_depois_corte', 'val_gersolar_depois_corte']
    # Colunas do simulado com sufixo (conflitam com BALANCO)
    cols_sim_com_sufixo = ['val_carga_sim', 'val_gereolica_sim', 'val_gersolar_sim']
    
    # Criar dicionário de agregação
    agg_dict = {}
    
    # BALANCO (primeiro valor, todos iguais)
    for col in cols_balanco_real:
        if col in df_completo.columns:
            agg_dict[col] = 'first'
    
    # Hidro detalhada (primeiro valor)
    for col in cols_hidro_hist:
        if col in df_completo.columns:
            agg_dict[col] = 'first'
    
    # Temporais
    for col in cols_temporais:
        if col in df_completo.columns:
            agg_dict[col] = 'first'
    
    # Simulado sem sufixo (média dos cenários)
    for col in cols_sim_sem_sufixo:
        if col in df_completo.columns:
            agg_dict[col] = 'mean'
    
    # Simulado com sufixo (média dos cenários)
    for col in cols_sim_com_sufixo:
        if col in df_completo.columns:
            agg_dict[col] = 'mean'
    
    df_agg = df_completo.groupby('din_instante').agg(agg_dict).reset_index()
    
    # Renomear
    df_agg = df_agg.rename(columns={
        # Histórico BALANCO (com sufixo _real)
        'val_carga_real': 'carga_real',
        'val_gereolica_real': 'eolica_real',
        'val_gersolar_real': 'solar_real',
        # Histórico Hidro (sem sufixo)
        'FD': 'hidro_fd_real',
        'R': 'hidro_r_real',
        'termica_flexivel': 'termica_flex_real',
        'carga_liquida_historica': 'carga_liq_hist',
        # Simulado temporais
        'ano_sim': 'ano',
        'mes_sim': 'mes',
        'hora_sim': 'hora',
        'dia_sim': 'dia',
        # Simulado BALANCO (com sufixo _sim)
        'val_carga_sim': 'carga_sim',
        'val_gereolica_sim': 'eolica_pre_sim',
        'val_gersolar_sim': 'solar_pre_sim',
        # Simulado outros (sem sufixo, não conflitam)
        'val_gereolica_depois_corte': 'eolica_pos_sim',
        'val_gersolar_depois_corte': 'solar_pos_sim',
        'val_inflexterm': 'inflex_sim',
        'val_gerhidro_fd': 'hidro_fd_sim',
        'val_gerhidro_reservatorio': 'hidro_r_sim',
        'val_term_despacho': 'termica_flex_sim',
        'curtailment': 'curtailment_sim',
        'curtailment_eolica': 'curtailment_eolica_sim',
        'curtailment_solar_cent': 'curtailment_solar_cent_sim',
        'carga_liquida': 'carga_liq_sim',
    })
    
    # Calcular carga líquida REAL
    df_agg['carga_liq_real'] = df_agg['hidro_r_real'] + df_agg['termica_flex_real']
    
    print(f"     [OK] {len(df_agg):,} registros agregados")
    
    return df_agg

def analisar_componentes(df_agg, n_extremos=100):
    """Analisa componente por componente."""
    
    print("\n" + "="*80)
    print(f"  ANÁLISE COMPONENTE POR COMPONENTE")
    print("="*80)
    
    # Calcular diferença total
    df_agg['diff_carga_liq'] = df_agg['carga_liq_sim'] - df_agg['carga_liq_real']
    df_agg['diff_abs'] = df_agg['diff_carga_liq'].abs()
    
    # Pegar extremos
    df_extremos = df_agg.nlargest(n_extremos, 'diff_abs').copy()
    
    print(f"\n{'='*80}")
    print(f"  TOP {n_extremos} EXTREMOS - DECOMPOSIÇÃO")
    print("="*80)
    
    # Comparar cada componente
    print(f"\n{'COMPONENTE':<25} {'REAL':<15} {'SIMULADO':<15} {'DIFERENÇA':<15} {'% DIFF':<10}")
    print("-"*80)
    
    componentes = [
        ('Carga Total', 'carga_real', 'carga_sim'),
        ('Eólica', 'eolica_real', 'eolica_pos_sim'),
        ('Solar', 'solar_real', 'solar_pos_sim'),
        ('Hidro FD', 'hidro_fd_real', 'hidro_fd_sim'),
        ('Hidro R', 'hidro_r_real', 'hidro_r_sim'),
        ('Térmica Flex', 'termica_flex_real', 'termica_flex_sim'),
    ]
    
    for nome, col_real, col_sim in componentes:
        media_real = df_extremos[col_real].mean()
        media_sim = df_extremos[col_sim].mean()
        diff = media_sim - media_real
        pct = (diff / media_real * 100) if media_real != 0 else 0
        
        print(f"{nome:<25} {media_real:>12,.0f} MW  {media_sim:>12,.0f} MW  {diff:>12,.0f} MW  {pct:>8.1f}%")
    
    print("-"*80)
    
    # Calcular impacto na carga líquida
    print(f"\n{'IMPACTO NA CARGA LÍQUIDA':<25} {'CONTRIBUIÇÃO':<15} {'% do Erro Total':<20}")
    print("-"*80)
    
    # Diferenças que aumentam carga líquida (positivo = aumenta necessidade)
    df_extremos['contrib_carga'] = df_extremos['carga_sim'] - df_extremos['carga_real']
    df_extremos['contrib_eolica'] = -(df_extremos['eolica_pos_sim'] - df_extremos['eolica_real'])
    df_extremos['contrib_solar'] = -(df_extremos['solar_pos_sim'] - df_extremos['solar_real'])
    df_extremos['contrib_hidro_fd'] = -(df_extremos['hidro_fd_sim'] - df_extremos['hidro_fd_real'])
    
    erro_total = df_extremos['diff_carga_liq'].mean()
    
    contribuicoes = [
        ('Carga', 'contrib_carga'),
        ('Eólica (menos = aumenta CL)', 'contrib_eolica'),
        ('Solar (menos = aumenta CL)', 'contrib_solar'),
        ('Hidro FD (menos = aumenta CL)', 'contrib_hidro_fd'),
    ]
    
    for nome, col in contribuicoes:
        valor = df_extremos[col].mean()
        pct = (valor / erro_total * 100) if erro_total != 0 else 0
        print(f"{nome:<25} {valor:>12,.0f} MW      {pct:>8.1f}%")
    
    print("-"*80)
    print(f"{'TOTAL CALCULADO':<25} {df_extremos[['contrib_carga', 'contrib_eolica', 'contrib_solar', 'contrib_hidro_fd']].sum(axis=1).mean():>12,.0f} MW")
    print(f"{'DIFERENÇA OBSERVADA':<25} {erro_total:>12,.0f} MW")
    
    return df_extremos

def gerar_graficos_decomposicao(df_extremos):
    """Gera gráficos de decomposição."""
    
    print("\n" + "="*80)
    print("  GERANDO GRÁFICOS DE DECOMPOSIÇÃO COMPLETA")
    print("="*80)
    
    output_dir = CARGA_LIQ_DIR / "Output" / "analise_completa"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Comparação componente por componente (6 scatters)
    fig, axes = plt.subplots(3, 2, figsize=(18, 16))
    fig.suptitle('Comparação Componente por Componente: Real vs Simulado', fontsize=16, fontweight='bold')
    
    componentes = [
        ('Carga', 'carga_real', 'carga_sim', 'green'),
        ('Eólica', 'eolica_real', 'eolica_pos_sim', 'blue'),
        ('Solar', 'solar_real', 'solar_pos_sim', 'orange'),
        ('Hidro FD', 'hidro_fd_real', 'hidro_fd_sim', 'skyblue'),
        ('Hidro R', 'hidro_r_real', 'hidro_r_sim', 'steelblue'),
        ('Térmica Flex', 'termica_flex_real', 'termica_flex_sim', 'red'),
    ]
    
    for idx, (nome, col_real, col_sim, cor) in enumerate(componentes):
        ax = axes[idx // 2, idx % 2]
        
        ax.scatter(df_extremos[col_real], df_extremos[col_sim], 
                  alpha=0.6, s=50, color=cor, edgecolor='k', linewidth=0.5)
        
        # Linha x=y
        lim_min = min(df_extremos[col_real].min(), df_extremos[col_sim].min())
        lim_max = max(df_extremos[col_real].max(), df_extremos[col_sim].max())
        ax.plot([lim_min, lim_max], [lim_min, lim_max], 'r--', linewidth=2, label='x=y', alpha=0.7)
        
        # Estatísticas
        diff_mean = (df_extremos[col_sim] - df_extremos[col_real]).mean()
        diff_pct = (diff_mean / df_extremos[col_real].mean() * 100) if df_extremos[col_real].mean() != 0 else 0
        
        ax.set_xlabel(f'{nome} Real (MW)', fontsize=11)
        ax.set_ylabel(f'{nome} Simulado (MW)', fontsize=11)
        ax.set_title(f'{nome}\nDiff: {diff_mean:,.0f} MW ({diff_pct:.1f}%)', fontweight='bold', fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'comparacao_todos_componentes.png', dpi=150, bbox_inches='tight')
    print(f"\n[OK] comparacao_todos_componentes.png")
    plt.close()
    
    # 2. Waterfall da decomposição
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    # Valores médios nos extremos
    carga_liq_real = df_extremos['carga_liq_real'].mean()
    carga_liq_sim = df_extremos['carga_liq_sim'].mean()
    
    contrib_carga = df_extremos['contrib_carga'].mean()
    contrib_eolica = df_extremos['contrib_eolica'].mean()
    contrib_solar = df_extremos['contrib_solar'].mean()
    contrib_hidro_fd = df_extremos['contrib_hidro_fd'].mean()
    
    # Criar waterfall
    categorias = ['Carga Liq\nReal', 'Δ Carga', 'Δ Eólica', 'Δ Solar', 'Δ Hidro FD', 'Carga Liq\nSimulada']
    valores = [carga_liq_real, contrib_carga, contrib_eolica, contrib_solar, contrib_hidro_fd, 0]
    
    # Calcular posições
    y_pos = [0] * len(valores)
    y_pos[0] = carga_liq_real
    for i in range(1, len(valores)-1):
        y_pos[i] = y_pos[i-1] + valores[i]
    y_pos[-1] = carga_liq_sim
    
    cores = ['blue', 'green' if contrib_carga > 0 else 'red',
             'green' if contrib_eolica > 0 else 'red',
             'green' if contrib_solar > 0 else 'red',
             'green' if contrib_hidro_fd > 0 else 'red',
             'orange']
    
    # Barras
    for i, (cat, val, y, cor) in enumerate(zip(categorias, valores, y_pos, cores)):
        if i == 0:  # Base
            ax.bar(i, val, color=cor, alpha=0.7, edgecolor='black', linewidth=2)
        elif i == len(categorias) - 1:  # Final
            ax.bar(i, val if val != 0 else y, bottom=0, color=cor, alpha=0.7, edgecolor='black', linewidth=2)
        else:  # Incrementos
            if val > 0:
                ax.bar(i, val, bottom=y - val, color=cor, alpha=0.7, edgecolor='black')
            else:
                ax.bar(i, -val, bottom=y, color=cor, alpha=0.7, edgecolor='black')
            
            # Linha conectando
            if i > 0:
                ax.plot([i-0.4, i-0.4], [y_pos[i-1], y], 'k--', linewidth=1, alpha=0.5)
    
    ax.set_xticks(range(len(categorias)))
    ax.set_xticklabels(categorias, fontsize=11)
    ax.set_ylabel('MW', fontsize=12)
    ax.set_title(f'Decomposição da Diferença - Top {len(df_extremos)} Extremos\n(valores médios)', 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(0, color='black', linewidth=0.8)
    
    # Anotações
    for i, y in enumerate(y_pos):
        if valores[i] != 0 or i == 0 or i == len(valores) - 1:
            ax.text(i, y, f'{y:,.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'waterfall_decomposicao.png', dpi=150, bbox_inches='tight')
    print(f"[OK] waterfall_decomposicao.png")
    plt.close()
    
    # Salvar CSV
    csv_path = output_dir / 'extremos_completos.csv'
    df_extremos.to_csv(csv_path, index=False)
    print(f"\n[OK] CSV completo salvo: extremos_completos.csv")
    
    print("\n" + "="*80)
    print("  [OK] ANÁLISE COMPLETA CONCLUÍDA!")
    print("="*80)
    print(f"\nResultados em: {output_dir}")
    
    return df_extremos

if __name__ == '__main__':
    df_agg = merge_completo()
    
    # Salvar arquivo completo para análises por dia
    output_dir = CARGA_LIQ_DIR / "Output" / "analise_completa"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_completo = output_dir / 'comparacao_completa.csv'
    df_agg.to_csv(csv_completo, index=False)
    print(f"\n[OK] Arquivo completo salvo: comparacao_completa.csv ({len(df_agg):,} registros)")
    
    df_extremos = analisar_componentes(df_agg, n_extremos=100)
    df_extremos = gerar_graficos_decomposicao(df_extremos)

