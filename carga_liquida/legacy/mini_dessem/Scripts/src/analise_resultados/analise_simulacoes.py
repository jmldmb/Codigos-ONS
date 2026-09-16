"""
Análise Completa de Resultados - Mini DESSEM
================================================

Este script realiza análises detalhadas dos resultados da simulação:
1. Análise de perfil horário (geração, carga, despacho)
2. Análise estatística (distribuições, correlações)
3. Análise de curtailment e PLD
4. Comparação entre cenários

Uso:
    python analise_simulacoes.py
    python analise_simulacoes.py --arquivo resultados_simulacao_YYYYMMDD_HHMMSS.parquet
    python analise_simulacoes.py --ultimo  # analisa o arquivo mais recente
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D
from pathlib import Path
import argparse
from scipy import stats


# Adicionar src ao path (subir dois níveis: analise_resultados -> src -> Scripts -> src)
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

from mini_dessem.config import OUTPUT_DIR


def carregar_resultados(arquivo_path=None):
    """Carrega resultados da simulação."""
    
    if arquivo_path is None:
        # Buscar arquivo mais recente
        arquivos = list(OUTPUT_DIR.glob('resultados_simulacao_*.parquet'))
        if not arquivos:
            raise FileNotFoundError(f"Nenhum arquivo de resultados encontrado em {OUTPUT_DIR}")
        
        arquivo_path = max(arquivos, key=lambda p: p.stat().st_mtime)
        print(f"Usando arquivo mais recente: {arquivo_path.name}")
    
    print(f"\nCarregando: {arquivo_path}")
    df = pd.read_parquet(arquivo_path)
    
    print(f"  Registros: {len(df):,}")
    print(f"  Colunas: {len(df.columns)}")
    
    return df


def analisar_perfis_horarios(df, output_dir, ano):
    """Análise de perfis horários por ano e por mês."""
    
    print(f"\n  >> Perfis Horários - {ano}")
    
    # Filtrar por ano
    df_ano = df[df['ano'] == ano]
    
    if len(df_ano) == 0:
        print(f"  [!] Sem dados para {ano}")
        return
    
    # Criar diretório para perfis horários
    perfil_dir = output_dir / 'perfil_horario'
    perfil_dir.mkdir(parents=True, exist_ok=True)
    
    # Processar cada mês
    meses = sorted(df_ano['mes'].unique())
    
    for mes in meses:
        df_mes = df_ano[df_ano['mes'] == mes]
        
        # Calcular estatísticas por hora
        stats_hora = df_mes.groupby('hora').agg({
            'val_gereolica_depois_corte': ['mean', 'std', 'min', 'max', lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)],
            'val_gersolar_cent_depois_corte': ['mean', 'std', 'min', 'max', lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)],
            'val_gersolar_dist_depois_corte': ['mean', 'std', 'min', 'max', lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)],
            'val_gerhidro_fd': ['mean', 'std', 'min', 'max', lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)],
            'val_gerhidro_reservatorio': ['mean', 'std', 'min', 'max', lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)],
            'val_carga': ['mean', 'std', 'min', 'max', lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)],
            'val_term_despacho': ['mean', 'std', 'min', 'max', lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)]
        })
        
        # Renomear colunas para facilitar acesso
        stats_hora.columns = ['_'.join(col).strip() for col in stats_hora.columns.values]
        stats_hora = stats_hora.reset_index()
        
        # Criar figura 2x2
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle(f'Perfis Horários - {ano} - Mês {mes:02d}', fontsize=16, fontweight='bold')
        
        # Eólica (pós-corte)
        ax = axes[0, 0]
        ax.plot(stats_hora['hora'], stats_hora['val_gereolica_depois_corte_mean'], 'b-', linewidth=2.5, label='Média', zorder=3)
        ax.fill_between(stats_hora['hora'], 
                        stats_hora['val_gereolica_depois_corte_mean'] - stats_hora['val_gereolica_depois_corte_std'],
                        stats_hora['val_gereolica_depois_corte_mean'] + stats_hora['val_gereolica_depois_corte_std'],
                        alpha=0.3, color='blue', label='±1σ', zorder=2)
        ax.fill_between(stats_hora['hora'], 
                        stats_hora['val_gereolica_depois_corte_<lambda_0>'],
                        stats_hora['val_gereolica_depois_corte_<lambda_1>'],
                        alpha=0.15, color='cyan', label='P5-P95', zorder=1)
        ax.plot(stats_hora['hora'], stats_hora['val_gereolica_depois_corte_min'], 'b--', linewidth=1, alpha=0.7, label='Min/Max')
        ax.plot(stats_hora['hora'], stats_hora['val_gereolica_depois_corte_max'], 'b--', linewidth=1, alpha=0.7)
        ax.set_title('Geração Eólica (pós-curtailment)', fontweight='bold', fontsize=12)
        ax.set_xlabel('Hora', fontsize=10)
        ax.set_ylabel('MW', fontsize=10)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
        
        # Solar (pós-corte, stacked: centralizada + distribuída)
        ax = axes[0, 1]
        # Stack: centralizada em baixo, distribuída em cima
        ax.fill_between(stats_hora['hora'], 0, stats_hora['val_gersolar_cent_depois_corte_mean'], 
                        color='orange', alpha=0.7, label='Solar Centralizada', zorder=2)
        ax.fill_between(stats_hora['hora'], 
                        stats_hora['val_gersolar_cent_depois_corte_mean'],
                        stats_hora['val_gersolar_cent_depois_corte_mean'] + stats_hora['val_gersolar_dist_depois_corte_mean'],
                        color='gold', alpha=0.7, label='Solar Distribuída', zorder=2)
        # Linha do total
        total_solar = stats_hora['val_gersolar_cent_depois_corte_mean'] + stats_hora['val_gersolar_dist_depois_corte_mean']
        ax.plot(stats_hora['hora'], total_solar, 'k-', linewidth=2, label='Total Solar', zorder=3)
        # Min/Max do total
        total_solar_min = stats_hora['val_gersolar_cent_depois_corte_min'] + stats_hora['val_gersolar_dist_depois_corte_min']
        total_solar_max = stats_hora['val_gersolar_cent_depois_corte_max'] + stats_hora['val_gersolar_dist_depois_corte_max']
        ax.plot(stats_hora['hora'], total_solar_min, 'k--', linewidth=1, alpha=0.5)
        ax.plot(stats_hora['hora'], total_solar_max, 'k--', linewidth=1, alpha=0.5)
        ax.set_title('Geração Solar (pós-curtailment)', fontweight='bold', fontsize=12)
        ax.set_xlabel('Hora', fontsize=10)
        ax.set_ylabel('MW', fontsize=10)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
        
        # Hidro (stacked: fio d'água + reservatório)
        ax = axes[1, 0]
        # Stack: fio d'água em baixo, reservatório em cima
        ax.fill_between(stats_hora['hora'], 0, stats_hora['val_gerhidro_fd_mean'], 
                        color='skyblue', alpha=0.7, label='Hidro Fio d\'Água', zorder=2)
        ax.fill_between(stats_hora['hora'], 
                        stats_hora['val_gerhidro_fd_mean'],
                        stats_hora['val_gerhidro_fd_mean'] + stats_hora['val_gerhidro_reservatorio_mean'],
                        color='steelblue', alpha=0.7, label='Hidro Reservatório', zorder=2)
        # Linha do total
        total_hidro = stats_hora['val_gerhidro_fd_mean'] + stats_hora['val_gerhidro_reservatorio_mean']
        ax.plot(stats_hora['hora'], total_hidro, 'navy', linewidth=2, label='Total Hidro', zorder=3)
        # Min/Max do total
        total_hidro_min = stats_hora['val_gerhidro_fd_min'] + stats_hora['val_gerhidro_reservatorio_min']
        total_hidro_max = stats_hora['val_gerhidro_fd_max'] + stats_hora['val_gerhidro_reservatorio_max']
        ax.plot(stats_hora['hora'], total_hidro_min, 'navy', linestyle='--', linewidth=1, alpha=0.5)
        ax.plot(stats_hora['hora'], total_hidro_max, 'navy', linestyle='--', linewidth=1, alpha=0.5)
        ax.set_title('Geração Hidrelétrica', fontweight='bold', fontsize=12)
        ax.set_xlabel('Hora', fontsize=10)
        ax.set_ylabel('MW', fontsize=10)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
        
        # Carga e Térmica juntas para contexto
        ax = axes[1, 1]
        ax.plot(stats_hora['hora'], stats_hora['val_carga_mean'], 'g-', linewidth=2.5, label='Carga', zorder=3)
        ax.fill_between(stats_hora['hora'], 
                        stats_hora['val_carga_<lambda_0>'],
                        stats_hora['val_carga_<lambda_1>'],
                        alpha=0.2, color='green', label='Carga P5-P95', zorder=1)
        ax.plot(stats_hora['hora'], stats_hora['val_term_despacho_mean'], 'r-', linewidth=2.5, label='Térmica', zorder=3)
        ax.fill_between(stats_hora['hora'], 
                        stats_hora['val_term_despacho_<lambda_0>'],
                        stats_hora['val_term_despacho_<lambda_1>'],
                        alpha=0.2, color='red', label='Térmica P5-P95', zorder=1)
        ax.set_title('Carga e Despacho Térmico', fontweight='bold', fontsize=12)
        ax.set_xlabel('Hora', fontsize=10)
        ax.set_ylabel('MW', fontsize=10)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = perfil_dir / f'perfil_horario_{ano}_mes{mes:02d}.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    print(f"     [OK] {len(meses)} gráficos salvos em perfil_horario/")


def analisar_scatter_carga_curtailment(df, output_dir, ano):
    """Gera scatter plot de Carga Líquida vs Curtailment."""
    
    print(f"\n  >> Scatter: Carga Líquida vs Curtailment - {ano}")
    
    # Filtrar por ano
    df_ano = df[df['ano'] == ano]
    
    if len(df_ano) == 0:
        print(f"  [!] Sem dados para {ano}")
        return
    
    # Verificar se as colunas necessárias existem
    if 'carga_liquida' not in df_ano.columns or 'curtailment' not in df_ano.columns:
        print(f"  [!] Colunas 'carga_liquida' ou 'curtailment' não encontradas")
        return
    
    # Criar diretório para curtailment
    curtail_dir = output_dir / 'curtailment'
    curtail_dir.mkdir(parents=True, exist_ok=True)
    
    # Filtrar apenas registros com curtailment > 0 para o scatter
    df_com_curtail = df_ano[df_ano['curtailment'] > 0].copy()
    
    if len(df_com_curtail) == 0:
        print(f"  [!] Sem curtailment em {ano} para gerar scatter")
        return
    
    print(f"     Registros com curtailment: {len(df_com_curtail):,} de {len(df_ano):,}")
    
    # Criar figura
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    # Scatter plot colorido por HORA do dia
    scatter = ax.scatter(df_com_curtail['carga_liquida'], 
                        df_com_curtail['curtailment'],
                        c=df_com_curtail['hora'], 
                        cmap='viridis',
                        alpha=0.6, 
                        s=30,
                        edgecolors='black',
                        linewidth=0.3,
                        vmin=0,
                        vmax=23)
    
    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax, ticks=range(0, 24, 2))
    cbar.set_label('Hora do Dia', fontsize=12)
    
    # Calcular e plotar linha de tendência
    mask = ~np.isnan(df_com_curtail['carga_liquida']) & ~np.isnan(df_com_curtail['curtailment'])
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        df_com_curtail.loc[mask, 'carga_liquida'], 
        df_com_curtail.loc[mask, 'curtailment']
    )
    
    x_trend = np.array([df_com_curtail['carga_liquida'].min(), df_com_curtail['carga_liquida'].max()])
    y_trend = slope * x_trend + intercept
    ax.plot(x_trend, y_trend, 'r--', linewidth=2, label=f'Tendência (R²={r_value**2:.3f})', alpha=0.8)
    
    # Configurações do gráfico
    ax.set_xlabel('Carga Líquida (MW)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Curtailment (MW)', fontsize=13, fontweight='bold')
    ax.set_title(f'Relação entre Carga Líquida e Curtailment - {ano}', 
                 fontsize=15, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Adicionar estatísticas no gráfico
    stats_text = f'Correlação: {r_value:.3f}\n'
    stats_text += f'Ocorrências: {len(df_com_curtail):,}\n'
    stats_text += f'Curtailment Médio: {df_com_curtail["curtailment"].mean():.0f} MW\n'
    stats_text += f'Carga Líq. Média: {df_com_curtail["carga_liquida"].mean():.0f} MW'
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    output_path = curtail_dir / f'scatter_carga_vs_curtailment_{ano}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"     [OK] Salvo: curtailment/{output_path.name}")
    plt.close()


def analisar_curtailment(df, output_dir, ano):
    """Análise de curtailment por ano."""
    
    print(f"\n  >> Curtailment - {ano}")
    
    # Filtrar por ano
    df_ano = df[df['ano'] == ano]
    
    if len(df_ano) == 0:
        print(f"  [!] Sem dados para {ano}")
        return
    
    # Criar diretório para curtailment
    curtail_dir = output_dir / 'curtailment'
    curtail_dir.mkdir(parents=True, exist_ok=True)
    
    total_curtailment = df_ano['curtailment'].sum()
    ocorrencias = (df_ano['curtailment'] > 0).sum()
    pct_ocorrencias = (ocorrencias / len(df_ano)) * 100
    
    print(f"\n     Curtailment Total: {total_curtailment:,.0f} MWh")
    print(f"     Ocorrências: {ocorrencias:,} ({pct_ocorrencias:.2f}% das horas)")
    
    if 'curtailment_eolica' in df_ano.columns:
        print(f"\n     Curtailment por componente:")
        print(f"       Eólica:            {df_ano['curtailment_eolica'].sum():>12,.0f} MWh ({df_ano['curtailment_eolica'].sum()/total_curtailment*100:.1f}%)")
        print(f"       Solar Centralizada:{df_ano['curtailment_solar_cent'].sum():>12,.0f} MWh ({df_ano['curtailment_solar_cent'].sum()/total_curtailment*100:.1f}%)")
        print(f"       Solar Distribuída: {df_ano['curtailment_solar_dist'].sum():>12,.0f} MWh ({df_ano['curtailment_solar_dist'].sum()/total_curtailment*100:.1f}%)")
    
    if ocorrencias == 0:
        print(f"     [!] Sem curtailment em {ano}")
        return
    
    # Criar figura com 4 gráficos
    fig, axes = plt.subplots(4, 1, figsize=(16, 18))
    fig.suptitle(f'Análise de Curtailment - {ano}', fontsize=16, fontweight='bold')
    
    # 1. Curtailment por hora para todos os 12 meses (linhas sobrepostas)
    ax = axes[0]
    for mes in range(1, 13):
        df_mes = df_ano[df_ano['mes'] == mes]
        if len(df_mes) > 0:
            curtail_hora_mes = df_mes.groupby('hora')['curtailment'].mean()
            ax.plot(curtail_hora_mes.index, curtail_hora_mes.values, marker='o', linewidth=1.5, 
                   label=f'Mês {mes}', alpha=0.7)
    ax.set_title('Curtailment Médio por Hora - Todos os Meses', fontweight='bold', fontsize=12)
    ax.set_xlabel('Hora', fontsize=10)
    ax.set_ylabel('MW', fontsize=10)
    ax.legend(ncol=4, fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # 2. Curtailment total por mês - Barras empilhadas (MWmédio)
    ax = axes[1]
    if 'curtailment_eolica' in df_ano.columns:
        # Calcular MWmédio por mês (soma MWh / horas no mês)
        curtail_mes = df_ano.groupby('mes').agg({
            'curtailment_eolica': 'sum',
            'curtailment_solar_cent': 'sum',
            'curtailment_solar_dist': 'sum'
        })
        
        # Contar horas por mês
        horas_por_mes = df_ano.groupby('mes').size()
        
        # Converter para MWmédio
        curtail_mes_mwm = curtail_mes.div(horas_por_mes, axis=0)
        
        meses = curtail_mes_mwm.index
        eolica = curtail_mes_mwm['curtailment_eolica']
        solar_cent = curtail_mes_mwm['curtailment_solar_cent']
        solar_dist = curtail_mes_mwm['curtailment_solar_dist']
        
        ax.bar(meses, eolica, label='Eólica', color='steelblue', alpha=0.8)
        ax.bar(meses, solar_cent, bottom=eolica, label='Solar Centralizada', color='orange', alpha=0.8)
        
        # Só mostrar Solar Distribuída se houver dados
        if solar_dist.sum() > 0:
            ax.bar(meses, solar_dist, bottom=eolica+solar_cent, label='Solar Distribuída', color='gold', alpha=0.8)
        
        # Calcular e adicionar linha de média aritmética total
        curtail_total_mes = eolica + solar_cent + solar_dist
        media_aritmetica = curtail_total_mes.mean()
        ax.axhline(y=media_aritmetica, color='red', linestyle='--', linewidth=2.5, 
                   label=f'Média: {media_aritmetica:.1f} MWmédio', alpha=0.9, zorder=10)
        
        ax.set_title('Curtailment Médio por Mês (MWmédio) - Empilhado', fontweight='bold', fontsize=12)
        ax.set_xlabel('Mês', fontsize=10)
        ax.set_ylabel('MWmédio', fontsize=10)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(range(1, 13))
    
    # 3. Percentual de curtailment por mês - Barras empilhadas
    ax = axes[2]
    if 'curtailment_eolica' in df_ano.columns:
        # Calcular % curtailment = curtailment / geração_pré * 100
        df_ano_copy = df_ano.copy()
        
        # NOVO: Calcular geração pré-curtailment de cada fonte
        if 'val_gereolica_antes_corte' in df_ano_copy.columns:
            df_ano_copy['ger_eolica_pre'] = df_ano_copy['val_gereolica_antes_corte']
        else:
            df_ano_copy['ger_eolica_pre'] = df_ano_copy['val_gereolica']
        
        if 'val_gersolar_cent_antes_corte' in df_ano_copy.columns:
            df_ano_copy['ger_solar_cent_pre'] = df_ano_copy['val_gersolar_cent_antes_corte']
        elif 'val_gersolar_cent_depois_corte' in df_ano_copy.columns:
            df_ano_copy['ger_solar_cent_pre'] = df_ano_copy['val_gersolar_cent_depois_corte'] + df_ano_copy['curtailment_solar_cent']
        else:
            df_ano_copy['ger_solar_cent_pre'] = df_ano_copy['val_gersolar'] * 0.36
        
        # Denominador TOTAL (SEM distribuída) - apenas fontes despacháveis
        df_ano_copy['ger_total_despacho_pre'] = df_ano_copy['ger_eolica_pre'] + df_ano_copy['ger_solar_cent_pre']
        
        # Geração pré-curtailment distribuída também
        if 'val_gersolar_dist_antes_corte' in df_ano_copy.columns:
            df_ano_copy['ger_solar_dist_pre'] = df_ano_copy['val_gersolar_dist_antes_corte']
        elif 'val_gersolar_dist_depois_corte' in df_ano_copy.columns:
            df_ano_copy['ger_solar_dist_pre'] = df_ano_copy['val_gersolar_dist_depois_corte'] + df_ano_copy['curtailment_solar_dist']
        else:
            df_ano_copy['ger_solar_dist_pre'] = df_ano_copy['val_gersolar'] * 0.64
        
        # % TOTAL (para linha vermelha)
        df_ano_copy['curtailment_total'] = (df_ano_copy['curtailment_eolica'] + 
                                              df_ano_copy['curtailment_solar_cent'] + 
                                              df_ano_copy['curtailment_solar_dist'])
        df_ano_copy['pct_total'] = np.where(
            df_ano_copy['ger_total_despacho_pre'] > 0,
            (df_ano_copy['curtailment_total'] / df_ano_copy['ger_total_despacho_pre']) * 100,
            0
        )
        
        # Agregar por mês PRIMEIRO (somar curtailment e geração)
        # Depois calcular % contribuição de cada fonte ao total
        
        mensal_contrib = df_ano_copy.groupby('mes').agg({
            'curtailment_eolica': 'sum',
            'curtailment_solar_cent': 'sum',
            'curtailment_solar_dist': 'sum',
            'curtailment_total': 'sum',
            'ger_total_despacho_pre': 'sum',
            'pct_total': 'mean'  # Este já é calculado corretamente
        })
        
        # Calcular contribuição de cada fonte (em relação ao denominador comum)
        mensal_contrib['pct_eolica_contrib'] = (
            mensal_contrib['curtailment_eolica'] / mensal_contrib['ger_total_despacho_pre']
        ) * 100
        
        mensal_contrib['pct_solar_cent_contrib'] = (
            mensal_contrib['curtailment_solar_cent'] / mensal_contrib['ger_total_despacho_pre']
        ) * 100
        
        mensal_contrib['pct_solar_dist_contrib'] = (
            mensal_contrib['curtailment_solar_dist'] / mensal_contrib['ger_total_despacho_pre']
        ) * 100
        
        meses = mensal_contrib.index
        pct_eolica = mensal_contrib['pct_eolica_contrib']
        pct_solar_cent = mensal_contrib['pct_solar_cent_contrib']
        pct_solar_dist = mensal_contrib['pct_solar_dist_contrib']
        pct_total_mes = mensal_contrib['pct_total']
        
        # Barras empilhadas - cada fonte mostra sua contribuição ao total
        ax.bar(meses, pct_eolica, label='Eólica', color='steelblue', alpha=0.8)
        ax.bar(meses, pct_solar_cent, bottom=pct_eolica, label='Solar Centralizada', color='orange', alpha=0.8)
        
        # Só mostrar Solar Distribuída se houver dados
        if pct_solar_dist.sum() > 0:
            ax.bar(meses, pct_solar_dist, bottom=pct_eolica+pct_solar_cent, label='Solar Distribuída', color='gold', alpha=0.8)
        
        # Linha vermelha: % total médio
        pct_medio_total = pct_total_mes.mean()
        ax.axhline(y=pct_medio_total, color='red', linestyle='--', linewidth=2.5, 
                   label=f'% Total Médio: {pct_medio_total:.1f}%', alpha=0.9, zorder=10)
        
        ax.set_title('% Curtailment por Mês - Contribuição ao Total (empilhado)', fontweight='bold', fontsize=12)
        ax.set_xlabel('Mês', fontsize=10)
        ax.set_ylabel('% Curtailment', fontsize=10)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(range(1, 13))
    
    # 4. Percentual de curtailment por FONTE (cada fonte em relação à sua própria geração)
    ax = axes[3]
    if 'curtailment_eolica' in df_ano.columns:
        df_ano_copy2 = df_ano.copy()
        
        # Geração pré-curtailment de cada fonte
        if 'val_gereolica_antes_corte' in df_ano_copy2.columns:
            df_ano_copy2['ger_eolica_pre'] = df_ano_copy2['val_gereolica_antes_corte']
        else:
            df_ano_copy2['ger_eolica_pre'] = df_ano_copy2['val_gereolica']
        
        if 'val_gersolar_cent_antes_corte' in df_ano_copy2.columns:
            df_ano_copy2['ger_solar_cent_pre'] = df_ano_copy2['val_gersolar_cent_antes_corte']
        elif 'val_gersolar_cent_depois_corte' in df_ano_copy2.columns:
            df_ano_copy2['ger_solar_cent_pre'] = df_ano_copy2['val_gersolar_cent_depois_corte'] + df_ano_copy2['curtailment_solar_cent']
        else:
            df_ano_copy2['ger_solar_cent_pre'] = df_ano_copy2['val_gersolar'] * 0.36
        
        if 'val_gersolar_dist_antes_corte' in df_ano_copy2.columns:
            df_ano_copy2['ger_solar_dist_pre'] = df_ano_copy2['val_gersolar_dist_antes_corte']
        elif 'val_gersolar_dist_depois_corte' in df_ano_copy2.columns:
            df_ano_copy2['ger_solar_dist_pre'] = df_ano_copy2['val_gersolar_dist_depois_corte'] + df_ano_copy2['curtailment_solar_dist']
        else:
            df_ano_copy2['ger_solar_dist_pre'] = df_ano_copy2['val_gersolar'] * 0.64
        
        # Agregar por mês PRIMEIRO (somar curtailment e geração de cada fonte)
        # Depois calcular % = curtail_mensal / ger_mensal
        # Isso captura a diferença entre fontes (solar só gera de dia, eólica 24h)
        
        mensal_proprio = df_ano_copy2.groupby('mes').agg({
            'curtailment_eolica': 'sum',
            'curtailment_solar_cent': 'sum',
            'curtailment_solar_dist': 'sum',
            'ger_eolica_pre': 'sum',
            'ger_solar_cent_pre': 'sum',
            'ger_solar_dist_pre': 'sum'
        })
        
        # Calcular % por mês (agregado)
        mensal_proprio['pct_eolica'] = np.where(
            mensal_proprio['ger_eolica_pre'] > 0,
            (mensal_proprio['curtailment_eolica'] / mensal_proprio['ger_eolica_pre']) * 100,
            0
        )
        
        mensal_proprio['pct_solar_cent'] = np.where(
            mensal_proprio['ger_solar_cent_pre'] > 0,
            (mensal_proprio['curtailment_solar_cent'] / mensal_proprio['ger_solar_cent_pre']) * 100,
            0
        )
        
        mensal_proprio['pct_solar_dist'] = np.where(
            mensal_proprio['ger_solar_dist_pre'] > 0,
            (mensal_proprio['curtailment_solar_dist'] / mensal_proprio['ger_solar_dist_pre']) * 100,
            0
        )
        
        meses_proprio = mensal_proprio.index
        pct_eolica_proprio = mensal_proprio['pct_eolica']
        pct_solar_cent_proprio = mensal_proprio['pct_solar_cent']
        pct_solar_dist_proprio = mensal_proprio['pct_solar_dist']
        
        # Calcular médias para as linhas horizontais
        # Usar a mesma metodologia: média dos % mensais calculados por agregação
        media_eolica_proprio = pct_eolica_proprio.mean()
        media_solar_cent_proprio = pct_solar_cent_proprio.mean()
        media_solar_dist_proprio = pct_solar_dist_proprio.mean()
        
        # Barras lado a lado (não empilhadas)
        # Ajustar width e posições baseado em quantas fontes têm dados
        tem_solar_dist = pct_solar_dist_proprio.sum() > 0
        
        if tem_solar_dist:
            width = 0.25
            x = np.arange(len(meses_proprio))
            ax.bar(x - width, pct_eolica_proprio, width, label='Eólica (vs própria)', color='steelblue', alpha=0.8)
            ax.bar(x, pct_solar_cent_proprio, width, label='Solar Cent (vs própria)', color='orange', alpha=0.8)
            ax.bar(x + width, pct_solar_dist_proprio, width, label='Solar Dist (vs própria)', color='gold', alpha=0.8)
        else:
            # Sem solar distribuída - barras mais largas, centralizar
            width = 0.35
            x = np.arange(len(meses_proprio))
            ax.bar(x - width/2, pct_eolica_proprio, width, label='Eólica (vs própria)', color='steelblue', alpha=0.8)
            ax.bar(x + width/2, pct_solar_cent_proprio, width, label='Solar Cent (vs própria)', color='orange', alpha=0.8)
        
        # Adicionar linhas horizontais com as médias
        ax.axhline(y=media_eolica_proprio, color='darkblue', linestyle='--', linewidth=2.5, 
                   label=f'Média Eólica: {media_eolica_proprio:.2f}%', alpha=0.8, zorder=10)
        ax.axhline(y=media_solar_cent_proprio, color='darkorange', linestyle='--', linewidth=2.5, 
                   label=f'Média Solar Cent: {media_solar_cent_proprio:.2f}%', alpha=0.8, zorder=10)
        
        if tem_solar_dist and media_solar_dist_proprio > 0:
            ax.axhline(y=media_solar_dist_proprio, color='darkgoldenrod', linestyle='--', linewidth=2.5, 
                       label=f'Média Solar Dist: {media_solar_dist_proprio:.2f}%', alpha=0.8, zorder=10)
        
        ax.set_title('% Curtailment por Fonte (em relação à própria geração)', fontweight='bold', fontsize=12)
        ax.set_xlabel('Mês', fontsize=10)
        ax.set_ylabel('% Curtailment', fontsize=10)
        ax.legend(fontsize=8, loc='best', ncol=2)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(x)
        ax.set_xticklabels(meses_proprio)
    
    plt.tight_layout()
    output_path = curtail_dir / f'curtailment_{ano}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"     [OK] Salvo: curtailment/{output_path.name}")
    plt.close()


def preparar_dados_curtailment_base(df):
    """Prepara dataframe com colunas necessárias para análises multi-ano."""

    required_cols = {'ano', 'mes'}
    if not required_cols.issubset(df.columns):
        print("  [!] Dados insuficientes para gráficos multi-ano de curtailment")
        return None

    componentes_cols = ['curtailment_eolica', 'curtailment_solar_cent', 'curtailment_solar_dist']
    if not any(col in df.columns for col in componentes_cols):
        print("  [!] Colunas de curtailment por componente não encontradas para gráficos multi-ano")
        return None

    df_base = df.copy()

    # Garantir que colunas de curtailment existam e não tenham NaN
    for col in componentes_cols:
        if col not in df_base.columns:
            df_base[col] = 0.0
    df_base[componentes_cols] = df_base[componentes_cols].fillna(0.0)

    # Garantir colunas de geração necessárias
    if 'val_gereolica' not in df_base.columns:
        df_base['val_gereolica'] = 0.0
    if 'val_gersolar' not in df_base.columns:
        df_base['val_gersolar'] = 0.0
    if 'val_gersolar_cent_depois_corte' not in df_base.columns:
        df_base['val_gersolar_cent_depois_corte'] = 0.0
    if 'val_gersolar_dist_depois_corte' not in df_base.columns:
        df_base['val_gersolar_dist_depois_corte'] = 0.0

    # Geração pré-curtailment
    if 'val_gereolica_antes_corte' in df_base.columns:
        df_base['ger_eolica_pre'] = df_base['val_gereolica_antes_corte']
    else:
        df_base['ger_eolica_pre'] = df_base['val_gereolica']

    if 'val_gersolar_cent_antes_corte' in df_base.columns:
        df_base['ger_solar_cent_pre'] = df_base['val_gersolar_cent_antes_corte']
    else:
        df_base['ger_solar_cent_pre'] = df_base['val_gersolar_cent_depois_corte'] + df_base['curtailment_solar_cent']

    if 'val_gersolar_dist_antes_corte' in df_base.columns:
        df_base['ger_solar_dist_pre'] = df_base['val_gersolar_dist_antes_corte']
    else:
        df_base['ger_solar_dist_pre'] = df_base['val_gersolar_dist_depois_corte'] + df_base['curtailment_solar_dist']

    df_base[['ger_eolica_pre', 'ger_solar_cent_pre', 'ger_solar_dist_pre']] = (
        df_base[['ger_eolica_pre', 'ger_solar_cent_pre', 'ger_solar_dist_pre']].fillna(0.0)
    )

    df_base['curtailment_total'] = (
        df_base['curtailment_eolica'] + df_base['curtailment_solar_cent'] + df_base['curtailment_solar_dist']
    )
    df_base['ger_total_despacho_pre'] = df_base['ger_eolica_pre'] + df_base['ger_solar_cent_pre']

    df_base['pct_total'] = np.where(
        df_base['ger_total_despacho_pre'] > 0,
        (df_base['curtailment_total'] / df_base['ger_total_despacho_pre']) * 100,
        np.nan
    )

    return df_base


def gerar_graficos_curtailment_multiano(df, output_dir):
    """Gera gráficos adicionais agregando múltiplos anos para curtailment."""

    df_base = preparar_dados_curtailment_base(df)
    if df_base is None:
        return

    curtail_dir = output_dir / 'curtailment'
    curtail_dir.mkdir(parents=True, exist_ok=True)

    agrupamento = df_base.groupby(['ano', 'mes']).agg({
        'curtailment_eolica': 'sum',
        'curtailment_solar_cent': 'sum',
        'curtailment_solar_dist': 'sum',
        'curtailment_total': 'sum',
        'ger_total_despacho_pre': 'sum',
        'ger_eolica_pre': 'sum',
        'ger_solar_cent_pre': 'sum',
        'ger_solar_dist_pre': 'sum',
        'pct_total': 'mean'
    }).reset_index()

    agrupamento.rename(columns={'pct_total': 'pct_total_media'}, inplace=True)

    if agrupamento.empty:
        print("  [!] Sem dados agregados para gráficos multi-ano de curtailment")
        return

    agrupamento['ano'] = agrupamento['ano'].astype(int)
    agrupamento['mes'] = agrupamento['mes'].astype(int)
    agrupamento.sort_values(['ano', 'mes'], inplace=True)

    agrupamento['pct_total'] = np.where(
        agrupamento['ger_total_despacho_pre'] > 0,
        (agrupamento['curtailment_total'] / agrupamento['ger_total_despacho_pre']) * 100,
        np.nan
    )
    agrupamento['pct_eolica_contrib'] = np.where(
        agrupamento['ger_total_despacho_pre'] > 0,
        (agrupamento['curtailment_eolica'] / agrupamento['ger_total_despacho_pre']) * 100,
        0
    )
    agrupamento['pct_solar_cent_contrib'] = np.where(
        agrupamento['ger_total_despacho_pre'] > 0,
        (agrupamento['curtailment_solar_cent'] / agrupamento['ger_total_despacho_pre']) * 100,
        0
    )
    agrupamento['pct_solar_dist_contrib'] = np.where(
        agrupamento['ger_total_despacho_pre'] > 0,
        (agrupamento['curtailment_solar_dist'] / agrupamento['ger_total_despacho_pre']) * 100,
        0
    )

    agrupamento['pct_eolica_proprio'] = np.where(
        agrupamento['ger_eolica_pre'] > 0,
        (agrupamento['curtailment_eolica'] / agrupamento['ger_eolica_pre']) * 100,
        np.nan
    )

    agrupamento['ger_solar_total_pre'] = agrupamento['ger_solar_cent_pre'] + agrupamento['ger_solar_dist_pre']
    agrupamento['curtailment_solar_total'] = (
        agrupamento['curtailment_solar_cent'] + agrupamento['curtailment_solar_dist']
    )
    agrupamento['pct_solar_total'] = np.where(
        agrupamento['ger_solar_total_pre'] > 0,
        (agrupamento['curtailment_solar_total'] / agrupamento['ger_solar_total_pre']) * 100,
        np.nan
    )
    agrupamento['pct_solar_cent_total'] = np.where(
        agrupamento['ger_solar_total_pre'] > 0,
        (agrupamento['curtailment_solar_cent'] / agrupamento['ger_solar_total_pre']) * 100,
        0
    )
    agrupamento['pct_solar_dist_total'] = np.where(
        agrupamento['ger_solar_total_pre'] > 0,
        (agrupamento['curtailment_solar_dist'] / agrupamento['ger_solar_total_pre']) * 100,
        0
    )
    agrupamento['pct_solar_cent_proprio'] = np.where(
        agrupamento['ger_solar_cent_pre'] > 0,
        (agrupamento['curtailment_solar_cent'] / agrupamento['ger_solar_cent_pre']) * 100,
        np.nan
    )
    agrupamento['pct_solar_dist_proprio'] = np.where(
        agrupamento['ger_solar_dist_pre'] > 0,
        (agrupamento['curtailment_solar_dist'] / agrupamento['ger_solar_dist_pre']) * 100,
        np.nan
    )

    agrupamento['label'] = agrupamento.apply(lambda row: f"{row['ano']}-{int(row['mes']):02d}", axis=1)
    x = np.arange(len(agrupamento))

    anos = sorted(agrupamento['ano'].unique())
    line_palette = sns.color_palette('Dark2', len(anos))

    def aplicar_xticks(ax, labels):
        if len(labels) > 24:
            step = max(1, len(labels) // 24)
            indices = x[::step]
            ax.set_xticks(indices)
            ax.set_xticklabels(labels[::step], rotation=45, ha='right')
        else:
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha='right')

    # Gráfico 1 - % total (sem separação por fonte)
    fig, ax = plt.subplots(figsize=(18, 9))
    valores_pct_total = agrupamento['pct_total_media'].fillna(0.0)
    barras_total = ax.bar(x, valores_pct_total, color='steelblue', alpha=0.85, label='% Curtailment Total')

    line_handles = []
    linha_cor = 'dimgray'
    for ano in anos:
        mask = agrupamento['ano'] == ano
        media = agrupamento.loc[mask, 'pct_total_media'].dropna().mean()
        if np.isnan(media):
            continue
        xmin = x[mask].min() - 0.4
        xmax = x[mask].max() + 0.4
        ax.hlines(media, xmin, xmax, colors=linha_cor, linestyles='--', linewidth=2.5)
        line_handles.append(Line2D([0], [0], color=linha_cor, linestyle='--', linewidth=2.5, label=f'Média {ano}: {media:.1f}%'))

    aplicar_xticks(ax, agrupamento['label'].tolist())
    ax.set_ylabel('% Curtailment')
    ax.set_title('Curtailment (% Total) por Mês-Ano')
    ax.grid(True, axis='y', alpha=0.3)

    handles = [barras_total]
    handles.extend(line_handles)
    ax.legend(handles=handles, fontsize=9, loc='best', ncol=2)

    plt.tight_layout()
    fig.savefig(curtail_dir / 'curtailment_pct_total_mes_ano.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # Gráfico 2 - % eólica (a partir do gráfico 4)
    fig, ax = plt.subplots(figsize=(18, 7))
    bar_eolica_pct = ax.bar(x, agrupamento['pct_eolica_proprio'].fillna(0.0), color='steelblue', alpha=0.85, label='% Eólica (vs própria geração)')

    line_handles = []
    for idx, ano in enumerate(anos):
        mask = agrupamento['ano'] == ano
        media = agrupamento.loc[mask, 'pct_eolica_proprio'].dropna().mean()
        if np.isnan(media):
            continue
        xmin = x[mask].min() - 0.4
        xmax = x[mask].max() + 0.4
        color = line_palette[idx]
        ax.hlines(media, xmin, xmax, colors=color, linestyles='--', linewidth=2.5)
        line_handles.append(Line2D([0], [0], color=color, linestyle='--', linewidth=2.5, label=f'Média {ano}: {media:.2f}%'))

    aplicar_xticks(ax, agrupamento['label'].tolist())
    ax.set_ylabel('% Curtailment')
    ax.set_title('Curtailment Eólico (% em relação à própria geração) por Mês-Ano')
    ax.grid(True, axis='y', alpha=0.3)

    handles = [bar_eolica_pct]
    handles.extend(line_handles)
    ax.legend(handles=handles, fontsize=9, loc='best')

    plt.tight_layout()
    fig.savefig(curtail_dir / 'curtailment_pct_eolico_mes_ano.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # Gráfico 3 - % solar total (a partir do gráfico 4)
    fig, ax = plt.subplots(figsize=(18, 9))
    valores_cent = agrupamento['pct_solar_cent_proprio'].fillna(0.0)
    bar_solar_cent_pct = ax.bar(x, valores_cent, color='orange', alpha=0.85, label='Solar Centralizada')
    bottom = valores_cent.values
    valores_dist = agrupamento['pct_solar_dist_proprio'].fillna(0.0)
    valid_solar_dist_total = valores_dist.abs().sum() > 1e-6
    if valid_solar_dist_total:
        bar_solar_dist_pct = ax.bar(x, valores_dist, bottom=bottom, color='gold', alpha=0.85, label='Solar Distribuída')
    else:
        bar_solar_dist_pct = None

    line_handles = []
    for idx, ano in enumerate(anos):
        mask = agrupamento['ano'] == ano
        media_cent = agrupamento.loc[mask, 'pct_solar_cent_proprio'].dropna().mean()
        xmin = x[mask].min() - 0.4
        xmax = x[mask].max() + 0.4
        color = line_palette[idx]
        if not np.isnan(media_cent):
            ax.hlines(media_cent, xmin, xmax, colors=color, linestyles='--', linewidth=2.5)
            line_handles.append(Line2D([0], [0], color=color, linestyle='--', linewidth=2.5,
                                       label=f'Média Solar Cent {ano}: {media_cent:.2f}%'))

        media_dist = agrupamento.loc[mask, 'pct_solar_dist_proprio'].dropna().mean()
        if valid_solar_dist_total and not np.isnan(media_dist):
            ax.hlines(media_dist, xmin, xmax, colors=color, linestyles='-.', linewidth=2.0)
            line_handles.append(Line2D([0], [0], color=color, linestyle='-.', linewidth=2.0,
                                       label=f'Média Solar Dist {ano}: {media_dist:.2f}%'))

    aplicar_xticks(ax, agrupamento['label'].tolist())
    ax.set_ylabel('% Curtailment')
    ax.set_title('Curtailment Solar (% em relação à geração total solar) por Mês-Ano')
    ax.grid(True, axis='y', alpha=0.3)

    handles = [bar_solar_cent_pct]
    if bar_solar_dist_pct is not None:
        handles.append(bar_solar_dist_pct)
    handles.extend(line_handles)
    ax.legend(handles=handles, fontsize=9, loc='best', ncol=2)

    plt.tight_layout()
    fig.savefig(curtail_dir / 'curtailment_pct_solar_mes_ano.png', dpi=150, bbox_inches='tight')
    plt.close(fig)


def analisar_carga_liquida(df, output_dir, ano):
    """Análise de Carga Líquida por ano - perfis por mês + resumo mensal."""
    
    print(f"\n  >> Carga Líquida - {ano}")
    
    # Filtrar por ano
    df_ano = df[df['ano'] == ano]
    
    if len(df_ano) == 0:
        print(f"  [!] Sem dados para {ano}")
        return
    
    # Verificar se a coluna existe
    if 'carga_liquida' not in df_ano.columns:
        print(f"  [!] Coluna 'carga_liquida' não encontrada")
        return
    
    # Criar diretório para carga líquida
    carga_liq_dir = output_dir / 'carga_liquida'
    carga_liq_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n     Carga Líquida Média: {df_ano['carga_liquida'].mean():,.0f} MW")
    print(f"     Min/Max: {df_ano['carga_liquida'].min():,.0f} / {df_ano['carga_liquida'].max():,.0f} MW")
    
    # Processar cada mês - PERFIS HORÁRIOS
    meses = sorted(df_ano['mes'].unique())
    
    for mes in meses:
        df_mes = df_ano[df_ano['mes'] == mes]
        
        # Calcular estatísticas por hora
        perfil_hora = df_mes.groupby('hora')['carga_liquida'].agg([
            'mean', 'std', 'min', 'max',
            ('p5', lambda x: np.percentile(x, 5)),
            ('p95', lambda x: np.percentile(x, 95))
        ])
        
        # Criar gráfico de perfil horário
        fig, ax = plt.subplots(1, 1, figsize=(16, 6))
        fig.suptitle(f'Perfil Horário de Carga Líquida - {ano} - Mês {mes:02d}', fontsize=16, fontweight='bold')
        
        ax.plot(perfil_hora.index, perfil_hora['mean'], 'purple', linewidth=2.5, label='Média', zorder=3)
        ax.fill_between(perfil_hora.index, 
                        perfil_hora['mean'] - perfil_hora['std'],
                        perfil_hora['mean'] + perfil_hora['std'],
                        alpha=0.3, color='purple', label='±1σ', zorder=2)
        ax.fill_between(perfil_hora.index, 
                        perfil_hora['p5'],
                        perfil_hora['p95'],
                        alpha=0.15, color='plum', label='P5-P95', zorder=1)
        ax.plot(perfil_hora.index, perfil_hora['min'], 'purple', linestyle='--', linewidth=1, alpha=0.5, label='Min/Max')
        ax.plot(perfil_hora.index, perfil_hora['max'], 'purple', linestyle='--', linewidth=1, alpha=0.5)
        
        # Linha em zero para referência
        ax.axhline(y=0, color='red', linestyle=':', linewidth=1.5, alpha=0.6, label='Zero')
        
        ax.set_title('Carga Líquida = Carga - Renováveis - Inflexível - Hidro FD', fontweight='bold', fontsize=11)
        ax.set_xlabel('Hora', fontsize=11)
        ax.set_ylabel('MW', fontsize=11)
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24))
        
        plt.tight_layout()
        output_path = carga_liq_dir / f'perfil_carga_liquida_{ano}_mes{mes:02d}.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    # Gráfico de resumo mensal
    fig, ax = plt.subplots(1, 1, figsize=(16, 6))
    fig.suptitle(f'Carga Líquida Média por Mês - {ano}', fontsize=16, fontweight='bold')
    
    carga_liq_mes = df_ano.groupby('mes')['carga_liquida'].agg(['mean', 'std', 'min', 'max'])
    
    meses_plot = carga_liq_mes.index
    
    # Barras para média
    ax.bar(meses_plot, carga_liq_mes['mean'], color='purple', alpha=0.7, edgecolor='black', label='Média')
    
    # Barras de erro (±std)
    ax.errorbar(meses_plot, carga_liq_mes['mean'], yerr=carga_liq_mes['std'], 
                fmt='none', ecolor='red', capsize=5, capthick=2, linewidth=2, label='±1σ', alpha=0.7)
    
    # Linha em zero
    ax.axhline(y=0, color='red', linestyle=':', linewidth=1.5, alpha=0.6)
    
    ax.set_title('Carga Líquida Média por Mês (com ±σ)', fontweight='bold', fontsize=12)
    ax.set_xlabel('Mês', fontsize=11)
    ax.set_ylabel('MW', fontsize=11)
    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(1, 13))
    
    plt.tight_layout()
    output_path = carga_liq_dir / f'resumo_mensal_carga_liquida_{ano}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"     [OK] {len(meses)} perfis horários + 1 resumo mensal salvos em carga_liquida/")


def analisar_pld(df, output_dir, ano):
    """Análise de PLD por ano - usando média por simulação."""
    
    print(f"\n  >> PLD - {ano}")
    
    # Filtrar por ano
    df_ano = df[df['ano'] == ano]
    
    if len(df_ano) == 0:
        print(f"  [!] Sem dados para {ano}")
        return
    
    # Criar diretório para PLD
    pld_dir = output_dir / 'pld'
    pld_dir.mkdir(parents=True, exist_ok=True)
    
    # NOVO: Calcular PLD médio por simulação primeiro
    # Agrupar por (ano, mes, simulacao) e calcular média
    pld_por_simulacao = df_ano.groupby(['ano', 'mes', 'simulacao'])['pld'].mean().reset_index()
    pld_por_simulacao.columns = ['ano', 'mes', 'simulacao', 'pld_medio']
    
    print(f"\n     PLD Médio (das simulações): R$ {pld_por_simulacao['pld_medio'].mean():.2f}/MWh")
    print(f"     PLD Mediana (das simulações): R$ {pld_por_simulacao['pld_medio'].median():.2f}/MWh")
    print(f"     PLD Min/Max (das simulações): R$ {pld_por_simulacao['pld_medio'].min():.2f} / R$ {pld_por_simulacao['pld_medio'].max():.2f}/MWh")
    
    # Criar figura com boxplots
    fig, ax = plt.subplots(1, 1, figsize=(16, 8))
    fig.suptitle(f'Análise de PLD por Mês - {ano} (Boxplot das Médias por Simulação)', 
                 fontsize=16, fontweight='bold')
    
    # Preparar dados para boxplot
    dados_boxplot = [pld_por_simulacao[pld_por_simulacao['mes'] == mes]['pld_medio'].values 
                     for mes in range(1, 13)]
    
    # Criar boxplot
    bp = ax.boxplot(dados_boxplot, positions=range(1, 13), widths=0.6, patch_artist=True,
                    showfliers=True, notch=False,
                    boxprops=dict(facecolor='seagreen', alpha=0.7, edgecolor='black', linewidth=1.5),
                    whiskerprops=dict(color='black', linewidth=1.5),
                    capprops=dict(color='black', linewidth=1.5),
                    medianprops=dict(color='darkred', linewidth=2.5),
                    flierprops=dict(marker='o', markerfacecolor='red', markersize=4, alpha=0.5))
    
    # Adicionar linha de média geral
    medias = [pld_por_simulacao[pld_por_simulacao['mes'] == mes]['pld_medio'].mean() 
              for mes in range(1, 13)]
    ax.plot(range(1, 13), medias, 'D-', color='blue', linewidth=2, markersize=8, 
            label='Média', alpha=0.8, zorder=10)
    
    ax.set_title('Distribuição do PLD Médio por Simulação - cada mês', fontweight='bold', fontsize=12)
    ax.set_xlabel('Mês', fontsize=11)
    ax.set_ylabel('R$/MWh', fontsize=11)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'])
    
    plt.tight_layout()
    output_path = pld_dir / f'pld_{ano}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"     [OK] Salvo: pld/{output_path.name}")
    plt.close()


def gerar_boxplots_comparativos(df, output_dir):
    """Gera boxplots comparativos entre anos para cada dimensão (x=mês, hue=ano) - usando médias por simulação."""
    
    print("\n" + "="*80)
    print("  BOXPLOTS COMPARATIVOS (mês vs anos) - 1 por página - Usando Médias por Simulação")
    print("="*80)
    
    # Criar diretório para boxplots
    boxplot_dir = output_dir / 'boxplots'
    boxplot_dir.mkdir(parents=True, exist_ok=True)
    
    # NOVO: Calcular médias por simulação para cada variável
    # Agregar por (ano, mes, simulacao)
    variaveis_media = {
        'val_gereolica': 'eolica_media',
        'val_gersolar': 'solar_media',
        'val_carga': 'carga_media',
        'val_term_despacho': 'termica_media',
        'curtailment': 'curtailment_media',
        'pld': 'pld_media'
    }
    
    # Calcular médias por simulação
    df_medias = df.groupby(['ano', 'mes', 'simulacao']).agg({
        'val_gereolica': 'mean',
        'val_gersolar': 'mean',
        'val_carga': 'mean',
        'val_term_despacho': 'mean',
        'curtailment': 'mean',
        'pld': 'mean'
    }).reset_index()
    
    # Renomear colunas
    df_medias.rename(columns=variaveis_media, inplace=True)
    
    # Converter tipos para compatibilidade com seaborn
    df_medias['ano'] = df_medias['ano'].astype(str)
    df_medias['mes'] = df_medias['mes'].astype(int)
    
    print(f"\n  Total de simulações agregadas: {len(df_medias):,}")
    
    # 1. Geração Eólica
    fig, ax = plt.subplots(1, 1, figsize=(18, 8))
    sns.boxplot(data=df_medias, x='mes', y='eolica_media', hue='ano', ax=ax, palette='Set2')
    ax.set_title('Geração Eólica por Mês e Ano (Média por Simulação)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Mês', fontsize=13)
    ax.set_ylabel('MW', fontsize=13)
    ax.legend(title='Ano', fontsize=10, title_fontsize=11, loc='upper right', ncol=3)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    output_path = boxplot_dir / 'boxplot_eolica_mes_ano.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  [OK] boxplots/boxplot_eolica_mes_ano.png")
    plt.close()
    
    # 2. Geração Solar
    fig, ax = plt.subplots(1, 1, figsize=(18, 8))
    sns.boxplot(data=df_medias, x='mes', y='solar_media', hue='ano', ax=ax, palette='YlOrRd')
    ax.set_title('Geração Solar por Mês e Ano (Média por Simulação)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Mês', fontsize=13)
    ax.set_ylabel('MW', fontsize=13)
    ax.legend(title='Ano', fontsize=10, title_fontsize=11, loc='upper right', ncol=3)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    output_path = boxplot_dir / 'boxplot_solar_mes_ano.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  [OK] boxplots/boxplot_solar_mes_ano.png")
    plt.close()
    
    # 3. Carga
    fig, ax = plt.subplots(1, 1, figsize=(18, 8))
    sns.boxplot(data=df_medias, x='mes', y='carga_media', hue='ano', ax=ax, palette='Greens')
    ax.set_title('Carga por Mês e Ano (Média por Simulação)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Mês', fontsize=13)
    ax.set_ylabel('MW', fontsize=13)
    ax.legend(title='Ano', fontsize=10, title_fontsize=11, loc='upper right', ncol=3)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    output_path = boxplot_dir / 'boxplot_carga_mes_ano.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  [OK] boxplots/boxplot_carga_mes_ano.png")
    plt.close()
    
    # 4. Despacho Térmico
    fig, ax = plt.subplots(1, 1, figsize=(18, 8))
    sns.boxplot(data=df_medias, x='mes', y='termica_media', hue='ano', ax=ax, palette='Reds')
    ax.set_title('Despacho Térmico por Mês e Ano (Média por Simulação)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Mês', fontsize=13)
    ax.set_ylabel('MW', fontsize=13)
    ax.legend(title='Ano', fontsize=10, title_fontsize=11, loc='upper right', ncol=3)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    output_path = boxplot_dir / 'boxplot_termica_mes_ano.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  [OK] boxplots/boxplot_termica_mes_ano.png")
    plt.close()
    
    # 5. Curtailment
    fig, ax = plt.subplots(1, 1, figsize=(18, 8))
    # Para curtailment, considerar todas as médias (incluindo zeros)
    sns.boxplot(data=df_medias, x='mes', y='curtailment_media', hue='ano', ax=ax, palette='OrRd')
    ax.set_title('Curtailment por Mês e Ano (Média por Simulação)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Mês', fontsize=13)
    ax.set_ylabel('MW', fontsize=13)
    ax.legend(title='Ano', fontsize=10, title_fontsize=11, loc='upper right', ncol=3)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    output_path = boxplot_dir / 'boxplot_curtailment_mes_ano.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  [OK] boxplots/boxplot_curtailment_mes_ano.png")
    plt.close()
    
    # 6. PLD
    fig, ax = plt.subplots(1, 1, figsize=(18, 8))
    sns.boxplot(data=df_medias, x='mes', y='pld_media', hue='ano', ax=ax, palette='viridis')
    ax.set_title('PLD por Mês e Ano (Média por Simulação)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Mês', fontsize=13)
    ax.set_ylabel('R$/MWh', fontsize=13)
    ax.legend(title='Ano', fontsize=10, title_fontsize=11, loc='upper right', ncol=3)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    output_path = boxplot_dir / 'boxplot_pld_mes_ano.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  [OK] boxplots/boxplot_pld_mes_ano.png")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Análise de resultados das simulações')
    parser.add_argument('--arquivo', type=str, help='Caminho para arquivo de resultados')
    parser.add_argument('--ultimo', action='store_true', help='Usar arquivo mais recente')
    
    args = parser.parse_args()
    
    # Determinar arquivo
    if args.arquivo:
        arquivo_path = Path(args.arquivo)
    else:
        arquivo_path = None
    
    # Carregar dados
    df = carregar_resultados(arquivo_path)
    
    # Identificar anos únicos
    anos = sorted(df['ano'].unique())
    print(f"\nAnos encontrados: {anos}")
    
    # Criar diretório de análise
    analise_dir = OUTPUT_DIR / 'analises'
    analise_dir.mkdir(parents=True, exist_ok=True)
    
    # Executar análises por ano
    for ano in anos:
        print("\n" + "="*80)
        print(f"  ANÁLISE: {ano}")
        print("="*80)
        
        analisar_perfis_horarios(df, analise_dir, ano)
        analisar_curtailment(df, analise_dir, ano)
        analisar_scatter_carga_curtailment(df, analise_dir, ano)
        analisar_carga_liquida(df, analise_dir, ano)
        analisar_pld(df, analise_dir, ano)
    
    gerar_graficos_curtailment_multiano(df, analise_dir)

    # Gerar boxplots comparativos entre anos
    gerar_boxplots_comparativos(df, analise_dir)
    
    print("\n" + "="*80)
    print(f"  Análise Concluída!")
    print("="*80)
    print(f"\nResultados salvos em: {analise_dir}")
    print(f"\nArquivos gerados:")
    print(f"\n  [Perfis Horários] - perfil_horario/")
    print(f"    - {len(anos) * 12} gráficos (12 meses × {len(anos)} anos)")
    print(f"\n  [Curtailment] - curtailment/")
    print(f"    - {len(anos)} gráficos de análise (1 por ano)")
    print(f"    - {len(anos)} scatter plots Carga vs Curtailment (1 por ano)")
    print(f"\n  [Carga Líquida] - carga_liquida/")
    print(f"    - {len(anos) * 13} gráficos (12 perfis horários + 1 resumo mensal por ano)")
    print(f"\n  [PLD] - pld/")
    print(f"    - {len(anos)} gráficos (1 por ano)")
    print(f"\n  [Boxplots Comparativos] - boxplots/")
    print(f"    - 6 gráficos (eólica, solar, carga, térmica, curtailment, PLD)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

