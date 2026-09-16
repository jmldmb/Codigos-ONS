"""
Backtest Simplificado - Geração Solar Centralizada e Distribuída
================================================================

Valida os perfis horários de solar testando se:
1. O perfil total (centralizada + distribuída) captura bem o comportamento real
2. Os perfis individuais têm características esperadas (picos em horários diferentes)
3. Gera séries sintéticas para análise

Usa dados disponíveis:
- BALANCO_ENERGIA para total real
- Samplers de centralizada e distribuída para gerar perfis
- Valores de data.py para MWmédios

Autor: ONS
Data: Novembro 2024
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import calendar
from solar_sampler import SolarSampler
from solar_distribuida_sampler import SolarDistribuidaSampler

# Configurar estilo dos gráficos
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Adicionar caminho para acessar data.py
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mini_dessem.data import (
    geracao_solar_centralizada_dic,
    geracao_solar_distribuida_dic,
    capacidade_solar_total_dic
)

# Definir diretórios
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "sample"

# Diretórios de output por tipo
BACKTEST_SOLAR_DIR = OUTPUT_DIR / "solar" / "backtest"
BACKTEST_DIST_DIR = OUTPUT_DIR / "solar_distribuida" / "backtest"
BACKTEST_COMPARACAO_DIR = OUTPUT_DIR / "solar_comparacao" / "backtest"

# Criar diretórios
BACKTEST_SOLAR_DIR.mkdir(parents=True, exist_ok=True)
BACKTEST_DIST_DIR.mkdir(parents=True, exist_ok=True)
BACKTEST_COMPARACAO_DIR.mkdir(parents=True, exist_ok=True)

# Caminhos de dados
DATA_BALANCO = BASE_DIR / "Data" / "raw_data"


def carregar_dados_reais():
    """
    Carrega dados reais de geração solar total do BALANCO_ENERGIA
    
    Returns:
        DataFrame com colunas: ano, mes, hora, total_real_mw
    """
    print("\n[1/7] Carregando dados históricos...")
    
    dados_consolidados = []
    
    # Carregar dados de 2024-04 a 2025-10 (período com dados)
    for ano in [2024, 2025]:
        arquivo = DATA_BALANCO / f"BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx"
        
        if not arquivo.exists():
            continue
        
        try:
            print(f"  Carregando {ano}...")
            df = pd.read_excel(arquivo, sheet_name=0)
            
            # Filtrar SIN
            id_col = None
            for cand in ['id_subsistema', 'id_subsistena', 'nom_subsistema']:
                if cand in df.columns:
                    id_col = cand
                    break
            
            if id_col is not None:
                df[id_col] = df[id_col].astype(str).str.upper().str.strip()
                df = df[df[id_col] == 'SIN'].copy()
            
            # Processar datas
            df['din_instante'] = pd.to_datetime(df['din_instante'], errors='coerce')
            df = df.dropna(subset=['din_instante'])
            df['ano'] = df['din_instante'].dt.year
            df['mes'] = df['din_instante'].dt.month
            df['hora'] = df['din_instante'].dt.hour
            
            # Converter para numérico
            df['val_gersolar'] = pd.to_numeric(df['val_gersolar'], errors='coerce')
            
            # Calcular média por mês e hora
            media_mes_hora = df.groupby(['ano', 'mes', 'hora'])['val_gersolar'].mean().reset_index()
            media_mes_hora.columns = ['ano', 'mes', 'hora', 'total_real_mw']
            
            dados_consolidados.append(media_mes_hora)
            print(f"    ✓ {ano}: {len(media_mes_hora)} registros")
            
        except Exception as e:
            print(f"  ⚠ Erro ao processar {ano}: {e}")
            continue
    
    df_real = pd.concat(dados_consolidados, ignore_index=True) if dados_consolidados else pd.DataFrame()
    
    if len(df_real) > 0:
        n_meses = df_real.groupby(['ano', 'mes']).ngroups
        print(f"\n  ✓ Total: {len(df_real)} registros horários")
        print(f"  ✓ {n_meses} meses disponíveis")
    
    return df_real


def calcular_metricas(real: np.ndarray, previsto: np.ndarray) -> dict:
    """
    Calcula métricas de erro entre perfis horários
    """
    # MAE e RMSE
    mae = np.mean(np.abs(real - previsto))
    rmse = np.sqrt(np.mean((real - previsto) ** 2))
    
    # MAPE apenas nas horas com geração significativa (> 100 MW)
    mask = real > 100
    
    if mask.sum() > 0:
        mape = np.mean(np.abs((real[mask] - previsto[mask]) / real[mask])) * 100
    else:
        mape = np.nan
    
    # R²
    ss_res = np.sum((real - previsto) ** 2)
    ss_tot = np.sum((real - np.mean(real)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    
    # Correlação
    if np.std(real) > 0 and np.std(previsto) > 0:
        correlacao = np.corrcoef(real, previsto)[0, 1]
    else:
        correlacao = np.nan
    
    # Bias
    bias = np.mean(previsto - real)
    bias_pct = (bias / np.mean(real)) * 100 if np.mean(real) > 0 else np.nan
    
    # Hora de pico
    hora_pico_real = np.argmax(real)
    hora_pico_prev = np.argmax(previsto)
    erro_hora_pico = abs(hora_pico_real - hora_pico_prev)
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
        'correlacao': correlacao,
        'bias': bias,
        'bias_pct': bias_pct,
        'hora_pico_real': hora_pico_real,
        'hora_pico_prev': hora_pico_prev,
        'erro_hora_pico': erro_hora_pico
    }


def gerar_series_sinteticas(sampler_cent, sampler_dist, ano, mes, n_dias=30):
    """
    Gera série sintética de múltiplos dias
    """
    # Buscar MWmédios dos dicionários
    mw_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
    mw_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
    
    if mw_cent == 0 or mw_dist == 0:
        return None
    
    dados = []
    
    for dia in range(1, n_dias + 1):
        # Gerar perfis
        perfil_cent = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        
        for hora in range(24):
            dados.append({
                'ano': ano,
                'mes': mes,
                'dia': dia,
                'hora': hora,
                'geracao_centralizada_mw': perfil_cent[hora],
                'geracao_distribuida_mw': perfil_dist[hora],
                'geracao_total_mw': perfil_cent[hora] + perfil_dist[hora]
            })
    
    return pd.DataFrame(dados)


def realizar_backtest():
    """
    Realiza backtest completo
    """
    print("="*80)
    print("BACKTEST SOLAR - CENTRALIZADA E DISTRIBUÍDA")
    print("="*80)
    
    # Carregar dados reais
    df_real = carregar_dados_reais()
    
    if len(df_real) == 0:
        print("\n❌ Nenhum dado real encontrado!")
        return None, None
    
    # Criar samplers
    print("\n[2/7] Inicializando samplers...")
    sampler_cent = SolarSampler()
    sampler_dist = SolarDistribuidaSampler()
    print("  ✓ Samplers inicializados")
    
    # Processar cada mês
    print("\n[3/7] Gerando previsões e calculando métricas...")
    print("  " + "-"*76)
    
    resultados = []
    
    for (ano, mes), grupo in df_real.groupby(['ano', 'mes']):
        # Perfil real médio do mês
        perfil_total_real = grupo.set_index('hora')['total_real_mw'].values
        
        if len(perfil_total_real) != 24:
            print(f"  ⚠ {ano}-{mes:02d}: Dados incompletos ({len(perfil_total_real)} horas)")
            continue
        
        # Buscar MWmédios dos dicionários
        mw_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
        mw_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
        mw_total = capacidade_solar_total_dic.get(ano, {}).get(mes, 0)
        
        if mw_cent == 0 or mw_dist == 0:
            print(f"  ⚠ {ano}-{mes:02d}: MWmédios não disponível")
            continue
        
        # Gerar perfis previstos
        perfil_cent_prev = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist_prev = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        perfil_total_prev = perfil_cent_prev + perfil_dist_prev
        
        # Métricas
        metricas_total = calcular_metricas(perfil_total_real, perfil_total_prev)
        
        # Métricas individuais (comparando com proporções esperadas)
        # Centralizada esperada: aproximadamente proporcional ao MWmédios
        prop_cent = mw_cent / (mw_cent + mw_dist) if (mw_cent + mw_dist) > 0 else 0
        prop_dist = mw_dist / (mw_cent + mw_dist) if (mw_cent + mw_dist) > 0 else 0
        
        perfil_cent_esperado = perfil_total_real * prop_cent
        perfil_dist_esperado = perfil_total_real * prop_dist
        
        metricas_cent = calcular_metricas(perfil_cent_esperado, perfil_cent_prev)
        metricas_dist = calcular_metricas(perfil_dist_esperado, perfil_dist_prev)
        
        # Armazenar resultado
        resultados.append({
            'ano': ano,
            'mes': mes,
            'ano_mes': f"{ano}-{mes:02d}",
            'mw_total': mw_total,
            'mw_cent': mw_cent,
            'mw_dist': mw_dist,
            'prop_cent': prop_cent * 100,
            'prop_dist': prop_dist * 100,
            # Métricas total
            'total_mae': metricas_total['mae'],
            'total_mape': metricas_total['mape'],
            'total_r2': metricas_total['r2'],
            'total_bias_pct': metricas_total['bias_pct'],
            'total_hora_pico_real': metricas_total['hora_pico_real'],
            'total_hora_pico_prev': metricas_total['hora_pico_prev'],
            # Métricas individualcentralizada
            'cent_mae': metricas_cent['mae'],
            'cent_mape': metricas_cent['mape'],
            'cent_hora_pico': metricas_cent['hora_pico_prev'],
            # Métricas distribuída
            'dist_mae': metricas_dist['mae'],
            'dist_mape': metricas_dist['mape'],
            'dist_hora_pico': metricas_dist['hora_pico_prev']
        })
        
        # Printar resultado
        print(f"  {ano}-{mes:02d}:")
        print(f"    Total:        MAE={metricas_total['mae']:>6.1f} MW, "
              f"MAPE={metricas_total['mape']:>5.2f}%, R²={metricas_total['r2']:>6.3f}")
        print(f"    Centralizada: {mw_cent:>6.0f} MW ({prop_cent*100:>4.1f}%), "
              f"Pico={metricas_cent['hora_pico_prev']:02d}h")
        print(f"    Distribuída:  {mw_dist:>6.0f} MW ({prop_dist*100:>4.1f}%), "
              f"Pico={metricas_dist['hora_pico_prev']:02d}h")
    
    df_resultados = pd.DataFrame(resultados)
    
    # Métricas agregadas
    print("\n[4/7] Métricas Agregadas:")
    print("  " + "-"*76)
    print(f"\n  TOTAL (Centralizada + Distribuída):")
    print(f"    MAE médio:         {df_resultados['total_mae'].mean():>10.2f} MW")
    print(f"    MAPE médio:        {df_resultados['total_mape'].mean():>10.2f}%")
    print(f"    R² médio:          {df_resultados['total_r2'].mean():>10.3f}")
    print(f"    Bias médio:        {df_resultados['total_bias_pct'].mean():>10.2f}%")
    
    print(f"\n  PERFIL CENTRALIZADA:")
    print(f"    Pico médio:        {df_resultados['cent_hora_pico'].mean():>10.1f}h")
    print(f"    Proporção média:   {df_resultados['prop_cent'].mean():>10.1f}%")
    
    print(f"\n  PERFIL DISTRIBUÍDA:")
    print(f"    Pico médio:        {df_resultados['dist_hora_pico'].mean():>10.1f}h")
    print(f"    Proporção média:   {df_resultados['prop_dist'].mean():>10.1f}%")
    
    # Salvar métricas
    print("\n[5/7] Salvando métricas...")
    df_resultados.to_csv(BACKTEST_COMPARACAO_DIR / "metricas_backtest_completo.csv", index=False)
    print("  ✓ Métricas salvas")
    
    # Gerar séries sintéticas
    print("\n[6/7] Gerando séries sintéticas de exemplo...")
    series_sinteticas = []
    
    # Gerar para todos os meses disponíveis
    for _, row in df_resultados.iterrows():
        ano, mes = int(row['ano']), int(row['mes'])
        
        serie = gerar_series_sinteticas(sampler_cent, sampler_dist, ano, mes, n_dias=30)
        
        if serie is not None:
            series_sinteticas.append(serie)
            print(f"    ✓ {ano}-{mes:02d}: 30 dias ({30*24} registros)")
    
    if series_sinteticas:
        df_series = pd.concat(series_sinteticas, ignore_index=True)
        df_series.to_csv(BACKTEST_COMPARACAO_DIR / "series_sinteticas_completas.csv", index=False)
        print(f"\n  ✓ Total: {len(df_series):,} registros de séries sintéticas salvos")
    
    # Gerar visualizações
    print("\n[7/7] Gerando visualizações...")
    criar_graficos_backtest(df_real, df_resultados, sampler_cent, sampler_dist)
    
    # Relatório final
    gerar_relatorio_texto(df_resultados)
    
    print("\n" + "="*80)
    print("BACKTEST CONCLUÍDO COM SUCESSO!")
    print("="*80)
    
    return df_resultados, df_series if series_sinteticas else None


def criar_graficos_backtest(df_real, df_resultados, sampler_cent, sampler_dist):
    """
    Cria visualizações do backtest
    """
    # Gráfico 1: Métricas ao longo do tempo
    fig1, axes1 = plt.subplots(2, 2, figsize=(16, 10))
    fig1.suptitle('Métricas de Performance - Perfil Total (Cent + Dist)', 
                  fontsize=16, fontweight='bold')
    
    # MAPE
    ax = axes1[0, 0]
    ax.plot(df_resultados['ano_mes'], df_resultados['total_mape'], 'o-', 
            linewidth=2, markersize=6, color='steelblue')
    ax.axhline(y=df_resultados['total_mape'].mean(), color='red', 
               linestyle='--', alpha=0.5,
               label=f'Média: {df_resultados["total_mape"].mean():.2f}%')
    ax.set_title('MAPE ao Longo do Tempo', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('MAPE (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # R²
    ax = axes1[0, 1]
    ax.plot(df_resultados['ano_mes'], df_resultados['total_r2'], 'o-', 
            linewidth=2, markersize=6, color='green')
    ax.axhline(y=df_resultados['total_r2'].mean(), color='red', 
               linestyle='--', alpha=0.5,
               label=f'Média: {df_resultados["total_r2"].mean():.3f}')
    ax.set_title('R² ao Longo do Tempo', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('R²')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # Proporção Centralizada vs Distribuída
    ax = axes1[1, 0]
    x = np.arange(len(df_resultados))
    width = 0.35
    ax.bar(x, df_resultados['prop_cent'], width, label='Centralizada', alpha=0.8)
    ax.bar(x, df_resultados['prop_dist'], width, bottom=df_resultados['prop_cent'], 
           label='Distribuída', alpha=0.8)
    ax.set_xlabel('Mês')
    ax.set_ylabel('Proporção (%)')
    ax.set_title('Proporção Centralizada vs Distribuída', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(df_resultados['ano_mes'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Hora de Pico
    ax = axes1[1, 1]
    ax.plot(df_resultados['ano_mes'], df_resultados['cent_hora_pico'], 's-',  
            linewidth=2, markersize=6, label='Centralizada', alpha=0.8)
    ax.plot(df_resultados['ano_mes'], df_resultados['dist_hora_pico'], '^-', 
            linewidth=2, markersize=6, label='Distribuída', alpha=0.8)
    ax.axhline(y=14, color='blue', linestyle='--', alpha=0.3, label='14h (esperado cent)')
    ax.axhline(y=11, color='orange', linestyle='--', alpha=0.3, label='11h (esperado dist)')
    ax.set_title('Hora de Pico dos Perfis', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Hora do Pico')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    fig1_path = BACKTEST_COMPARACAO_DIR / "metricas_performance.png"
    plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print(f"  ✓ Gráfico de métricas salvo: {fig1_path.name}")
    
    # Gráfico 2: Perfis horários de exemplo
    meses_exemplo = df_resultados['ano_mes'].iloc[:6].values
    
    fig2, axes2 = plt.subplots(2, 3, figsize=(18, 10))
    fig2.suptitle('Perfis Horários - Real vs Modelo (Primeiros 6 Meses)', 
                  fontsize=16, fontweight='bold')
    
    for idx, ano_mes in enumerate(meses_exemplo):
        if idx >= 6:
            break
        
        row = idx // 3
        col = idx % 3
        ax = axes2[row, col]
        
        # Dados do mês
        ano, mes = map(int, ano_mes.split('-'))
        dados_mes = df_real[(df_real['ano'] == ano) & (df_real['mes'] == mes)]
        
        if len(dados_mes) == 0:
            continue
        
        # Perfil real
        perfil_total_real = dados_mes.set_index('hora')['total_real_mw'].values
        
        # MWmédios
        mw_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
        mw_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
        
        # Perfis previstos
        perfil_cent_prev = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist_prev = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        perfil_total_prev = perfil_cent_prev + perfil_dist_prev
        
        # Plotar
        horas = range(24)
        ax.plot(horas, perfil_total_real, 'o-', label='Total Real', 
                linewidth=2.5, markersize=6, color='black')
        ax.plot(horas, perfil_total_prev, 's--', label='Total Modelo (C+D)', 
                linewidth=2, markersize=4, alpha=0.7, color='purple')
        ax.fill_between(horas, 0, perfil_cent_prev, alpha=0.3, label='Centralizada', color='blue')
        ax.fill_between(horas, perfil_cent_prev, perfil_total_prev, 
                        alpha=0.3, label='Distribuída', color='orange')
        
        # Métricas do mês
        resultado_mes = df_resultados[df_resultados['ano_mes'] == ano_mes].iloc[0]
        
        ax.set_title(f'{ano_mes} | MAPE={resultado_mes["total_mape"]:.2f}% | R²={resultado_mes["total_r2"]:.3f}', 
                    fontsize=11, fontweight='bold')
        ax.set_xlabel('Hora do Dia')
        ax.set_ylabel('Geração (MW)')
        ax.legend(fontsize=8, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 3))
    
    plt.tight_layout()
    fig2_path = BACKTEST_COMPARACAO_DIR / "perfis_horarios_exemplo.png"
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f"  ✓ Gráfico de perfis horários salvo: {fig2_path.name}")
    
    # Gráfico 3: Perfil médio geral
    fig3, ax3 = plt.subplots(1, 1, figsize=(14, 7))
    
    # Calcular perfil médio de todos os meses
    perfil_medio_cent = np.zeros(24)
    perfil_medio_dist = np.zeros(24)
    n_meses = 0
    
    for _, row in df_resultados.iterrows():
        ano, mes = int(row['ano']), int(row['mes'])
        mw_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
        mw_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
        
        if mw_cent > 0 and mw_dist > 0:
            perfil_cent = sampler_cent.gerar_perfil_dia(mes, mw_cent)
            perfil_dist = sampler_dist.gerar_perfil_dia(mes, mw_dist)
            
            # Normalizar para porcentagem do dia
            perfil_medio_cent += (perfil_cent / perfil_cent.sum()) * 100
            perfil_medio_dist += (perfil_dist / perfil_dist.sum()) * 100
            n_meses += 1
    
    perfil_medio_cent /= n_meses
    perfil_medio_dist /= n_meses
    
    horas = range(24)
    ax3.plot(horas, perfil_medio_cent, 'o-', linewidth=3, markersize=8, 
            label='Centralizada (pico ~14h)', color='blue')
    ax3.plot(horas, perfil_medio_dist, 's-', linewidth=3, markersize=8, 
            label='Distribuída (pico ~11h)', color='orange')
    
    # Marcar horas de pico
    pico_cent = np.argmax(perfil_medio_cent)
    pico_dist = np.argmax(perfil_medio_dist)
    
    ax3.axvline(x=pico_cent, color='blue', linestyle='--', alpha=0.5, 
               label=f'Pico Cent: {pico_cent}h')
    ax3.axvline(x=pico_dist, color='orange', linestyle='--', alpha=0.5, 
               label=f'Pico Dist: {pico_dist}h')
    
    ax3.set_title('Perfil Horário Médio - Centralizada vs Distribuída', 
                 fontsize=14, fontweight='bold')
    ax3.set_xlabel('Hora do Dia', fontsize=12)
    ax3.set_ylabel('% da Geração Diária', fontsize=12)
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(range(0, 24))
    
    plt.tight_layout()
    fig3_path = BACKTEST_COMPARACAO_DIR / "perfil_medio_comparacao.png"
    plt.savefig(fig3_path, dpi=300, bbox_inches='tight')
    plt.close(fig3)
    print(f"  ✓ Gráfico de perfil médio salvo: {fig3_path.name}")


def gerar_relatorio_texto(df_resultados):
    """
    Gera relatório em texto
    """
    relatorio = []
    relatorio.append("="*80)
    relatorio.append("RELATÓRIO DE BACKTEST - GERAÇÃO SOLAR")
    relatorio.append("="*80)
    relatorio.append("")
    
    relatorio.append("1. RESUMO EXECUTIVO")
    relatorio.append("-" * 80)
    relatorio.append("")
    
    relatorio.append(f"PERFORMANCE GERAL (Centralizada + Distribuída):")
    relatorio.append(f"  - MAPE médio:       {df_resultados['total_mape'].mean():.2f}%")
    relatorio.append(f"  - R² médio:         {df_resultados['total_r2'].mean():.3f}")
    relatorio.append(f"  - MAE médio:        {df_resultados['total_mae'].mean():.2f} MW")
    relatorio.append(f"  - Bias médio:       {df_resultados['total_bias_pct'].mean():.2f}%")
    relatorio.append("")
    
    relatorio.append(f"CARACTERÍSTICAS DOS PERFIS:")
    relatorio.append(f"  - Centralizada:")
    relatorio.append(f"    • Proporção média:  {df_resultados['prop_cent'].mean():.1f}%")
    relatorio.append(f"    • Hora pico média:  {df_resultados['cent_hora_pico'].mean():.1f}h")
    relatorio.append(f"  - Distribuída:")
    relatorio.append(f"    • Proporção média:  {df_resultados['prop_dist'].mean():.1f}%")
    relatorio.append(f"    • Hora pico média:  {df_resultados['dist_hora_pico'].mean():.1f}h")
    relatorio.append("")
    
    # Classificação
    relatorio.append("2. AVALIAÇÃO DA QUALIDADE")
    relatorio.append("-" * 80)
    relatorio.append("")
    
    mape = df_resultados['total_mape'].mean()
    r2 = df_resultados['total_r2'].mean()
    
    if mape < 5 and r2 > 0.95:
        qualidade = "EXCELENTE"
    elif mape < 10 and r2 > 0.90:
        qualidade = "MUITO BOA"
    elif mape < 15 and r2 > 0.85:
        qualidade = "BOA"
    else:
        qualidade = "RAZOÁVEL"
    
    relatorio.append(f"Qualidade geral: {qualidade}")
    relatorio.append("")
    
    # Validação de características
    pico_cent = df_resultados['cent_hora_pico'].mean()
    pico_dist = df_resultados['dist_hora_pico'].mean()
    
    relatorio.append("3. VALIDAÇÃO DE CARACTERÍSTICAS")
    relatorio.append("-" * 80)
    relatorio.append("")
    
    if 13 <= pico_cent <= 15:
        relatorio.append("✅ Pico da centralizada dentro do esperado (13h-15h)")
    else:
        relatorio.append(f"⚠️  Pico da centralizada fora do esperado: {pico_cent:.1f}h")
    
    if 10 <= pico_dist <= 12:
        relatorio.append("✅ Pico da distribuída dentro do esperado (10h-12h)")
    else:
        relatorio.append(f"⚠️  Pico da distribuída fora do esperado: {pico_dist:.1f}h")
    
    diferenca_picos = abs(pico_cent - pico_dist)
    if diferenca_picos >= 2:
        relatorio.append(f"✅ Diferença entre picos adequada ({diferenca_picos:.1f}h)")
    else:
        relatorio.append(f"⚠️  Diferença entre picos muito pequena ({diferenca_picos:.1f}h)")
    
    relatorio.append("")
    
    # Análise por mês
    relatorio.append("4. MÉTRICAS POR MÊS")
    relatorio.append("-" * 80)
    relatorio.append("")
    relatorio.append(f"{'Mês':<10} {'MAPE':<8} {'R²':<8} {'MAE':<10} {'Bias%':<10}")
    relatorio.append("-" * 80)
    for _, row in df_resultados.iterrows():
        relatorio.append(f"{row['ano_mes']:<10} {row['total_mape']:>6.2f}% {row['total_r2']:>6.3f} "
                        f"{row['total_mae']:>8.1f} MW {row['total_bias_pct']:>8.2f}%")
    relatorio.append("")
    
    # Conclusão
    relatorio.append("5. CONCLUSÕES")
    relatorio.append("-" * 80)
    relatorio.append("")
    
    if mape < 10:
        relatorio.append("✅ Modelo apresenta excelente performance (MAPE < 10%)")
    else:
        relatorio.append("⚠️  Há oportunidade de melhoria no modelo")
    
    relatorio.append("")
    
    if abs(df_resultados['total_bias_pct'].mean()) < 3:
        relatorio.append("✅ Bias muito baixo (< 3%)")
    else:
        relatorio.append("⚠️  Revisar bias sistemático")
    
    relatorio.append("")
    
    if 13 <= pico_cent <= 15 and 10 <= pico_dist <= 12:
        relatorio.append("✅ Perfis horários capturando corretamente as características")
    else:
        relatorio.append("⚠️  Revisar perfis horários")
    
    relatorio.append("")
    relatorio.append("="*80)
    
    # Salvar relatório
    relatorio_texto = "\n".join(relatorio)
    relatorio_path = BACKTEST_COMPARACAO_DIR / "relatorio_backtest.txt"
    with open(relatorio_path, 'w', encoding='utf-8') as f:
        f.write(relatorio_texto)
    
    print(f"  ✓ Relatório salvo: {relatorio_path.name}")
    
    # Imprimir resumo na tela
    print("\n" + "="*80)
    print("RESUMO DO BACKTEST")
    print("="*80)
    print(f"\n  MAPE médio:     {df_resultados['total_mape'].mean():>6.2f}%")
    print(f"  R² médio:       {df_resultados['total_r2'].mean():>6.3f}")
    print(f"  Qualidade:      {qualidade}")
    print(f"\n  Pico Centralizada:  {pico_cent:>4.1f}h (esperado: 14h)")
    print(f"  Pico Distribuída:   {pico_dist:>4.1f}h (esperado: 11h)")


if __name__ == "__main__":
    df_resultados, df_series = realizar_backtest()




