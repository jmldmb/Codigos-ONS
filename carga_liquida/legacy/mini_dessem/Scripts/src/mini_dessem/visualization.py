"""
Funções para visualização dos resultados da simulação
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from .config import OUTPUT_DIR


def plot_distribuicao_renovavel(df_resultados, save_fig=False, output_dir=None):
    """
    Plota distribuições de geração renovável após corte.
    
    Parâmetros:
    - df_resultados (pd.DataFrame): DataFrame com resultados da simulação
    - save_fig (bool): Se True, salva a figura
    - output_dir (str/Path): Diretório para salvar figura
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Distribuição da geração eólica após corte
    axes[0].hist(df_resultados['val_gereolica_depois_corte'], bins=50, 
                 color='blue', alpha=0.7, edgecolor='black')
    axes[0].set_title('Distribuição da Geração Eólica Após Corte', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Geração Eólica (MW)', fontsize=12)
    axes[0].set_ylabel('Frequência', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    # Distribuição da geração solar após corte
    axes[1].hist(df_resultados['val_gersolar_depois_corte'], bins=50, 
                 color='orange', alpha=0.7, edgecolor='black')
    axes[1].set_title('Distribuição da Geração Solar Após Corte', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Geração Solar (MW)', fontsize=12)
    axes[1].set_ylabel('Frequência', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_fig:
        if output_dir is None:
            output_dir = OUTPUT_DIR
        output_path = Path(output_dir) / 'distribuicao_renovavel.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Figura salva em: {output_path}")
    
    plt.show()


def plot_boxplot_despacho_hora(df_resultados, save_fig=False, output_dir=None):
    """
    Plota boxplot das variáveis de despacho por hora.
    
    Parâmetros:
    - df_resultados (pd.DataFrame): DataFrame com resultados da simulação
    - save_fig (bool): Se True, salva a figura
    - output_dir (str/Path): Diretório para salvar figura
    """
    plt.figure(figsize=(18, 10))
    
    variables = [
        'val_term_despacho', 
        'val_gerhidro_reservatorio', 
        'val_gerhidro_fd',
        'val_gereolica_depois_corte', 
        'val_gersolar_depois_corte'
    ]
    
    # Renomear variáveis para melhor visualização
    rename_dict = {
        'val_term_despacho': 'Térmico',
        'val_gerhidro_reservatorio': 'Hidro Reservatório',
        'val_gerhidro_fd': 'Hidro Fio d\'Água',
        'val_gereolica_depois_corte': 'Eólica',
        'val_gersolar_depois_corte': 'Solar'
    }
    
    df_boxplot = df_resultados[variables + ['hora']].copy()
    df_boxplot = df_boxplot.rename(columns=rename_dict)
    
    df_boxplot_melted = df_boxplot.melt(
        id_vars=['hora'], 
        value_vars=list(rename_dict.values()),
        var_name='Fonte', 
        value_name='Geração (MW)'
    )
    
    sns.boxplot(
        x='hora', 
        y='Geração (MW)', 
        hue='Fonte', 
        data=df_boxplot_melted,
        palette='Set2'
    )
    
    plt.title('Distribuição das Fontes de Geração por Hora do Dia', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Hora do Dia', fontsize=14)
    plt.ylabel('Geração (MW)', fontsize=14)
    plt.legend(title='Fonte', fontsize=11, title_fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    if save_fig:
        if output_dir is None:
            output_dir = OUTPUT_DIR
        output_path = Path(output_dir) / 'boxplot_despacho_hora.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Figura salva em: {output_path}")
    
    plt.show()


def plot_perfil_geracao_cenario(df_resultados, simulacao=None, save_fig=False, output_dir=None):
    """
    Plota perfil de geração para um cenário específico.
    
    Parâmetros:
    - df_resultados (pd.DataFrame): DataFrame com resultados da simulação
    - simulacao (int): Número da simulação. Se None, escolhe aleatoriamente.
    - save_fig (bool): Se True, salva a figura
    - output_dir (str/Path): Diretório para salvar figura
    """
    if simulacao is None:
        simulacao = np.random.choice(df_resultados['simulacao'].unique())
    
    df_sim = df_resultados[df_resultados['simulacao'] == simulacao].sort_values('hora')
    
    if len(df_sim) == 0:
        print(f"Simulação {simulacao} não encontrada no DataFrame.")
        return
    
    plt.figure(figsize=(14, 8))
    
    # Plotar cada fonte
    plt.plot(df_sim['hora'], df_sim['val_gerhidro_total'], 
             label='Hidro Total', linewidth=2.5, marker='o', markersize=4)
    plt.plot(df_sim['hora'], df_sim['val_gereolica_depois_corte'], 
             label='Eólica', linewidth=2.5, marker='s', markersize=4)
    plt.plot(df_sim['hora'], df_sim['val_gersolar_depois_corte'], 
             label='Solar', linewidth=2.5, marker='^', markersize=4)
    plt.plot(df_sim['hora'], df_sim['val_term_despacho'], 
             label='Térmico', linewidth=2.5, marker='d', markersize=4)
    plt.plot(df_sim['hora'], df_sim['val_carga'], 
             label='Carga', linewidth=2.5, linestyle='--', color='black', marker='x', markersize=4)
    
    # Informações adicionais
    mes = df_sim['mes'].iloc[0]
    ano = df_sim['ano'].iloc[0]
    
    plt.title(f'Perfil de Geração - Simulação {simulacao} ({ano}-{mes:02d})', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Hora do Dia', fontsize=14)
    plt.ylabel('Geração (MW)', fontsize=14)
    plt.legend(fontsize=12, loc='best')
    plt.grid(True, alpha=0.3)
    plt.xticks(range(0, 24))
    plt.tight_layout()
    
    if save_fig:
        if output_dir is None:
            output_dir = OUTPUT_DIR
        output_path = Path(output_dir) / f'perfil_geracao_sim_{simulacao}.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Figura salva em: {output_path}")
    
    plt.show()


def plot_curtailment_analise(df_resultados, save_fig=False, output_dir=None):
    """
    Plota análise de curtailment.
    
    Parâmetros:
    - df_resultados (pd.DataFrame): DataFrame com resultados da simulação
    - save_fig (bool): Se True, salva a figura
    - output_dir (str/Path): Diretório para salvar figura
    """
    # Filtrar apenas registros com curtailment
    df_curtailment = df_resultados[df_resultados['curtailment'] > 0]
    
    if len(df_curtailment) == 0:
        print("Nenhum curtailment detectado nos resultados.")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Distribuição de curtailment
    axes[0, 0].hist(df_curtailment['curtailment'], bins=50, 
                    color='red', alpha=0.7, edgecolor='black')
    axes[0, 0].set_title('Distribuição de Curtailment', fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('Curtailment (MW)', fontsize=12)
    axes[0, 0].set_ylabel('Frequência', fontsize=12)
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Curtailment por hora
    curtailment_por_hora = df_curtailment.groupby('hora')['curtailment'].mean()
    axes[0, 1].bar(curtailment_por_hora.index, curtailment_por_hora.values, 
                   color='orangered', alpha=0.7, edgecolor='black')
    axes[0, 1].set_title('Curtailment Médio por Hora', fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('Hora do Dia', fontsize=12)
    axes[0, 1].set_ylabel('Curtailment Médio (MW)', fontsize=12)
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    axes[0, 1].set_xticks(range(0, 24))
    
    # 3. Curtailment por mês
    curtailment_por_mes = df_curtailment.groupby('mes')['curtailment'].mean()
    axes[1, 0].bar(curtailment_por_mes.index, curtailment_por_mes.values, 
                   color='coral', alpha=0.7, edgecolor='black')
    axes[1, 0].set_title('Curtailment Médio por Mês', fontsize=14, fontweight='bold')
    axes[1, 0].set_xlabel('Mês', fontsize=12)
    axes[1, 0].set_ylabel('Curtailment Médio (MW)', fontsize=12)
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    axes[1, 0].set_xticks(range(1, 13))
    
    # 4. Percentual de horas com curtailment
    total_registros = len(df_resultados)
    registros_com_curtailment = len(df_curtailment)
    percentual_curtailment = (registros_com_curtailment / total_registros) * 100
    
    axes[1, 1].text(0.5, 0.6, f'{percentual_curtailment:.2f}%', 
                    ha='center', va='center', fontsize=60, fontweight='bold', color='red')
    axes[1, 1].text(0.5, 0.3, 'de horas com curtailment', 
                    ha='center', va='center', fontsize=16)
    axes[1, 1].set_xlim(0, 1)
    axes[1, 1].set_ylim(0, 1)
    axes[1, 1].axis('off')
    axes[1, 1].set_title('Frequência de Curtailment', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_fig:
        if output_dir is None:
            output_dir = OUTPUT_DIR
        output_path = Path(output_dir) / 'analise_curtailment.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Figura salva em: {output_path}")
    
    plt.show()


def plot_pld_analise(df_resultados, save_fig=False, output_dir=None):
    """
    Plota análise de PLD.
    
    Parâmetros:
    - df_resultados (pd.DataFrame): DataFrame com resultados da simulação
    - save_fig (bool): Se True, salva a figura
    - output_dir (str/Path): Diretório para salvar figura
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Distribuição de PLD
    axes[0, 0].hist(df_resultados['pld'], bins=50, 
                    color='green', alpha=0.7, edgecolor='black')
    axes[0, 0].set_title('Distribuição de PLD', fontsize=14, fontweight='bold')
    axes[0, 0].set_xlabel('PLD (R$/MWh)', fontsize=12)
    axes[0, 0].set_ylabel('Frequência', fontsize=12)
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. PLD médio por hora
    pld_por_hora = df_resultados.groupby('hora')['pld'].mean()
    axes[0, 1].plot(pld_por_hora.index, pld_por_hora.values, 
                    marker='o', linewidth=2, markersize=6, color='darkgreen')
    axes[0, 1].set_title('PLD Médio por Hora', fontsize=14, fontweight='bold')
    axes[0, 1].set_xlabel('Hora do Dia', fontsize=12)
    axes[0, 1].set_ylabel('PLD Médio (R$/MWh)', fontsize=12)
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].set_xticks(range(0, 24))
    
    # 3. PLD médio por mês
    pld_por_mes = df_resultados.groupby('mes')['pld'].mean()
    axes[1, 0].bar(pld_por_mes.index, pld_por_mes.values, 
                   color='seagreen', alpha=0.7, edgecolor='black')
    axes[1, 0].set_title('PLD Médio por Mês', fontsize=14, fontweight='bold')
    axes[1, 0].set_xlabel('Mês', fontsize=12)
    axes[1, 0].set_ylabel('PLD Médio (R$/MWh)', fontsize=12)
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    axes[1, 0].set_xticks(range(1, 13))
    
    # 4. Estatísticas de PLD
    stats_text = f"""
    Média: {df_resultados['pld'].mean():.2f} R$/MWh
    Mediana: {df_resultados['pld'].median():.2f} R$/MWh
    Mínimo: {df_resultados['pld'].min():.2f} R$/MWh
    Máximo: {df_resultados['pld'].max():.2f} R$/MWh
    Desvio Padrão: {df_resultados['pld'].std():.2f} R$/MWh
    """
    axes[1, 1].text(0.5, 0.5, stats_text, 
                    ha='center', va='center', fontsize=14, 
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    axes[1, 1].set_xlim(0, 1)
    axes[1, 1].set_ylim(0, 1)
    axes[1, 1].axis('off')
    axes[1, 1].set_title('Estatísticas de PLD', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_fig:
        if output_dir is None:
            output_dir = OUTPUT_DIR
        output_path = Path(output_dir) / 'analise_pld.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Figura salva em: {output_path}")
    
    plt.show()


def gerar_todos_graficos(df_resultados, save_fig=True, output_dir=None):
    """
    Gera todos os gráficos de análise.
    
    Parâmetros:
    - df_resultados (pd.DataFrame): DataFrame com resultados da simulação
    - save_fig (bool): Se True, salva as figuras
    - output_dir (str/Path): Diretório para salvar figuras
    """
    print("Gerando gráficos de análise...")
    
    plot_distribuicao_renovavel(df_resultados, save_fig=save_fig, output_dir=output_dir)
    plot_boxplot_despacho_hora(df_resultados, save_fig=save_fig, output_dir=output_dir)
    plot_perfil_geracao_cenario(df_resultados, save_fig=save_fig, output_dir=output_dir)
    plot_curtailment_analise(df_resultados, save_fig=save_fig, output_dir=output_dir)
    plot_pld_analise(df_resultados, save_fig=save_fig, output_dir=output_dir)
    
    print("✅ Todos os gráficos foram gerados!")



