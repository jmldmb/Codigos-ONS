"""
Análise Profunda do Modelo de Carga V4
=======================================

Investiga em detalhe por que o modelo subestima sistematicamente
a carga no meio do dia, apesar de haver padrões visuais claros.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuração visual
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (18, 12)
plt.rcParams['font.size'] = 10

CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "analise_profunda_carga"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def carregar_dados():
    """Carrega base completa."""
    print("\n[1/1] Carregando dados completos...")
    
    csv_path = CARGA_LIQ_DIR / "Output" / "analise_completa" / "comparacao_completa.csv"
    df = pd.read_csv(csv_path)
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    
    # Adicionar features temporais
    df['hora'] = df['din_instante'].dt.hour
    df['dia_semana'] = df['din_instante'].dt.dayofweek
    df['mes'] = df['din_instante'].dt.month
    df['ano'] = df['din_instante'].dt.year
    df['dia_nome'] = df['din_instante'].dt.day_name()
    df['eh_fds'] = df['dia_semana'].isin([5, 6])
    df['trimestre'] = df['din_instante'].dt.quarter
    
    # Renomear colunas
    rename_map = {}
    if 'carga_real' in df.columns:
        rename_map['carga_real'] = 'carga_bruta_real'
    if 'carga_sim' in df.columns:
        rename_map['carga_sim'] = 'carga_bruta_sim'
    if 'carga_liquida_historica' in df.columns:
        rename_map['carga_liquida_historica'] = 'carga_liq_real'
    if 'carga_liquida' in df.columns:
        rename_map['carga_liquida'] = 'carga_liq_sim'
    
    df = df.rename(columns=rename_map)
    
    # Calcular erros
    df['erro_carga_bruta'] = df['carga_bruta_sim'] - df['carga_bruta_real']
    df['erro_carga_bruta_pct'] = (df['erro_carga_bruta'] / df['carga_bruta_real']) * 100
    
    print(f"     Registros: {len(df):,}")
    print(f"     Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    
    return df

def analise_1_perfil_horario_medio(df):
    """Análise 1: Perfil horário médio - Real vs Simulado."""
    
    print("\n" + "="*100)
    print("  ANÁLISE 1: PERFIL HORÁRIO MÉDIO")
    print("="*100)
    
    # Perfil médio por hora
    perfil = df.groupby('hora').agg({
        'carga_bruta_real': ['mean', 'std', 'min', 'max'],
        'carga_bruta_sim': ['mean', 'std', 'min', 'max'],
        'erro_carga_bruta': ['mean', 'std'],
        'erro_carga_bruta_pct': ['mean', 'std']
    }).round(0)
    
    print("\nPerfil Horário - Estatísticas:")
    print(f"\n{'Hora':>4} | {'Real Média':>12} | {'Sim Média':>12} | {'Erro (MW)':>12} | {'Erro (%)':>10} | {'Std Erro':>12}")
    print("-" * 85)
    
    for hora in range(24):
        real_mean = perfil.loc[hora, ('carga_bruta_real', 'mean')]
        sim_mean = perfil.loc[hora, ('carga_bruta_sim', 'mean')]
        erro_mean = perfil.loc[hora, ('erro_carga_bruta', 'mean')]
        erro_pct = perfil.loc[hora, ('erro_carga_bruta_pct', 'mean')]
        erro_std = perfil.loc[hora, ('erro_carga_bruta', 'std')]
        
        print(f"{hora:4d} | {real_mean:12,.0f} | {sim_mean:12,.0f} | {erro_mean:+12,.0f} | {erro_pct:+9.2f}% | {erro_std:12,.0f}")
    
    # Gráfico
    fig, axes = plt.subplots(3, 1, figsize=(18, 14))
    
    horas = range(24)
    real_mean = [perfil.loc[h, ('carga_bruta_real', 'mean')] for h in horas]
    sim_mean = [perfil.loc[h, ('carga_bruta_sim', 'mean')] for h in horas]
    erro_mean = [perfil.loc[h, ('erro_carga_bruta', 'mean')] for h in horas]
    erro_std = [perfil.loc[h, ('erro_carga_bruta', 'std')] for h in horas]
    erro_pct = [perfil.loc[h, ('erro_carga_bruta_pct', 'mean')] for h in horas]
    
    # Subplot 1: Perfil Real vs Simulado
    ax = axes[0]
    ax.plot(horas, real_mean, 'o-', linewidth=3, markersize=8, label='Real', color='darkblue')
    ax.plot(horas, sim_mean, 's--', linewidth=3, markersize=8, label='Simulado V4', color='orange')
    ax.fill_between(horas, real_mean, sim_mean, alpha=0.3, color='red')
    ax.set_ylabel('Carga Bruta (MW)', fontsize=13, fontweight='bold')
    ax.set_title('Perfil Horário Médio: Real vs Simulado V4', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # Subplot 2: Erro Absoluto
    ax = axes[1]
    bars = ax.bar(horas, erro_mean, color=['red' if e < -1000 else 'lightcoral' if e < 0 else 'lightgreen' if e < 1000 else 'green' for e in erro_mean],
                   alpha=0.8, edgecolor='black', linewidth=1.5)
    ax.errorbar(horas, erro_mean, yerr=erro_std, fmt='none', ecolor='black', capsize=4, alpha=0.5, linewidth=1.5)
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_ylabel('Erro (Sim - Real) [MW]', fontsize=13, fontweight='bold')
    ax.set_title('Erro Médio por Hora (±1 Desvio Padrão)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    # Subplot 3: Erro Percentual
    ax = axes[2]
    ax.plot(horas, erro_pct, 'o-', linewidth=3, markersize=8, color='purple')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.axhline(-5, color='red', linestyle=':', linewidth=1, alpha=0.5, label='±5%')
    ax.axhline(5, color='red', linestyle=':', linewidth=1, alpha=0.5)
    ax.fill_between(horas, -5, 5, alpha=0.1, color='green')
    ax.set_xlabel('Hora do Dia', fontsize=13, fontweight='bold')
    ax.set_ylabel('Erro Percentual (%)', fontsize=13, fontweight='bold')
    ax.set_title('Erro Percentual por Hora', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_1_perfil_horario.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n[OK] Gráfico salvo: analise_1_perfil_horario.png")

def analise_2_heatmap_erro_detalhado(df):
    """Análise 2: Heatmap erro por hora e mês."""
    
    print("\n" + "="*100)
    print("  ANÁLISE 2: HEATMAP ERRO HORA × MÊS")
    print("="*100)
    
    # Pivot: hora x mês
    pivot_abs = df.pivot_table(values='erro_carga_bruta', index='hora', columns='mes', aggfunc='mean')
    pivot_pct = df.pivot_table(values='erro_carga_bruta_pct', index='hora', columns='mes', aggfunc='mean')
    
    fig, axes = plt.subplots(2, 1, figsize=(16, 14))
    
    # Erro absoluto
    ax = axes[0]
    sns.heatmap(pivot_abs, annot=True, fmt='.0f', cmap='RdBu_r', center=0,
                cbar_kws={'label': 'Erro (MW)'}, ax=ax, linewidths=0.5)
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
    ax.set_title('Erro Médio (MW) por Hora e Mês', fontsize=14, fontweight='bold')
    
    # Erro percentual
    ax = axes[1]
    sns.heatmap(pivot_pct, annot=True, fmt='.1f', cmap='RdBu_r', center=0,
                cbar_kws={'label': 'Erro (%)'}, ax=ax, linewidths=0.5)
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
    ax.set_title('Erro Percentual (%) por Hora e Mês', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_2_heatmap_hora_mes.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n[OK] Gráfico salvo: analise_2_heatmap_hora_mes.png")
    
    # Identificar pior combinação hora-mês
    idx_min = pivot_abs.stack().idxmin()
    idx_max = pivot_abs.stack().idxmax()
    
    print(f"\nPIOR subestimacao: Hora {idx_min[0]}h, Mes {idx_min[1]} = {pivot_abs.loc[idx_min[0], idx_min[1]]:.0f} MW")
    print(f"PIOR superestimacao: Hora {idx_max[0]}h, Mes {idx_max[1]} = {pivot_abs.loc[idx_max[0], idx_max[1]]:.0f} MW")

def analise_3_fator_escala_vs_perfil(df):
    """Análise 3: Será que é problema de escala ou de perfil?"""
    
    print("\n" + "="*100)
    print("  ANÁLISE 3: FATOR DE ESCALA vs PERFIL")
    print("="*100)
    
    # Para cada hora, calcular fator de escala médio (sim/real)
    df_hora = df.groupby('hora').agg({
        'carga_bruta_real': 'mean',
        'carga_bruta_sim': 'mean'
    })
    
    df_hora['fator_escala'] = df_hora['carga_bruta_sim'] / df_hora['carga_bruta_real']
    df_hora['desvio_escala_pct'] = (df_hora['fator_escala'] - 1) * 100
    
    print("\nFator de Escala por Hora:")
    print(f"\n{'Hora':>4} | {'Fator':>8} | {'Desvio (%)':>12}")
    print("-" * 30)
    for hora in range(24):
        fator = df_hora.loc[hora, 'fator_escala']
        desvio = df_hora.loc[hora, 'desvio_escala_pct']
        print(f"{hora:4d} | {fator:8.4f} | {desvio:+11.2f}%")
    
    # Testar: se reescalarmos uniformemente, qual seria o erro?
    fator_global = df['carga_bruta_sim'].sum() / df['carga_bruta_real'].sum()
    df['carga_bruta_sim_reescalada'] = df['carga_bruta_sim'] / fator_global
    df['erro_reescalado'] = df['carga_bruta_sim_reescalada'] - df['carga_bruta_real']
    
    mae_original = df['erro_carga_bruta'].abs().mean()
    mae_reescalado = df['erro_reescalado'].abs().mean()
    
    print(f"\n{'Modelo':>20} | {'MAE (MW)':>12} | {'Melhoria':>12}")
    print("-" * 50)
    print(f"{'Original V4':>20} | {mae_original:12,.0f} |")
    print(f"{'V4 Reescalado':>20} | {mae_reescalado:12,.0f} | {(1 - mae_reescalado/mae_original)*100:+10.1f}%")
    
    # Gráfico
    fig, axes = plt.subplots(2, 1, figsize=(18, 10))
    
    horas = range(24)
    
    # Subplot 1: Fator de escala
    ax = axes[0]
    ax.plot(horas, df_hora['fator_escala'].values, 'o-', linewidth=3, markersize=8, color='purple')
    ax.axhline(1.0, color='green', linestyle='--', linewidth=2, label='Fator Ideal = 1.0')
    ax.axhline(fator_global, color='red', linestyle=':', linewidth=2, label=f'Fator Global = {fator_global:.4f}')
    ax.fill_between(horas, 0.95, 1.05, alpha=0.1, color='green', label='±5%')
    ax.set_ylabel('Fator de Escala (Sim/Real)', fontsize=13, fontweight='bold')
    ax.set_title('Fator de Escala por Hora (Simidentifica Viés de Perfil)', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # Subplot 2: Comparação erro original vs reescalado
    ax = axes[1]
    erro_original_hora = df.groupby('hora')['erro_carga_bruta'].mean()
    erro_reescalado_hora = df.groupby('hora')['erro_reescalado'].mean()
    
    x = np.arange(24)
    width = 0.35
    ax.bar(x - width/2, erro_original_hora.values, width, label='Original V4', alpha=0.8, color='orange', edgecolor='black')
    ax.bar(x + width/2, erro_reescalado_hora.values, width, label='V4 Reescalado', alpha=0.8, color='lightblue', edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_xlabel('Hora do Dia', fontsize=13, fontweight='bold')
    ax.set_ylabel('Erro Médio (MW)', fontsize=13, fontweight='bold')
    ax.set_title('Erro Original vs Reescalado', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_3_fator_escala.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n[OK] Gráfico salvo: analise_3_fator_escala.png")

def analise_4_modelo_deterministico_benchmark(df):
    """Análise 4: Comparar com modelo determinístico simples."""
    
    print("\n" + "="*100)
    print("  ANÁLISE 4: BENCHMARK - MODELO DETERMINÍSTICO")
    print("="*100)
    
    # Modelo Determinístico: Perfil horário médio histórico
    perfil_historico = df.groupby(['hora', 'mes', 'dia_semana']).agg({
        'carga_bruta_real': 'mean'
    }).reset_index()
    perfil_historico.columns = ['hora', 'mes', 'dia_semana', 'perfil_medio']
    
    # Join com dados
    df_test = df.merge(perfil_historico, on=['hora', 'mes', 'dia_semana'], how='left')
    
    # Modelo Determinístico Simples: usar perfil médio
    df_test['carga_det_simples'] = df_test['perfil_medio']
    df_test['erro_det_simples'] = df_test['carga_det_simples'] - df_test['carga_bruta_real']
    
    # Modelo Determinístico Melhorado: Perfil + ajuste por média mensal
    df_test['media_mensal_real'] = df_test.groupby(['ano', 'mes'])['carga_bruta_real'].transform('mean')
    df_test['media_mensal_perfil'] = df_test.groupby(['ano', 'mes'])['perfil_medio'].transform('mean')
    df_test['fator_ajuste_mensal'] = df_test['media_mensal_real'] / df_test['media_mensal_perfil']
    df_test['carga_det_melhorado'] = df_test['perfil_medio'] * df_test['fator_ajuste_mensal']
    df_test['erro_det_melhorado'] = df_test['carga_det_melhorado'] - df_test['carga_bruta_real']
    
    # Comparar métricas
    mae_v4 = df_test['erro_carga_bruta'].abs().mean()
    rmse_v4 = np.sqrt((df_test['erro_carga_bruta']**2).mean())
    
    mae_det_simples = df_test['erro_det_simples'].abs().mean()
    rmse_det_simples = np.sqrt((df_test['erro_det_simples']**2).mean())
    
    mae_det_melhorado = df_test['erro_det_melhorado'].abs().mean()
    rmse_det_melhorado = np.sqrt((df_test['erro_det_melhorado']**2).mean())
    
    print(f"\n{'Modelo':>30} | {'MAE (MW)':>12} | {'RMSE (MW)':>12} | {'vs V4':>12}")
    print("-" * 75)
    print(f"{'Modelo V4 (Estocástico)':>30} | {mae_v4:12,.0f} | {rmse_v4:12,.0f} |")
    print(f"{'Determinístico Simples':>30} | {mae_det_simples:12,.0f} | {rmse_det_simples:12,.0f} | {(mae_det_simples/mae_v4-1)*100:+10.1f}%")
    print(f"{'Determinístico Melhorado':>30} | {mae_det_melhorado:12,.0f} | {rmse_det_melhorado:12,.0f} | {(mae_det_melhorado/mae_v4-1)*100:+10.1f}%")
    
    # Gráfico comparativo
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    
    # Subplot 1: Erro por hora - V4
    ax = axes[0, 0]
    erro_v4_hora = df_test.groupby('hora')['erro_carga_bruta'].mean()
    ax.bar(range(24), erro_v4_hora.values, alpha=0.8, color='orange', edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_ylabel('Erro (MW)', fontsize=11, fontweight='bold')
    ax.set_title(f'Modelo V4 (Estocástico)\nMAE = {mae_v4:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    # Subplot 2: Erro por hora - Det Simples
    ax = axes[0, 1]
    erro_det_s_hora = df_test.groupby('hora')['erro_det_simples'].mean()
    ax.bar(range(24), erro_det_s_hora.values, alpha=0.8, color='lightblue', edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_ylabel('Erro (MW)', fontsize=11, fontweight='bold')
    ax.set_title(f'Determinístico Simples\nMAE = {mae_det_simples:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    # Subplot 3: Erro por hora - Det Melhorado
    ax = axes[1, 0]
    erro_det_m_hora = df_test.groupby('hora')['erro_det_melhorado'].mean()
    ax.bar(range(24), erro_det_m_hora.values, alpha=0.8, color='lightgreen', edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
    ax.set_ylabel('Erro (MW)', fontsize=11, fontweight='bold')
    ax.set_title(f'Determinístico Melhorado\nMAE = {mae_det_melhorado:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    # Subplot 4: Comparação MAE por hora
    ax = axes[1, 1]
    x = np.arange(24)
    width = 0.25
    ax.bar(x - width, df_test.groupby('hora')['erro_carga_bruta'].apply(lambda x: x.abs().mean()), 
           width, label='V4', alpha=0.8, color='orange', edgecolor='black')
    ax.bar(x, df_test.groupby('hora')['erro_det_simples'].apply(lambda x: x.abs().mean()), 
           width, label='Det Simples', alpha=0.8, color='lightblue', edgecolor='black')
    ax.bar(x + width, df_test.groupby('hora')['erro_det_melhorado'].apply(lambda x: x.abs().mean()), 
           width, label='Det Melhorado', alpha=0.8, color='lightgreen', edgecolor='black')
    ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
    ax.set_ylabel('MAE (MW)', fontsize=11, fontweight='bold')
    ax.set_title('Comparação: MAE por Hora', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_4_benchmark_deterministico.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n[OK] Gráfico salvo: analise_4_benchmark_deterministico.png")
    
    return df_test

def analise_5_diagnostico_raiz_do_problema(df):
    """Análise 5: Diagnóstico - onde está o problema?"""
    
    print("\n" + "="*100)
    print("  ANÁLISE 5: DIAGNÓSTICO - RAIZ DO PROBLEMA")
    print("="*100)
    
    # Hipóteses a testar:
    # H1: Problema está na média diária (Stage 1)?
    # H2: Problema está no perfil horário (Stage 2)?
    # H3: Problema está na variabilidade (AR)?
    
    # Para cada dia, comparar média diária
    df['data'] = df['din_instante'].dt.date
    df_dia = df.groupby('data').agg({
        'carga_bruta_real': 'mean',
        'carga_bruta_sim': 'mean'
    }).reset_index()
    
    df_dia['erro_medio_diario'] = df_dia['carga_bruta_sim'] - df_dia['carga_bruta_real']
    df_dia['erro_medio_diario_pct'] = (df_dia['erro_medio_diario'] / df_dia['carga_bruta_real']) * 100
    
    mae_dia = df_dia['erro_medio_diario'].abs().mean()
    
    print(f"\nH1: Erro na Média Diária (Stage 1):")
    print(f"    MAE médio diário: {mae_dia:,.0f} MW ({(mae_dia/df_dia['carga_bruta_real'].mean())*100:.2f}%)")
    
    # H2: Desvio do perfil horário (intra-dia)
    df['media_dia'] = df.groupby('data')['carga_bruta_real'].transform('mean')
    df['desvio_perfil_real'] = df['carga_bruta_real'] - df['media_dia']
    
    df['media_dia_sim'] = df.groupby('data')['carga_bruta_sim'].transform('mean')
    df['desvio_perfil_sim'] = df['carga_bruta_sim'] - df['media_dia_sim']
    
    df['erro_perfil'] = df['desvio_perfil_sim'] - df['desvio_perfil_real']
    
    mae_perfil = df['erro_perfil'].abs().mean()
    
    print(f"\nH2: Erro no Perfil Horário (Stage 2):")
    print(f"    MAE desvio de perfil: {mae_perfil:,.0f} MW")
    
    # Decomposição do erro total
    mae_total = df['erro_carga_bruta'].abs().mean()
    
    # Aproximação: Erro total ≈ Erro médio diário + Erro perfil
    print(f"\nDecomposição do Erro:")
    print(f"    Erro Total (MAE):        {mae_total:12,.0f} MW (100.0%)")
    print(f"    Erro Médio Diário:       {mae_dia:12,.0f} MW ({(mae_dia/mae_total)*100:5.1f}%)")
    print(f"    Erro Perfil Intra-Dia:   {mae_perfil:12,.0f} MW ({(mae_perfil/mae_total)*100:5.1f}%)")
    
    # Gráfico de diagnóstico
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    
    # Subplot 1: Scatter média diária
    ax = axes[0, 0]
    ax.scatter(df_dia['carga_bruta_real'], df_dia['carga_bruta_sim'], alpha=0.3, s=10)
    lims = [df_dia['carga_bruta_real'].min(), df_dia['carga_bruta_real'].max()]
    ax.plot(lims, lims, 'r--', linewidth=2, label='Ideal')
    ax.set_xlabel('Média Diária Real (MW)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Média Diária Simulada (MW)', fontsize=11, fontweight='bold')
    ax.set_title('Stage 1: Média Diária', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Subplot 2: Distribuição erro médio diário
    ax = axes[0, 1]
    ax.hist(df_dia['erro_medio_diario_pct'], bins=50, alpha=0.7, edgecolor='black')
    ax.axvline(0, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('Erro Média Diária (%)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequência', fontsize=11, fontweight='bold')
    ax.set_title(f'Distribuição Erro Stage 1\nMAE = {mae_dia:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Subplot 3: Erro perfil por hora
    ax = axes[1, 0]
    erro_perfil_hora = df.groupby('hora')['erro_perfil'].agg(['mean', 'std'])
    ax.bar(range(24), erro_perfil_hora['mean'].values, alpha=0.8, color='purple', edgecolor='black')
    ax.errorbar(range(24), erro_perfil_hora['mean'].values, yerr=erro_perfil_hora['std'].values,
                fmt='none', ecolor='black', capsize=3, alpha=0.5)
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
    ax.set_ylabel('Erro Desvio de Perfil (MW)', fontsize=11, fontweight='bold')
    ax.set_title(f'Stage 2: Erro no Perfil Horário\nMAE = {mae_perfil:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    # Subplot 4: Contribuição relativa
    ax = axes[1, 1]
    contribuicoes = ['Erro\nMédio\nDiário', 'Erro\nPerfil\nIntra-Dia']
    valores = [mae_dia, mae_perfil]
    cores = ['orange', 'purple']
    bars = ax.bar(contribuicoes, valores, color=cores, alpha=0.8, edgecolor='black', linewidth=2)
    ax.set_ylabel('MAE (MW)', fontsize=11, fontweight='bold')
    ax.set_title('Decomposição do Erro Total', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars, valores):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:,.0f} MW\n({(val/mae_total)*100:.1f}%)',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_5_diagnostico_raiz.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n[OK] Gráfico salvo: analise_5_diagnostico_raiz.png")

def main():
    """Executa análise profunda completa."""
    
    print("\n" + "="*100)
    print("  ANÁLISE PROFUNDA - MODELO DE CARGA V4")
    print("  Por que o modelo subestima no meio do dia?")
    print("="*100)
    
    df = carregar_dados()
    
    analise_1_perfil_horario_medio(df)
    analise_2_heatmap_erro_detalhado(df)
    analise_3_fator_escala_vs_perfil(df)
    df_test = analise_4_modelo_deterministico_benchmark(df)
    analise_5_diagnostico_raiz_do_problema(df)
    
    print("\n" + "="*100)
    print("  ANÁLISE CONCLUÍDA!")
    print("="*100)
    print(f"\nResultados salvos em: {OUTPUT_DIR}")
    print("\nArquivos gerados:")
    print("  1. analise_1_perfil_horario.png")
    print("  2. analise_2_heatmap_hora_mes.png")
    print("  3. analise_3_fator_escala.png")
    print("  4. analise_4_benchmark_deterministico.png")
    print("  5. analise_5_diagnostico_raiz.png")
    
    print("\n" + "="*100)

if __name__ == "__main__":
    main()

