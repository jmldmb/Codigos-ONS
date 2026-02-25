"""
Gerar Séries Sintéticas Completas e Comparar com Dados Reais
=============================================================

Gera séries sintéticas hora a hora para cada mês desde abril/2024
e compara com os dados reais do BALANCO_ENERGIA.

Para cada mês:
- Gera série sintética completa (todos os dias do mês)
- Compara com dados reais
- Calcula métricas de erro
- Gera visualizações de comparação

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
from datetime import date, timedelta
from solar_sampler import SolarSampler
from solar_distribuida_sampler import SolarDistribuidaSampler

# Configurar estilo dos gráficos
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Adicionar caminho para acessar data.py
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mini_dessem.data import (
    geracao_solar_centralizada_dic,
    geracao_solar_distribuida_dic,
    capacidade_solar_total_dic
)

# Definir diretórios
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "sample" / "solar_comparacao"

# Diretórios de output
SERIES_DIR = OUTPUT_DIR / "series_sinteticas"
COMPARACAO_DIR = OUTPUT_DIR / "comparacao_real"
METRICAS_DIR = OUTPUT_DIR / "metricas"

# Criar diretórios
SERIES_DIR.mkdir(parents=True, exist_ok=True)
COMPARACAO_DIR.mkdir(parents=True, exist_ok=True)
METRICAS_DIR.mkdir(parents=True, exist_ok=True)

# Caminhos de dados
DATA_BALANCO = BASE_DIR / "Data" / "raw_data"


def carregar_dados_reais_detalhados(ano, mes):
    """
    Carrega dados reais HORA A HORA de um mês específico
    
    Returns:
        DataFrame com colunas: data_hora, hora, total_real_mw
    """
    arquivo = DATA_BALANCO / f"BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx"
    
    if not arquivo.exists():
        return None
    
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
        
        # Filtrar apenas o mês desejado
        df = df[(df['din_instante'].dt.year == ano) & 
                (df['din_instante'].dt.month == mes)].copy()
        
        if len(df) == 0:
            return None
        
        # Converter para numérico
        df['val_gersolar'] = pd.to_numeric(df['val_gersolar'], errors='coerce')
        
        # Preparar saída
        df_saida = df[['din_instante', 'val_gersolar']].copy()
        df_saida.columns = ['data_hora', 'total_real_mw']
        df_saida['hora'] = df_saida['data_hora'].dt.hour
        df_saida = df_saida.sort_values('data_hora').reset_index(drop=True)
        
        return df_saida
        
    except Exception as e:
        print(f"  ⚠ Erro ao processar {ano}-{mes:02d}: {e}")
        return None


def gerar_serie_sintetica_mes(sampler_cent, sampler_dist, ano, mes):
    """
    Gera série sintética COMPLETA para um mês específico
    (todos os dias do mês, hora a hora)
    
    Returns:
        DataFrame com colunas: data_hora, hora, cent_mw, dist_mw, total_mw
    """
    # Buscar MWmédios dos dicionários
    mw_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
    mw_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
    
    if mw_cent == 0 or mw_dist == 0:
        return None
    
    # Número de dias no mês
    n_dias = calendar.monthrange(ano, mes)[1]
    
    dados = []
    
    for dia in range(1, n_dias + 1):
        # Gerar perfis do dia
        perfil_cent = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        
        for hora in range(24):
            data_hora = pd.Timestamp(year=ano, month=mes, day=dia, hour=hora)
            
            dados.append({
                'data_hora': data_hora,
                'hora': hora,
                'cent_mw': perfil_cent[hora],
                'dist_mw': perfil_dist[hora],
                'total_mw': perfil_cent[hora] + perfil_dist[hora]
            })
    
    return pd.DataFrame(dados)


def calcular_metricas_serie(df_comparacao):
    """
    Calcula métricas entre real e sintético para uma série completa
    """
    real = df_comparacao['total_real_mw'].values
    sintetico = df_comparacao['total_sintetico_mw'].values
    
    # Remover NaNs
    mask = ~(np.isnan(real) | np.isnan(sintetico))
    real = real[mask]
    sintetico = sintetico[mask]
    
    if len(real) == 0:
        return None
    
    # MAE e RMSE
    mae = np.mean(np.abs(real - sintetico))
    rmse = np.sqrt(np.mean((real - sintetico) ** 2))
    
    # MAPE apenas nas horas com geração significativa
    mask_sig = real > 100
    if mask_sig.sum() > 0:
        mape = np.mean(np.abs((real[mask_sig] - sintetico[mask_sig]) / real[mask_sig])) * 100
    else:
        mape = np.nan
    
    # R²
    ss_res = np.sum((real - sintetico) ** 2)
    ss_tot = np.sum((real - np.mean(real)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    
    # Correlação
    if np.std(real) > 0 and np.std(sintetico) > 0:
        correlacao = np.corrcoef(real, sintetico)[0, 1]
    else:
        correlacao = np.nan
    
    # Bias
    bias = np.mean(sintetico - real)
    bias_pct = (bias / np.mean(real)) * 100 if np.mean(real) > 0 else np.nan
    
    # Max error
    max_error = np.max(np.abs(real - sintetico))
    
    return {
        'n_registros': len(real),
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
        'correlacao': correlacao,
        'bias': bias,
        'bias_pct': bias_pct,
        'max_error': max_error,
        'media_real': np.mean(real),
        'media_sintetico': np.mean(sintetico)
    }


def criar_grafico_comparacao_mes(df_comparacao, ano, mes, metricas):
    """
    Cria visualização comparando real vs sintético para um mês
    """
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle(f'Comparação Real vs Sintético - {ano}-{mes:02d}', 
                 fontsize=16, fontweight='bold')
    
    # 1. Série temporal completa
    ax = axes[0]
    ax.plot(df_comparacao['data_hora'], df_comparacao['total_real_mw'], 
            '-', linewidth=1, label='Real', alpha=0.8, color='blue')
    ax.plot(df_comparacao['data_hora'], df_comparacao['total_sintetico_mw'], 
            '-', linewidth=1, label='Sintético', alpha=0.7, color='red')
    
    ax.set_title('Série Temporal Completa', fontsize=12, fontweight='bold')
    ax.set_xlabel('Data/Hora')
    ax.set_ylabel('Geração Solar Total (MW)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Adicionar métricas no canto
    textstr = f'MAPE: {metricas["mape"]:.2f}%\nR²: {metricas["r2"]:.3f}\nMAE: {metricas["mae"]:.1f} MW'
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 2. Scatter plot Real vs Sintético
    ax = axes[1]
    ax.scatter(df_comparacao['total_real_mw'], df_comparacao['total_sintetico_mw'], 
              alpha=0.5, s=10, c=df_comparacao['hora'], cmap='viridis')
    
    # Linha de referência (perfeito)
    min_val = min(df_comparacao['total_real_mw'].min(), df_comparacao['total_sintetico_mw'].min())
    max_val = max(df_comparacao['total_real_mw'].max(), df_comparacao['total_sintetico_mw'].max())
    ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Ajuste Perfeito')
    
    ax.set_title('Real vs Sintético (todos os pontos)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Real (MW)')
    ax.set_ylabel('Sintético (MW)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Adicionar colorbar para hora
    plt.colorbar(ax.collections[0], ax=ax, label='Hora do Dia')
    
    # 3. Perfil médio por hora do dia
    ax = axes[2]
    
    perfil_real = df_comparacao.groupby('hora')['total_real_mw'].mean()
    perfil_sint = df_comparacao.groupby('hora')['total_sintetico_mw'].mean()
    perfil_erro = perfil_sint - perfil_real
    
    horas = range(24)
    ax.plot(horas, perfil_real, 'o-', linewidth=2, markersize=6, 
            label='Real (média)', color='blue')
    ax.plot(horas, perfil_sint, 's--', linewidth=2, markersize=6, 
            label='Sintético (média)', color='red', alpha=0.7)
    
    # Área de erro
    ax2 = ax.twinx()
    ax2.bar(horas, perfil_erro, alpha=0.3, color='gray', label='Erro (Sint - Real)')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_ylabel('Erro (MW)', fontsize=11)
    ax2.legend(loc='upper right')
    
    ax.set_title('Perfil Médio por Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_xlabel('Hora do Dia')
    ax.set_ylabel('Geração Solar (MW)', fontsize=11)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24))
    
    plt.tight_layout()
    
    # Salvar figura
    fig_path = COMPARACAO_DIR / f"{ano}_{mes:02d}_comparacao.png"
    plt.savefig(fig_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    
    return fig_path


def processar_todos_os_meses():
    """
    Processa todos os meses desde abril/2024
    """
    print("="*80)
    print("GERAÇÃO DE SÉRIES SINTÉTICAS E COMPARAÇÃO COM DADOS REAIS")
    print("="*80)
    
    # Criar samplers
    print("\n[1/4] Inicializando samplers...")
    sampler_cent = SolarSampler()
    sampler_dist = SolarDistribuidaSampler()
    print("  ✓ Samplers inicializados")
    
    # Definir meses a processar
    meses_processar = []
    
    # 2024: abril a dezembro
    for mes in range(4, 13):
        meses_processar.append((2024, mes))
    
    # 2025: janeiro a outubro
    for mes in range(1, 11):
        meses_processar.append((2025, mes))
    
    print(f"\n[2/4] Processando {len(meses_processar)} meses...")
    print("  " + "-"*76)
    
    resultados = []
    todas_series = []
    
    for ano, mes in meses_processar:
        print(f"\n  Processando {ano}-{mes:02d}...")
        
        # Carregar dados reais
        df_real = carregar_dados_reais_detalhados(ano, mes)
        
        if df_real is None or len(df_real) == 0:
            print(f"    ⚠ Sem dados reais disponíveis")
            continue
        
        print(f"    ✓ Dados reais carregados: {len(df_real)} registros")
        
        # Gerar série sintética
        df_sintetico = gerar_serie_sintetica_mes(sampler_cent, sampler_dist, ano, mes)
        
        if df_sintetico is None:
            print(f"    ⚠ Erro ao gerar série sintética")
            continue
        
        print(f"    ✓ Série sintética gerada: {len(df_sintetico)} registros")
        
        # Merge para comparação
        df_comparacao = pd.merge(
            df_real[['data_hora', 'hora', 'total_real_mw']], 
            df_sintetico[['data_hora', 'hora', 'cent_mw', 'dist_mw', 'total_mw']], 
            on=['data_hora', 'hora'], 
            how='inner'
        )
        df_comparacao = df_comparacao.rename(columns={'total_mw': 'total_sintetico_mw'})
        
        print(f"    ✓ Comparação: {len(df_comparacao)} registros pareados")
        
        # Calcular métricas
        metricas = calcular_metricas_serie(df_comparacao)
        
        if metricas is None:
            print(f"    ⚠ Erro ao calcular métricas")
            continue
        
        print(f"    ✓ Métricas: MAPE={metricas['mape']:.2f}%, R²={metricas['r2']:.3f}, MAE={metricas['mae']:.1f} MW")
        
        # Salvar série sintética individual
        serie_path = SERIES_DIR / f"{ano}_{mes:02d}_serie_sintetica.csv"
        df_sintetico.to_csv(serie_path, index=False)
        print(f"    ✓ Série sintética salva: {serie_path.name}")
        
        # Salvar comparação
        comp_path = SERIES_DIR / f"{ano}_{mes:02d}_comparacao.csv"
        df_comparacao.to_csv(comp_path, index=False)
        print(f"    ✓ Comparação salva: {comp_path.name}")
        
        # Criar gráfico
        fig_path = criar_grafico_comparacao_mes(df_comparacao, ano, mes, metricas)
        print(f"    ✓ Gráfico salvo: {fig_path.name}")
        
        # Armazenar resultados
        resultados.append({
            'ano': ano,
            'mes': mes,
            'ano_mes': f"{ano}-{mes:02d}",
            **metricas
        })
        
        # Adicionar ao consolidado
        df_sintetico['ano'] = ano
        df_sintetico['mes'] = mes
        todas_series.append(df_sintetico)
    
    # Consolidar resultados
    print("\n[3/4] Consolidando resultados...")
    
    df_metricas = pd.DataFrame(resultados)
    df_metricas_path = METRICAS_DIR / "metricas_por_mes.csv"
    df_metricas.to_csv(df_metricas_path, index=False)
    print(f"  ✓ Métricas consolidadas salvas: {df_metricas_path.name}")
    
    if todas_series:
        df_todas_series = pd.concat(todas_series, ignore_index=True)
        series_consolidadas_path = SERIES_DIR / "series_sinteticas_consolidadas.csv"
        df_todas_series.to_csv(series_consolidadas_path, index=False)
        print(f"  ✓ Séries consolidadas salvas: {series_consolidadas_path.name}")
        print(f"    Total de registros: {len(df_todas_series):,}")
    
    # Gerar resumo
    print("\n[4/4] Gerando visualização resumo...")
    criar_grafico_resumo(df_metricas)
    
    # Relatório final
    print("\n" + "="*80)
    print("RESUMO GERAL")
    print("="*80)
    print(f"\n  Meses processados:     {len(df_metricas)}")
    print(f"  Total de registros:    {len(df_todas_series):,}")
    print(f"\n  MÉTRICAS MÉDIAS:")
    print(f"    MAPE:                {df_metricas['mape'].mean():.2f}%")
    print(f"    R²:                  {df_metricas['r2'].mean():.3f}")
    print(f"    MAE:                 {df_metricas['mae'].mean():.1f} MW")
    print(f"    Correlação:          {df_metricas['correlacao'].mean():.3f}")
    print(f"    Bias:                {df_metricas['bias_pct'].mean():.2f}%")
    
    print(f"\n  ARQUIVOS GERADOS:")
    print(f"    Séries individuais:  {SERIES_DIR}")
    print(f"    Comparações:         {COMPARACAO_DIR}")
    print(f"    Métricas:            {METRICAS_DIR}")
    
    print("\n" + "="*80)
    print("PROCESSAMENTO CONCLUÍDO!")
    print("="*80)
    
    return df_metricas, df_todas_series


def criar_grafico_resumo(df_metricas):
    """
    Cria gráfico resumo de todas as métricas
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Resumo de Performance - Todos os Meses', fontsize=16, fontweight='bold')
    
    # 1. MAPE ao longo do tempo
    ax = axes[0, 0]
    ax.plot(df_metricas['ano_mes'], df_metricas['mape'], 'o-', 
            linewidth=2, markersize=6, color='steelblue')
    ax.axhline(y=df_metricas['mape'].mean(), color='red', linestyle='--', 
               alpha=0.5, label=f'Média: {df_metricas["mape"].mean():.2f}%')
    ax.set_title('MAPE por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('MAPE (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 2. R² ao longo do tempo
    ax = axes[0, 1]
    ax.plot(df_metricas['ano_mes'], df_metricas['r2'], 'o-', 
            linewidth=2, markersize=6, color='green')
    ax.axhline(y=df_metricas['r2'].mean(), color='red', linestyle='--', 
               alpha=0.5, label=f'Média: {df_metricas["r2"].mean():.3f}')
    ax.set_title('R² por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('R²')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 3. MAE ao longo do tempo
    ax = axes[0, 2]
    ax.plot(df_metricas['ano_mes'], df_metricas['mae'], 'o-', 
            linewidth=2, markersize=6, color='coral')
    ax.axhline(y=df_metricas['mae'].mean(), color='red', linestyle='--', 
               alpha=0.5, label=f'Média: {df_metricas["mae"].mean():.1f} MW')
    ax.set_title('MAE por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('MAE (MW)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 4. Distribuição de MAPE
    ax = axes[1, 0]
    ax.hist(df_metricas['mape'], bins=15, color='steelblue', 
            edgecolor='black', alpha=0.7)
    ax.axvline(x=df_metricas['mape'].mean(), color='red', 
               linestyle='--', linewidth=2, label=f'Média: {df_metricas["mape"].mean():.2f}%')
    ax.set_title('Distribuição de MAPE', fontsize=12, fontweight='bold')
    ax.set_xlabel('MAPE (%)')
    ax.set_ylabel('Frequência')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 5. Bias ao longo do tempo
    ax = axes[1, 1]
    ax.plot(df_metricas['ano_mes'], df_metricas['bias_pct'], 'o-', 
            linewidth=2, markersize=6, color='purple')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.axhline(y=df_metricas['bias_pct'].mean(), color='red', linestyle='--', 
               alpha=0.5, label=f'Média: {df_metricas["bias_pct"].mean():.2f}%')
    ax.set_title('Bias por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Bias (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 6. Tabela de resumo
    ax = axes[1, 2]
    ax.axis('off')
    
    resumo_texto = [
        ['Métrica', 'Média', 'Min', 'Max'],
        ['MAPE (%)', f"{df_metricas['mape'].mean():.2f}", 
         f"{df_metricas['mape'].min():.2f}", f"{df_metricas['mape'].max():.2f}"],
        ['R²', f"{df_metricas['r2'].mean():.3f}", 
         f"{df_metricas['r2'].min():.3f}", f"{df_metricas['r2'].max():.3f}"],
        ['MAE (MW)', f"{df_metricas['mae'].mean():.1f}", 
         f"{df_metricas['mae'].min():.1f}", f"{df_metricas['mae'].max():.1f}"],
        ['Bias (%)', f"{df_metricas['bias_pct'].mean():.2f}", 
         f"{df_metricas['bias_pct'].min():.2f}", f"{df_metricas['bias_pct'].max():.2f}"],
        ['Corr', f"{df_metricas['correlacao'].mean():.3f}", 
         f"{df_metricas['correlacao'].min():.3f}", f"{df_metricas['correlacao'].max():.3f}"]
    ]
    
    table = ax.table(cellText=resumo_texto, cellLoc='center', loc='center',
                     colWidths=[0.3, 0.25, 0.25, 0.25])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Estilizar header
    for i in range(4):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax.set_title('Resumo Estatístico', fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # Salvar figura
    fig_path = METRICAS_DIR / "resumo_geral.png"
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Gráfico resumo salvo: {fig_path.name}")


if __name__ == "__main__":
    df_metricas, df_series = processar_todos_os_meses()




