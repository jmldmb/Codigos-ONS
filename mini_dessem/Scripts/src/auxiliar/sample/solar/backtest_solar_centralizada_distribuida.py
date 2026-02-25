"""
Backtest Completo - Geração Solar Centralizada e Distribuída
=============================================================

Valida os perfis horários de solar centralizada e distribuída gerando
séries sintéticas para cada mês e comparando com dados históricos.

Objetivos:
1. Testar se os perfis capturam bem o comportamento real
2. Comparar métricas entre centralizada e distribuída
3. Validar que centralizada + distribuída = total
4. Gerar séries sintéticas para análise de sensibilidade

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
from solar_sampler import SolarSampler
from solar_distribuida_sampler import SolarDistribuidaSampler

# Configurar estilo dos gráficos
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

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
DATA_CURTAILMENT = BASE_DIR / "output" / "curtailment" / "solar" / "comparacao_perfil_curtailment"


def carregar_dados_reais():
    """
    Carrega dados reais de geração solar total, centralizada e distribuída
    
    Returns:
        DataFrame com colunas: ano, mes, hora, total, centralizada, distribuida
    """
    print("\n[1/8] Carregando dados históricos...")
    
    # Lista para armazenar dados
    dados_consolidados = []
    
    # Carregar dados de 2024-04 a 2025-10 (período com separação cent/dist)
    anos_meses_disponiveis = []
    for ano in [2024, 2025]:
        inicio = 4 if ano == 2024 else 1
        fim = 12 if ano == 2024 else 10
        
        for mes in range(inicio, fim + 1):
            arquivo = DATA_BALANCO / f"BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx"
            
            if not arquivo.exists():
                continue
            
            try:
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
                
                # Filtrar mês específico
                df_mes = df[(df['ano'] == ano) & (df['mes'] == mes)].copy()
                
                if len(df_mes) == 0:
                    continue
                
                # Converter para numérico
                df_mes['val_gersolar'] = pd.to_numeric(df_mes['val_gersolar'], errors='coerce')
                
                # Calcular média por hora
                media_hora = df_mes.groupby('hora')['val_gersolar'].mean()
                
                # Carregar dados de centralizada (se disponível)
                arquivo_cent = DATA_CURTAILMENT / "por_mes" / f"{ano}_{mes:02d}_curtailment.csv"
                
                if arquivo_cent.exists():
                    df_cent = pd.read_csv(arquivo_cent)
                    df_cent = df_cent[df_cent['id_subsistema'] == 'SIN'].copy()
                    media_cent = df_cent.groupby('hora')['potencial_total_mwh'].mean()
                    
                    for hora in range(24):
                        total = media_hora.get(hora, 0)
                        cent = media_cent.get(hora, 0)
                        dist = total - cent
                        
                        dados_consolidados.append({
                            'ano': ano,
                            'mes': mes,
                            'hora': hora,
                            'total': total,
                            'centralizada': cent,
                            'distribuida': dist
                        })
                    
                    anos_meses_disponiveis.append(f"{ano}-{mes:02d}")
                    
            except Exception as e:
                print(f"  ⚠ Erro ao processar {ano}-{mes:02d}: {e}")
                continue
    
    df_real = pd.DataFrame(dados_consolidados)
    
    print(f"  ✓ {len(df_real)} registros horários carregados")
    print(f"  ✓ {len(anos_meses_disponiveis)} meses disponíveis: {', '.join(anos_meses_disponiveis[:5])}...")
    
    return df_real


def calcular_metricas(real: np.ndarray, previsto: np.ndarray, tipo: str = "geral") -> dict:
    """
    Calcula métricas de erro entre perfis horários
    
    Args:
        real: Perfil horário real (24 valores)
        previsto: Perfil horário previsto pelo modelo (24 valores)
        tipo: Tipo de geração ("geral", "diurno", "pico")
    
    Returns:
        Dicionário com métricas
    """
    # MAE e RMSE
    mae = np.mean(np.abs(real - previsto))
    rmse = np.sqrt(np.mean((real - previsto) ** 2))
    
    # MAPE apenas nas horas relevantes
    if tipo == "diurno":
        # Apenas horas de sol (6h-18h)
        mask = (np.arange(24) >= 6) & (np.arange(24) <= 18) & (real > 50)
    elif tipo == "pico":
        # Apenas horas de pico (10h-15h)
        mask = (np.arange(24) >= 10) & (np.arange(24) <= 15) & (real > 100)
    else:
        # Todas as horas com geração significativa
        mask = real > 50
    
    if mask.sum() > 0:
        mape = np.mean(np.abs((real[mask] - previsto[mask]) / real[mask])) * 100
    else:
        mape = np.nan
    
    # R² - Coeficiente de determinação
    ss_res = np.sum((real - previsto) ** 2)
    ss_tot = np.sum((real - np.mean(real)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    
    # Correlação de Pearson
    if np.std(real) > 0 and np.std(previsto) > 0:
        correlacao = np.corrcoef(real, previsto)[0, 1]
    else:
        correlacao = np.nan
    
    # Bias (erro médio)
    bias = np.mean(previsto - real)
    bias_pct = (bias / np.mean(real)) * 100 if np.mean(real) > 0 else np.nan
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
        'correlacao': correlacao,
        'bias': bias,
        'bias_pct': bias_pct
    }


def gerar_series_sinteticas(sampler, ano: int, mes: int, mw_medios: float, 
                            n_dias: int = 30, tipo: str = "centralizada"):
    """
    Gera série sintética de múltiplos dias para análise
    
    Args:
        sampler: Sampler (Solar ou SolarDistribuida)
        ano: Ano
        mes: Mês
        mw_medios: Potência média em MWmédios
        n_dias: Número de dias a gerar
        tipo: "centralizada" ou "distribuida"
    
    Returns:
        DataFrame com série sintética
    """
    dados = []
    
    for dia in range(1, n_dias + 1):
        # Gerar perfil do dia
        perfil = sampler.gerar_perfil_dia(mes, mw_medios)
        
        for hora in range(24):
            dados.append({
                'ano': ano,
                'mes': mes,
                'dia': dia,
                'hora': hora,
                'geracao_mw': perfil[hora],
                'tipo': tipo
            })
    
    return pd.DataFrame(dados)


def realizar_backtest():
    """
    Realiza backtest completo para centralizada e distribuída
    """
    print("="*80)
    print("BACKTEST COMPLETO - SOLAR CENTRALIZADA E DISTRIBUÍDA")
    print("="*80)
    
    # Carregar dados reais
    df_real = carregar_dados_reais()
    
    if len(df_real) == 0:
        print("\n❌ Nenhum dado real encontrado! Verifique os arquivos de dados.")
        return None, None, None
    
    # Criar samplers
    print("\n[2/8] Inicializando samplers...")
    sampler_cent = SolarSampler()
    sampler_dist = SolarDistribuidaSampler()
    print("  ✓ Samplers de centralizada e distribuída inicializados")
    
    # Processar cada mês
    print("\n[3/8] Gerando previsões e calculando métricas...")
    print("  " + "-"*76)
    
    resultados_cent = []
    resultados_dist = []
    resultados_total = []
    
    for (ano, mes), grupo in df_real.groupby(['ano', 'mes']):
        # Perfis reais médios
        perfil_total_real = grupo.set_index('hora')['total'].values
        perfil_cent_real = grupo.set_index('hora')['centralizada'].values
        perfil_dist_real = grupo.set_index('hora')['distribuida'].values
        
        # Calcular MWmédios
        n_dias = pd.Period(f'{ano}-{mes:02d}').days_in_month
        
        mw_medios_total = perfil_total_real.mean()
        mw_medios_cent = perfil_cent_real.mean()
        mw_medios_dist = perfil_dist_real.mean()
        
        # Gerar perfis previstos
        perfil_cent_prev = sampler_cent.gerar_perfil_dia(mes, mw_medios_cent)
        perfil_dist_prev = sampler_dist.gerar_perfil_dia(mes, mw_medios_dist)
        perfil_total_prev = perfil_cent_prev + perfil_dist_prev
        
        # Métricas para centralizada
        metricas_cent = calcular_metricas(perfil_cent_real, perfil_cent_prev, "diurno")
        resultados_cent.append({
            'ano': ano,
            'mes': mes,
            'ano_mes': f"{ano}-{mes:02d}",
            'mw_medios': mw_medios_cent,
            'total_real_dia': perfil_cent_real.sum(),
            'total_prev_dia': perfil_cent_prev.sum(),
            **metricas_cent
        })
        
        # Métricas para distribuída
        metricas_dist = calcular_metricas(perfil_dist_real, perfil_dist_prev, "diurno")
        resultados_dist.append({
            'ano': ano,
            'mes': mes,
            'ano_mes': f"{ano}-{mes:02d}",
            'mw_medios': mw_medios_dist,
            'total_real_dia': perfil_dist_real.sum(),
            'total_prev_dia': perfil_dist_prev.sum(),
            **metricas_dist
        })
        
        # Métricas para total (soma)
        metricas_total = calcular_metricas(perfil_total_real, perfil_total_prev, "diurno")
        resultados_total.append({
            'ano': ano,
            'mes': mes,
            'ano_mes': f"{ano}-{mes:02d}",
            'mw_medios': mw_medios_total,
            'total_real_dia': perfil_total_real.sum(),
            'total_prev_dia': perfil_total_prev.sum(),
            **metricas_total
        })
        
        # Printar resultado
        print(f"  {ano}-{mes:02d}:")
        print(f"    Centralizada: MAE={metricas_cent['mae']:>6.1f} MW, "
              f"MAPE={metricas_cent['mape']:>5.2f}%, R²={metricas_cent['r2']:>6.3f}")
        print(f"    Distribuída:  MAE={metricas_dist['mae']:>6.1f} MW, "
              f"MAPE={metricas_dist['mape']:>5.2f}%, R²={metricas_dist['r2']:>6.3f}")
        print(f"    Total (soma): MAE={metricas_total['mae']:>6.1f} MW, "
              f"MAPE={metricas_total['mape']:>5.2f}%, R²={metricas_total['r2']:>6.3f}")
    
    df_cent = pd.DataFrame(resultados_cent)
    df_dist = pd.DataFrame(resultados_dist)
    df_total = pd.DataFrame(resultados_total)
    
    # Métricas agregadas
    print("\n[4/8] Métricas Agregadas:")
    print("  " + "-"*76)
    
    print("\n  CENTRALIZADA:")
    print(f"    MAE médio:         {df_cent['mae'].mean():>10.2f} MW")
    print(f"    MAPE médio:        {df_cent['mape'].mean():>10.2f}%")
    print(f"    R² médio:          {df_cent['r2'].mean():>10.3f}")
    print(f"    Bias médio:        {df_cent['bias_pct'].mean():>10.2f}%")
    
    print("\n  DISTRIBUÍDA:")
    print(f"    MAE médio:         {df_dist['mae'].mean():>10.2f} MW")
    print(f"    MAPE médio:        {df_dist['mape'].mean():>10.2f}%")
    print(f"    R² médio:          {df_dist['r2'].mean():>10.3f}")
    print(f"    Bias médio:        {df_dist['bias_pct'].mean():>10.2f}%")
    
    print("\n  TOTAL (CENTRALIZADA + DISTRIBUÍDA):")
    print(f"    MAE médio:         {df_total['mae'].mean():>10.2f} MW")
    print(f"    MAPE médio:        {df_total['mape'].mean():>10.2f}%")
    print(f"    R² médio:          {df_total['r2'].mean():>10.3f}")
    print(f"    Bias médio:        {df_total['bias_pct'].mean():>10.2f}%")
    
    # Salvar métricas
    print("\n[5/8] Salvando métricas...")
    df_cent.to_csv(BACKTEST_SOLAR_DIR / "metricas_backtest_centralizada.csv", index=False)
    df_dist.to_csv(BACKTEST_DIST_DIR / "metricas_backtest_distribuida.csv", index=False)
    df_total.to_csv(BACKTEST_COMPARACAO_DIR / "metricas_backtest_total.csv", index=False)
    print("  ✓ Métricas salvas")
    
    # Gerar séries sintéticas
    print("\n[6/8] Gerando séries sintéticas de exemplo...")
    series_sinteticas = []
    
    # Gerar para alguns meses representativos
    meses_exemplo = [(2024, 6), (2024, 9), (2024, 12), (2025, 3), (2025, 6), (2025, 9)]
    
    for ano, mes in meses_exemplo:
        # Buscar MWmédios deste mês
        dados_mes = df_real[(df_real['ano'] == ano) & (df_real['mes'] == mes)]
        
        if len(dados_mes) > 0:
            mw_cent = dados_mes['centralizada'].mean()
            mw_dist = dados_mes['distribuida'].mean()
            
            # Gerar 30 dias
            serie_cent = gerar_series_sinteticas(sampler_cent, ano, mes, mw_cent, 30, "centralizada")
            serie_dist = gerar_series_sinteticas(sampler_dist, ano, mes, mw_dist, 30, "distribuida")
            
            # Consolidar
            serie_mes = pd.concat([serie_cent, serie_dist], ignore_index=True)
            series_sinteticas.append(serie_mes)
    
    if series_sinteticas:
        df_series = pd.concat(series_sinteticas, ignore_index=True)
        df_series.to_csv(BACKTEST_COMPARACAO_DIR / "series_sinteticas_exemplo.csv", index=False)
        print(f"  ✓ {len(df_series)} registros de séries sintéticas salvos")
    
    # Gerar visualizações
    print("\n[7/8] Gerando visualizações...")
    criar_graficos_comparativos(df_real, df_cent, df_dist, df_total, 
                                sampler_cent, sampler_dist)
    
    # Relatório final
    print("\n[8/8] Gerando relatório consolidado...")
    gerar_relatorio_texto(df_cent, df_dist, df_total)
    
    print("\n" + "="*80)
    print("BACKTEST CONCLUÍDO COM SUCESSO!")
    print("="*80)
    
    return df_cent, df_dist, df_total


def criar_graficos_comparativos(df_real, df_cent, df_dist, df_total,
                                sampler_cent, sampler_dist):
    """
    Cria visualizações comparativas entre centralizada e distribuída
    """
    # Gráfico 1: Comparação de métricas
    fig1, axes1 = plt.subplots(2, 3, figsize=(18, 10))
    fig1.suptitle('Comparação de Métricas - Centralizada vs Distribuída', 
                  fontsize=16, fontweight='bold')
    
    # MAPE
    ax = axes1[0, 0]
    x = np.arange(len(df_cent))
    width = 0.35
    ax.bar(x - width/2, df_cent['mape'], width, label='Centralizada', alpha=0.8)
    ax.bar(x + width/2, df_dist['mape'], width, label='Distribuída', alpha=0.8)
    ax.set_xlabel('Mês')
    ax.set_ylabel('MAPE (%)')
    ax.set_title('MAPE por Mês')
    ax.set_xticks(x)
    ax.set_xticklabels(df_cent['ano_mes'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # R²
    ax = axes1[0, 1]
    ax.bar(x - width/2, df_cent['r2'], width, label='Centralizada', alpha=0.8)
    ax.bar(x + width/2, df_dist['r2'], width, label='Distribuída', alpha=0.8)
    ax.set_xlabel('Mês')
    ax.set_ylabel('R²')
    ax.set_title('R² por Mês')
    ax.set_xticks(x)
    ax.set_xticklabels(df_cent['ano_mes'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # MAE
    ax = axes1[0, 2]
    ax.bar(x - width/2, df_cent['mae'], width, label='Centralizada', alpha=0.8)
    ax.bar(x + width/2, df_dist['mae'], width, label='Distribuída', alpha=0.8)
    ax.set_xlabel('Mês')
    ax.set_ylabel('MAE (MW)')
    ax.set_title('MAE por Mês')
    ax.set_xticks(x)
    ax.set_xticklabels(df_cent['ano_mes'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Bias %
    ax = axes1[1, 0]
    ax.bar(x - width/2, df_cent['bias_pct'], width, label='Centralizada', alpha=0.8)
    ax.bar(x + width/2, df_dist['bias_pct'], width, label='Distribuída', alpha=0.8)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_xlabel('Mês')
    ax.set_ylabel('Bias (%)')
    ax.set_title('Bias (%) por Mês')
    ax.set_xticks(x)
    ax.set_xticklabels(df_cent['ano_mes'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Distribuição MAPE
    ax = axes1[1, 1]
    ax.hist(df_cent['mape'], bins=10, alpha=0.6, label='Centralizada', edgecolor='black')
    ax.hist(df_dist['mape'], bins=10, alpha=0.6, label='Distribuída', edgecolor='black')
    ax.set_xlabel('MAPE (%)')
    ax.set_ylabel('Frequência')
    ax.set_title('Distribuição de MAPE')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Comparação Total
    ax = axes1[1, 2]
    metricas_comp = {
        'MAPE (%)': [df_cent['mape'].mean(), df_dist['mape'].mean(), df_total['mape'].mean()],
        'R²': [df_cent['r2'].mean(), df_dist['r2'].mean(), df_total['r2'].mean()],
        'MAE (MW)': [df_cent['mae'].mean(), df_dist['mae'].mean(), df_total['mae'].mean()]
    }
    
    labels = ['Centralizada', 'Distribuída', 'Total']
    x_pos = np.arange(len(labels))
    
    # Normalizar para visualização
    mape_norm = np.array(metricas_comp['MAPE (%)']) / max(metricas_comp['MAPE (%)'])
    r2_norm = np.array(metricas_comp['R²'])
    
    ax.bar(x_pos - 0.2, mape_norm, 0.4, label='MAPE (norm)', alpha=0.8)
    ax.bar(x_pos + 0.2, r2_norm, 0.4, label='R²', alpha=0.8)
    ax.set_xlabel('Tipo')
    ax.set_ylabel('Valor (normalizado)')
    ax.set_title('Resumo de Métricas')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    fig1_path = BACKTEST_COMPARACAO_DIR / "comparacao_metricas.png"
    plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print(f"  ✓ Gráfico de comparação salvo: {fig1_path}")
    
    # Gráfico 2: Perfis horários para alguns meses
    meses_exemplo = df_cent['ano_mes'].iloc[:6].values  # Primeiros 6 meses
    
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
        
        # Perfis reais
        perfil_cent_real = dados_mes.set_index('hora')['centralizada'].values
        perfil_dist_real = dados_mes.set_index('hora')['distribuida'].values
        
        # MWmédios
        mw_cent = perfil_cent_real.mean()
        mw_dist = perfil_dist_real.mean()
        
        # Perfis previstos
        perfil_cent_prev = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist_prev = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        
        # Plotar
        horas = range(24)
        ax.plot(horas, perfil_cent_real, 'o-', label='Cent Real', linewidth=2, markersize=4)
        ax.plot(horas, perfil_cent_prev, 's--', label='Cent Modelo', linewidth=2, markersize=4, alpha=0.7)
        ax.plot(horas, perfil_dist_real, '^-', label='Dist Real', linewidth=2, markersize=4)
        ax.plot(horas, perfil_dist_prev, 'v--', label='Dist Modelo', linewidth=2, markersize=4, alpha=0.7)
        
        ax.set_title(f'{ano_mes}', fontsize=11, fontweight='bold')
        ax.set_xlabel('Hora do Dia')
        ax.set_ylabel('Geração (MW)')
        ax.legend(fontsize=8, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 3))
    
    plt.tight_layout()
    fig2_path = BACKTEST_COMPARACAO_DIR / "perfis_horarios_exemplo.png"
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f"  ✓ Gráfico de perfis horários salvo: {fig2_path}")
    
    # Gráfico 3: Análise de erro por hora do dia
    fig3, axes3 = plt.subplots(1, 3, figsize=(18, 5))
    fig3.suptitle('Erro Médio por Hora do Dia', fontsize=16, fontweight='bold')
    
    # Calcular erro médio por hora
    erros_cent = np.zeros(24)
    erros_dist = np.zeros(24)
    erros_total = np.zeros(24)
    n_meses = 0
    
    for _, row_cent in df_cent.iterrows():
        ano, mes = row_cent['ano'], row_cent['mes']
        
        dados_mes = df_real[(df_real['ano'] == ano) & (df_real['mes'] == mes)]
        
        if len(dados_mes) == 0:
            continue
        
        perfil_cent_real = dados_mes.set_index('hora')['centralizada'].values
        perfil_dist_real = dados_mes.set_index('hora')['distribuida'].values
        perfil_total_real = dados_mes.set_index('hora')['total'].values
        
        mw_cent = perfil_cent_real.mean()
        mw_dist = perfil_dist_real.mean()
        
        perfil_cent_prev = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist_prev = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        perfil_total_prev = perfil_cent_prev + perfil_dist_prev
        
        erros_cent += np.abs(perfil_cent_real - perfil_cent_prev)
        erros_dist += np.abs(perfil_dist_real - perfil_dist_prev)
        erros_total += np.abs(perfil_total_real - perfil_total_prev)
        
        n_meses += 1
    
    erros_cent /= n_meses
    erros_dist /= n_meses
    erros_total /= n_meses
    
    horas = range(24)
    
    # Centralizada
    axes3[0].bar(horas, erros_cent, color='steelblue', edgecolor='darkblue', alpha=0.7)
    axes3[0].set_title('Centralizada', fontsize=12, fontweight='bold')
    axes3[0].set_xlabel('Hora do Dia')
    axes3[0].set_ylabel('MAE (MW)')
    axes3[0].grid(True, alpha=0.3, axis='y')
    axes3[0].set_xticks(range(0, 24, 2))
    
    # Distribuída
    axes3[1].bar(horas, erros_dist, color='coral', edgecolor='darkred', alpha=0.7)
    axes3[1].set_title('Distribuída', fontsize=12, fontweight='bold')
    axes3[1].set_xlabel('Hora do Dia')
    axes3[1].set_ylabel('MAE (MW)')
    axes3[1].grid(True, alpha=0.3, axis='y')
    axes3[1].set_xticks(range(0, 24, 2))
    
    # Total
    axes3[2].bar(horas, erros_total, color='green', edgecolor='darkgreen', alpha=0.7)
    axes3[2].set_title('Total', fontsize=12, fontweight='bold')
    axes3[2].set_xlabel('Hora do Dia')
    axes3[2].set_ylabel('MAE (MW)')
    axes3[2].grid(True, alpha=0.3, axis='y')
    axes3[2].set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    fig3_path = BACKTEST_COMPARACAO_DIR / "erro_por_hora.png"
    plt.savefig(fig3_path, dpi=300, bbox_inches='tight')
    plt.close(fig3)
    print(f"  ✓ Gráfico de erro por hora salvo: {fig3_path}")


def gerar_relatorio_texto(df_cent, df_dist, df_total):
    """
    Gera relatório em texto com análise dos resultados
    """
    relatorio = []
    relatorio.append("="*80)
    relatorio.append("RELATÓRIO DE BACKTEST - GERAÇÃO SOLAR CENTRALIZADA E DISTRIBUÍDA")
    relatorio.append("="*80)
    relatorio.append("")
    
    relatorio.append("1. RESUMO EXECUTIVO")
    relatorio.append("-" * 80)
    relatorio.append("")
    
    # Centralizada
    relatorio.append("GERAÇÃO CENTRALIZADA:")
    relatorio.append(f"  - MAPE médio:       {df_cent['mape'].mean():.2f}%")
    relatorio.append(f"  - R² médio:         {df_cent['r2'].mean():.3f}")
    relatorio.append(f"  - MAE médio:        {df_cent['mae'].mean():.2f} MW")
    relatorio.append(f"  - Bias médio:       {df_cent['bias_pct'].mean():.2f}%")
    relatorio.append(f"  - Correlação média: {df_cent['correlacao'].mean():.3f}")
    relatorio.append("")
    
    # Distribuída
    relatorio.append("GERAÇÃO DISTRIBUÍDA:")
    relatorio.append(f"  - MAPE médio:       {df_dist['mape'].mean():.2f}%")
    relatorio.append(f"  - R² médio:         {df_dist['r2'].mean():.3f}")
    relatorio.append(f"  - MAE médio:        {df_dist['mae'].mean():.2f} MW")
    relatorio.append(f"  - Bias médio:       {df_dist['bias_pct'].mean():.2f}%")
    relatorio.append(f"  - Correlação média: {df_dist['correlacao'].mean():.3f}")
    relatorio.append("")
    
    # Total
    relatorio.append("TOTAL (CENTRALIZADA + DISTRIBUÍDA):")
    relatorio.append(f"  - MAPE médio:       {df_total['mape'].mean():.2f}%")
    relatorio.append(f"  - R² médio:         {df_total['r2'].mean():.3f}")
    relatorio.append(f"  - MAE médio:        {df_total['mae'].mean():.2f} MW")
    relatorio.append(f"  - Bias médio:       {df_total['bias_pct'].mean():.2f}%")
    relatorio.append(f"  - Correlação média: {df_total['correlacao'].mean():.3f}")
    relatorio.append("")
    
    # Classificação
    relatorio.append("2. AVALIAÇÃO DA QUALIDADE")
    relatorio.append("-" * 80)
    relatorio.append("")
    
    def classificar(mape, r2):
        if mape < 5 and r2 > 0.95:
            return "EXCELENTE"
        elif mape < 10 and r2 > 0.90:
            return "MUITO BOA"
        elif mape < 15 and r2 > 0.85:
            return "BOA"
        else:
            return "RAZOÁVEL"
    
    relatorio.append(f"Centralizada: {classificar(df_cent['mape'].mean(), df_cent['r2'].mean())}")
    relatorio.append(f"Distribuída:  {classificar(df_dist['mape'].mean(), df_dist['r2'].mean())}")
    relatorio.append(f"Total:        {classificar(df_total['mape'].mean(), df_total['r2'].mean())}")
    relatorio.append("")
    
    # Análise por mês
    relatorio.append("3. MÉTRICAS POR MÊS")
    relatorio.append("-" * 80)
    relatorio.append("")
    relatorio.append("Centralizada:")
    relatorio.append(f"{'Mês':<10} {'MAPE':<8} {'R²':<8} {'MAE':<10} {'Bias%':<10}")
    for _, row in df_cent.iterrows():
        relatorio.append(f"{row['ano_mes']:<10} {row['mape']:>6.2f}% {row['r2']:>6.3f} "
                        f"{row['mae']:>8.1f} MW {row['bias_pct']:>8.2f}%")
    relatorio.append("")
    
    relatorio.append("Distribuída:")
    relatorio.append(f"{'Mês':<10} {'MAPE':<8} {'R²':<8} {'MAE':<10} {'Bias%':<10}")
    for _, row in df_dist.iterrows():
        relatorio.append(f"{row['ano_mes']:<10} {row['mape']:>6.2f}% {row['r2']:>6.3f} "
                        f"{row['mae']:>8.1f} MW {row['bias_pct']:>8.2f}%")
    relatorio.append("")
    
    # Conclusão
    relatorio.append("4. CONCLUSÕES")
    relatorio.append("-" * 80)
    relatorio.append("")
    
    if df_cent['mape'].mean() < 10 and df_dist['mape'].mean() < 10:
        relatorio.append("✅ Ambos os modelos apresentam performance excelente (MAPE < 10%)")
    else:
        relatorio.append("⚠️  Há oportunidade de melhoria nos modelos")
    
    relatorio.append("")
    
    if abs(df_cent['bias_pct'].mean()) < 3 and abs(df_dist['bias_pct'].mean()) < 3:
        relatorio.append("✅ Bias muito baixo em ambos os modelos (< 3%)")
    else:
        relatorio.append("⚠️  Revisar bias - pode indicar viés sistemático")
    
    relatorio.append("")
    relatorio.append("="*80)
    
    # Salvar relatório
    relatorio_texto = "\n".join(relatorio)
    relatorio_path = BACKTEST_COMPARACAO_DIR / "relatorio_backtest.txt"
    with open(relatorio_path, 'w', encoding='utf-8') as f:
        f.write(relatorio_texto)
    
    print(f"  ✓ Relatório salvo: {relatorio_path}")
    
    # Imprimir resumo na tela
    print("\n" + "="*80)
    print("RESUMO DO BACKTEST")
    print("="*80)
    print(f"\n{'Tipo':<15} {'MAPE':<10} {'R²':<10} {'Qualidade':<15}")
    print("-" * 80)
    print(f"{'Centralizada':<15} {df_cent['mape'].mean():>6.2f}% {df_cent['r2'].mean():>8.3f}   "
          f"{classificar(df_cent['mape'].mean(), df_cent['r2'].mean())}")
    print(f"{'Distribuída':<15} {df_dist['mape'].mean():>6.2f}% {df_dist['r2'].mean():>8.3f}   "
          f"{classificar(df_dist['mape'].mean(), df_dist['r2'].mean())}")
    print(f"{'Total':<15} {df_total['mape'].mean():>6.2f}% {df_total['r2'].mean():>8.3f}   "
          f"{classificar(df_total['mape'].mean(), df_total['r2'].mean())}")


if __name__ == "__main__":
    df_cent, df_dist, df_total = realizar_backtest()




