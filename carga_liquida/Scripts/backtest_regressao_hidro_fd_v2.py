"""
Backtest V2: Modelo de Regressao Hidro FD com ENA REAL
========================================================

Versao atualizada usando dados historicos REAIS de ENA diarios
em vez de valores mensais fixos.

Fonte: ENA_HISTORICO.xlsx
Coluna: ena_armazenavel_regiao_mwmed (valores diarios)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configuração visual
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 10

# Diretórios
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
ENA_FILE = MINI_DESSEM_DIR / "Data" / "ENA" / "ENA" / "ENA_HISTORICO.xlsx"
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "backtest_hidro_fd_v2"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# ===== PARÂMETROS DA REGRESSÃO (de config.py) =====
REGRESSION_PARAMS = {
    'intercept': 3563,
    'ghr': 0.33,
    'ena': 0.15,
    'peso_mes': {
        1: 1944, 2: 2737, 3: 4870, 4: 6687, 5: 5241, 6: 2677,
        7: 1062, 8: -467, 9: -1353, 10: -2544, 11: -1036, 12: 0
    },
    'peso_hora': {
        0: -166, 1: -197, 2: -195, 3: -320, 4: -502, 5: -601,
        6: -530, 7: -363, 8: -183, 9: -159, 10: 11, 11: 589,
        12: 998, 13: 1566, 14: 2290, 15: 2961, 16: 3129, 17: 2816,
        18: 2444, 19: 1975, 20: 1449, 21: 704, 22: 275, 23: 0
    },
    'peso_weekday': 1352,
    'peso_fds': 1523
}

MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

def carregar_ena_historico():
    """Carrega dados históricos de ENA."""
    
    print("\n" + "="*80)
    print("  CARREGANDO DADOS DE ENA HISTÓRICO")
    print("="*80 + "\n")
    
    if not ENA_FILE.exists():
        print(f"[ERRO] Arquivo não encontrado: {ENA_FILE}")
        return None
    
    print(f"Carregando: {ENA_FILE.name}")
    df_ena = pd.read_excel(ENA_FILE)
    
    # Renomear colunas
    df_ena['data'] = pd.to_datetime(df_ena['Data'])
    df_ena['ena_mwmed'] = df_ena['ena_armazenavel_regiao_mwmed']
    
    # Criar coluna de data sem hora para merge
    df_ena['data_dia'] = df_ena['data'].dt.date
    
    # Selecionar apenas colunas necessárias
    df_ena = df_ena[['data_dia', 'ena_mwmed']].copy()
    
    print(f"  [OK] {len(df_ena):,} dias de ENA carregados")
    print(f"  Período: {df_ena['data_dia'].min()} até {df_ena['data_dia'].max()}")
    print(f"  ENA médio: {df_ena['ena_mwmed'].mean():,.0f} MWmed")
    print(f"  ENA mín: {df_ena['ena_mwmed'].min():,.0f} MWmed")
    print(f"  ENA máx: {df_ena['ena_mwmed'].max():,.0f} MWmed")
    
    return df_ena

def carregar_dados():
    """Carrega dados históricos de FD e R."""
    
    print("\n" + "="*80)
    print("  CARREGANDO DADOS HISTÓRICOS FD e R")
    print("="*80 + "\n")
    
    path_hist = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
    
    if not path_hist.exists():
        print(f"[ERRO] Arquivo não encontrado: {path_hist}")
        return None
    
    print(f"Carregando: {path_hist.name}")
    df = pd.read_parquet(path_hist)
    
    # Verificar colunas necessárias
    colunas_necessarias = ['din_instante', 'FD', 'R']
    for col in colunas_necessarias:
        if col not in df.columns:
            print(f"[ERRO] Coluna '{col}' não encontrada")
            return None
    
    # Processar dados
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    df['ano'] = df['din_instante'].dt.year
    df['mes'] = df['din_instante'].dt.month
    df['dia'] = df['din_instante'].dt.day
    df['hora'] = df['din_instante'].dt.hour
    df['dia_semana'] = df['din_instante'].dt.dayofweek
    df['data_dia'] = df['din_instante'].dt.date
    
    # Garantir que FD e R sejam numéricos
    df['FD'] = pd.to_numeric(df['FD'], errors='coerce')
    df['R'] = pd.to_numeric(df['R'], errors='coerce')
    
    # Remover valores NaN
    df = df.dropna(subset=['FD', 'R'])
    
    print(f"  [OK] {len(df):,} registros carregados")
    print(f"  Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    print(f"  Anos: {sorted(df['ano'].unique())}")
    
    return df

def merge_com_ena(df, df_ena):
    """Faz merge dos dados de FD/R com ENA."""
    
    print("\n" + "="*80)
    print("  FAZENDO MERGE COM ENA REAL")
    print("="*80 + "\n")
    
    print(f"Registros antes do merge: {len(df):,}")
    
    # Merge por data
    df_merged = pd.merge(df, df_ena, on='data_dia', how='left')
    
    # Verificar quantos registros têm ENA
    sem_ena = df_merged['ena_mwmed'].isna().sum()
    com_ena = (~df_merged['ena_mwmed'].isna()).sum()
    
    print(f"Registros após merge:")
    print(f"  Com ENA:    {com_ena:,} ({com_ena/len(df_merged)*100:.1f}%)")
    print(f"  Sem ENA:    {sem_ena:,} ({sem_ena/len(df_merged)*100:.1f}%)")
    
    # Remover registros sem ENA
    if sem_ena > 0:
        print(f"\n[AVISO] Removendo {sem_ena:,} registros sem dados de ENA")
        df_merged = df_merged.dropna(subset=['ena_mwmed'])
    
    print(f"\n  [OK] {len(df_merged):,} registros com ENA para análise")
    
    return df_merged

def calcular_fd_modelo(row):
    """
    Calcula FD previsto pelo modelo de regressão usando ENA REAL.
    """
    mes = int(row['mes'])
    hora = int(row['hora'])
    is_weekday = row['dia_semana'] < 5  # 0-4 = Segunda a Sexta
    val_gerhidro_reservatorio = row['R']
    ENA_arm = row['ena_mwmed']  # <- USANDO ENA REAL!
    
    # Parâmetros da regressão
    intercept = REGRESSION_PARAMS['intercept']
    ghr = REGRESSION_PARAMS['ghr']
    ena = REGRESSION_PARAMS['ena']
    peso_mes = REGRESSION_PARAMS['peso_mes'][mes]
    peso_hora = REGRESSION_PARAMS['peso_hora'][hora]
    peso_weekday = REGRESSION_PARAMS['peso_weekday'] if is_weekday else REGRESSION_PARAMS['peso_fds']
    
    # Regressão linear
    fd_previsto = (
        intercept +
        ghr * val_gerhidro_reservatorio +
        ena * ENA_arm +
        peso_mes +
        peso_hora +
        peso_weekday
    )
    
    return fd_previsto

def aplicar_modelo(df):
    """Aplica modelo de regressão para calcular FD previsto."""
    
    print("\n" + "="*80)
    print("  APLICANDO MODELO DE REGRESSÃO COM ENA REAL")
    print("="*80 + "\n")
    
    print("Calculando FD previsto para cada registro...")
    df['FD_previsto'] = df.apply(calcular_fd_modelo, axis=1)
    
    # Calcular erros
    df['erro'] = df['FD_previsto'] - df['FD']
    df['erro_abs'] = df['erro'].abs()
    df['erro_pct'] = (df['erro'] / df['FD']) * 100
    df['erro_pct_abs'] = df['erro_pct'].abs()
    
    print(f"  [OK] Modelo aplicado em {len(df):,} registros")
    
    return df

def calcular_metricas(df):
    """Calcula métricas de desempenho do modelo."""
    
    print("\n" + "="*80)
    print("  MÉTRICAS DE DESEMPENHO")
    print("="*80 + "\n")
    
    # Métricas gerais
    mae = df['erro_abs'].mean()
    rmse = np.sqrt((df['erro']**2).mean())
    mape = df['erro_pct_abs'].mean()
    bias = df['erro'].mean()
    bias_pct = (bias / df['FD'].mean()) * 100
    
    # Correlação
    corr = df['FD'].corr(df['FD_previsto'])
    r2 = corr ** 2
    
    print(f"Erro Absoluto Médio (MAE):     {mae:>12,.2f} MW")
    print(f"Raiz do Erro Quadrático (RMSE): {rmse:>12,.2f} MW")
    print(f"Erro Percentual Médio (MAPE):   {mape:>12,.2f} %")
    print(f"Viés (Bias):                    {bias:>12,.2f} MW ({bias_pct:+.2f}%)")
    print(f"Correlação (R):                 {corr:>12,.4f}")
    print(f"R²:                             {r2:>12,.4f}")
    
    # Métricas por ano
    print(f"\n{'ANO':<8} {'MAE (MW)':<12} {'MAPE (%)':<12} {'Bias (MW)':<12} {'R²':<8}")
    print("-" * 60)
    
    metricas_ano = []
    for ano in sorted(df['ano'].unique()):
        df_ano = df[df['ano'] == ano]
        mae_ano = df_ano['erro_abs'].mean()
        mape_ano = df_ano['erro_pct_abs'].mean()
        bias_ano = df_ano['erro'].mean()
        r2_ano = df_ano['FD'].corr(df_ano['FD_previsto']) ** 2
        
        metricas_ano.append({
            'ano': ano,
            'mae': mae_ano,
            'mape': mape_ano,
            'bias': bias_ano,
            'r2': r2_ano
        })
        
        print(f"{ano:<8} {mae_ano:>12,.0f} {mape_ano:>12,.2f} {bias_ano:>12,.0f} {r2_ano:>8,.4f}")
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'bias': bias,
        'bias_pct': bias_pct,
        'corr': corr,
        'r2': r2,
        'metricas_ano': pd.DataFrame(metricas_ano)
    }

def gerar_graficos_principais(df, metricas):
    """Gera gráficos principais de validação."""
    
    print("\n" + "="*80)
    print("  GERANDO GRÁFICOS PRINCIPAIS")
    print("="*80 + "\n")
    
    # Figura com 4 subplots
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    fig.suptitle('Backtest V2: Modelo de Regressão Hidro FD (com ENA REAL)', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Scatter: Real vs Previsto
    ax = axes[0, 0]
    
    # Sample para não sobrecarregar
    df_sample = df.sample(min(50000, len(df)))
    ax.scatter(df_sample['FD'], df_sample['FD_previsto'], 
              alpha=0.3, s=5, c=df_sample['ano'], cmap='viridis')
    
    # Linha x=y
    lim_min = min(df['FD'].min(), df['FD_previsto'].min())
    lim_max = max(df['FD'].max(), df['FD_previsto'].max())
    ax.plot([lim_min, lim_max], [lim_min, lim_max], 'r--', linewidth=2, label='y=x', alpha=0.7)
    
    # Estatísticas
    ax.text(0.05, 0.95, 
           f"R² = {metricas['r2']:.4f}\nMAE = {metricas['mae']:,.0f} MW\nBias = {metricas['bias']:+,.0f} MW",
           transform=ax.transAxes, fontsize=11,
           verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.set_xlabel('FD Real (MW)', fontsize=12, fontweight='bold')
    ax.set_ylabel('FD Previsto (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Real vs Previsto', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 2. Distribuição do erro
    ax = axes[0, 1]
    ax.hist(df['erro'], bins=100, alpha=0.7, color='steelblue', edgecolor='black')
    ax.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero')
    ax.axvline(metricas['bias'], color='green', linestyle='--', linewidth=2,
              label=f"Bias = {metricas['bias']:,.0f} MW")
    
    ax.set_xlabel('Erro (Previsto - Real) [MW]', fontsize=12, fontweight='bold')
    ax.set_ylabel('Frequência', fontsize=12, fontweight='bold')
    ax.set_title('Distribuição do Erro', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3. Erro por hora do dia
    ax = axes[1, 0]
    erro_hora = df.groupby('hora').agg({
        'erro': 'mean',
        'erro_abs': 'mean'
    }).reset_index()
    
    ax.bar(erro_hora['hora'], erro_hora['erro'], alpha=0.7, 
          color=['red' if e < 0 else 'green' for e in erro_hora['erro']],
          edgecolor='black')
    ax.axhline(0, color='black', linewidth=1)
    
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro Médio (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro Médio por Hora', fontsize=13, fontweight='bold')
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. Erro por mês
    ax = axes[1, 1]
    erro_mes = df.groupby('mes').agg({
        'erro': 'mean',
        'erro_abs': 'mean'
    }).reset_index()
    
    ax.bar(erro_mes['mes'], erro_mes['erro'], alpha=0.7,
          color=['red' if e < 0 else 'green' for e in erro_mes['erro']],
          edgecolor='black')
    ax.axhline(0, color='black', linewidth=1)
    
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro Médio (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro Médio por Mês', fontsize=13, fontweight='bold')
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([MESES_PT[i] for i in range(1, 13)])
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'backtest_principal_v2.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] backtest_principal_v2.png")

def gerar_analise_ena(df):
    """Gera análise específica do impacto de ENA."""
    
    print("\n" + "="*80)
    print("  ANÁLISE DO IMPACTO DE ENA")
    print("="*80 + "\n")
    
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Análise do Impacto de ENA no Modelo', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Scatter: ENA vs Erro
    ax = axes[0, 0]
    df_sample = df.sample(min(20000, len(df)))
    scatter = ax.scatter(df_sample['ena_mwmed'], df_sample['erro'], 
                        alpha=0.3, s=10, c=df_sample['ano'], cmap='viridis')
    ax.axhline(0, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('ENA (MWmed)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro vs ENA', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax, label='Ano')
    
    # 2. Boxplot: Erro por faixa de ENA
    ax = axes[0, 1]
    df['faixa_ena'] = pd.qcut(df['ena_mwmed'], q=5, labels=['Muito Baixa', 'Baixa', 'Média', 'Alta', 'Muito Alta'])
    df.boxplot(column='erro', by='faixa_ena', ax=ax, showfliers=False)
    ax.axhline(0, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('Faixa de ENA', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Distribuição do Erro por Faixa de ENA', fontsize=13, fontweight='bold')
    plt.suptitle('')  # Remover título automático do boxplot
    
    # 3. Série temporal: ENA ao longo do tempo
    ax = axes[1, 0]
    df_diario = df.groupby('data_dia').agg({
        'ena_mwmed': 'mean',
        'erro': 'mean'
    }).reset_index()
    df_diario['data_dia'] = pd.to_datetime(df_diario['data_dia'])
    
    ax.plot(df_diario['data_dia'], df_diario['ena_mwmed'], linewidth=1, alpha=0.7)
    ax.set_xlabel('Data', fontsize=12, fontweight='bold')
    ax.set_ylabel('ENA (MWmed)', fontsize=12, fontweight='bold')
    ax.set_title('Série Temporal de ENA', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 4. Correlação ENA vs componentes
    ax = axes[1, 1]
    
    correlacoes = {
        'FD Real': df['FD'].corr(df['ena_mwmed']),
        'R (Reserv.)': df['R'].corr(df['ena_mwmed']),
        'FD Previsto': df['FD_previsto'].corr(df['ena_mwmed']),
        'Erro': df['erro'].corr(df['ena_mwmed'])
    }
    
    x_pos = np.arange(len(correlacoes))
    colors = ['green' if v > 0 else 'red' for v in correlacoes.values()]
    bars = ax.bar(x_pos, list(correlacoes.values()), color=colors, alpha=0.7, edgecolor='black')
    
    # Adicionar valores
    for i, (bar, val) in enumerate(zip(bars, correlacoes.values())):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{val:.3f}', ha='center', 
               va='bottom' if height > 0 else 'top', fontsize=10)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(list(correlacoes.keys()), rotation=15, ha='right')
    ax.set_ylabel('Correlação', fontsize=12, fontweight='bold')
    ax.set_title('Correlação de ENA com Componentes', fontsize=13, fontweight='bold')
    ax.axhline(0, color='black', linewidth=1)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(-1, 1)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_impacto_ena.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] analise_impacto_ena.png")

def gerar_comparacao_versoes(df):
    """Gera comparação entre V1 (ENA mensal) e V2 (ENA real)."""
    
    print("\n" + "="*80)
    print("  GERANDO COMPARAÇÃO V1 vs V2")
    print("="*80 + "\n")
    
    # Carregar resultados V1 se existir
    v1_dir = CARGA_LIQ_DIR / "Output" / "backtest_hidro_fd"
    v1_metricas_file = v1_dir / "metricas_por_ano.csv"
    
    if v1_metricas_file.exists():
        df_v1 = pd.read_csv(v1_metricas_file)
        
        # Métricas V2
        metricas_v2 = []
        for ano in sorted(df['ano'].unique()):
            df_ano = df[df['ano'] == ano]
            metricas_v2.append({
                'ano': ano,
                'mae': df_ano['erro_abs'].mean(),
                'mape': df_ano['erro_pct_abs'].mean(),
                'r2': df_ano['FD'].corr(df_ano['FD_previsto']) ** 2
            })
        df_v2 = pd.DataFrame(metricas_v2)
        
        # Gráfico comparativo
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('Comparação: V1 (ENA Mensal) vs V2 (ENA Real)', 
                     fontsize=16, fontweight='bold')
        
        anos = sorted(df['ano'].unique())
        x = np.arange(len(anos))
        width = 0.35
        
        # MAE
        ax = axes[0]
        bars1 = ax.bar(x - width/2, df_v1['mae'], width, label='V1 (ENA Mensal)', 
                      alpha=0.8, color='lightcoral', edgecolor='black')
        bars2 = ax.bar(x + width/2, df_v2['mae'], width, label='V2 (ENA Real)', 
                      alpha=0.8, color='lightgreen', edgecolor='black')
        ax.set_xlabel('Ano', fontsize=12, fontweight='bold')
        ax.set_ylabel('MAE (MW)', fontsize=12, fontweight='bold')
        ax.set_title('Erro Absoluto Médio', fontsize=13, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(anos)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # MAPE
        ax = axes[1]
        bars1 = ax.bar(x - width/2, df_v1['mape'], width, label='V1 (ENA Mensal)', 
                      alpha=0.8, color='lightcoral', edgecolor='black')
        bars2 = ax.bar(x + width/2, df_v2['mape'], width, label='V2 (ENA Real)', 
                      alpha=0.8, color='lightgreen', edgecolor='black')
        ax.set_xlabel('Ano', fontsize=12, fontweight='bold')
        ax.set_ylabel('MAPE (%)', fontsize=12, fontweight='bold')
        ax.set_title('Erro Percentual Médio', fontsize=13, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(anos)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # R²
        ax = axes[2]
        bars1 = ax.bar(x - width/2, df_v1['r2'], width, label='V1 (ENA Mensal)', 
                      alpha=0.8, color='lightcoral', edgecolor='black')
        bars2 = ax.bar(x + width/2, df_v2['r2'], width, label='V2 (ENA Real)', 
                      alpha=0.8, color='lightgreen', edgecolor='black')
        ax.set_xlabel('Ano', fontsize=12, fontweight='bold')
        ax.set_ylabel('R²', fontsize=12, fontweight='bold')
        ax.set_title('Coeficiente de Determinação', fontsize=13, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(anos)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'comparacao_v1_v2.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  [OK] comparacao_v1_v2.png")
    else:
        print("  [AVISO] Resultados V1 não encontrados, pulando comparação")

def gerar_relatorio(df, metricas):
    """Gera relatório em texto."""
    
    print("\n" + "="*80)
    print("  GERANDO RELATÓRIO V2")
    print("="*80 + "\n")
    
    relatorio = []
    relatorio.append("="*80)
    relatorio.append("BACKTEST V2: MODELO DE REGRESSAO HIDRO FD (COM ENA REAL)")
    relatorio.append("="*80)
    relatorio.append("")
    
    relatorio.append("DIFERENCA PARA V1:")
    relatorio.append("  V1: Usava valores mensais FIXOS de ENA")
    relatorio.append("  V2: Usa valores DIARIOS REAIS de ENA")
    relatorio.append("")
    
    # Modelo
    relatorio.append("1. MODELO DE REGRESSAO")
    relatorio.append("-" * 80)
    relatorio.append("FD = intercept + ghr*R + ena*ENA + peso_mes + peso_hora + peso_weekday")
    relatorio.append("")
    
    # Dados
    relatorio.append("2. DADOS ANALISADOS")
    relatorio.append("-" * 80)
    relatorio.append(f"Periodo:          {df['din_instante'].min()} ate {df['din_instante'].max()}")
    relatorio.append(f"Total registros:  {len(df):,}")
    relatorio.append(f"Anos:             {', '.join(map(str, sorted(df['ano'].unique())))}")
    relatorio.append(f"ENA medio:        {df['ena_mwmed'].mean():,.0f} MWmed")
    relatorio.append(f"ENA min:          {df['ena_mwmed'].min():,.0f} MWmed")
    relatorio.append(f"ENA max:          {df['ena_mwmed'].max():,.0f} MWmed")
    relatorio.append("")
    
    # Métricas gerais
    relatorio.append("3. METRICAS DE DESEMPENHO GERAL")
    relatorio.append("-" * 80)
    relatorio.append(f"MAE (Erro Absoluto Medio):      {metricas['mae']:>12,.2f} MW")
    relatorio.append(f"RMSE (Raiz Erro Quadratico):    {metricas['rmse']:>12,.2f} MW")
    relatorio.append(f"MAPE (Erro Percentual Medio):   {metricas['mape']:>12,.2f} %")
    relatorio.append(f"Bias (Vies):                    {metricas['bias']:>12,.2f} MW ({metricas['bias_pct']:+.2f}%)")
    relatorio.append(f"Correlacao (R):                 {metricas['corr']:>12,.4f}")
    relatorio.append(f"R2:                             {metricas['r2']:>12,.4f}")
    relatorio.append("")
    
    # Métricas por ano
    relatorio.append("4. METRICAS POR ANO")
    relatorio.append("-" * 80)
    relatorio.append(f"{'Ano':<8} {'MAE (MW)':<15} {'MAPE (%)':<15} {'Bias (MW)':<15} {'R2':<10}")
    relatorio.append("-" * 80)
    for _, row in metricas['metricas_ano'].iterrows():
        relatorio.append(f"{int(row['ano']):<8} {row['mae']:>15,.0f} {row['mape']:>15,.2f} {row['bias']:>15,.0f} {row['r2']:>10,.4f}")
    relatorio.append("")
    
    # Conclusões
    relatorio.append("5. CONCLUSOES")
    relatorio.append("-" * 80)
    
    if metricas['r2'] > 0.7:
        relatorio.append("[OK] MODELO BOM: R2 > 0.7 indica boa capacidade preditiva")
    elif metricas['r2'] > 0.5:
        relatorio.append("[!] MODELO MODERADO: R2 entre 0.5-0.7 indica capacidade preditiva moderada")
    else:
        relatorio.append("[X] MODELO FRACO: R2 < 0.5 indica baixa capacidade preditiva")
    
    if abs(metricas['bias_pct']) < 5:
        relatorio.append("[OK] VIES BAIXO: Bias < 5% indica modelo bem calibrado")
    elif abs(metricas['bias_pct']) < 10:
        relatorio.append("[!] VIES MODERADO: Bias entre 5-10% - considerar recalibracao")
    else:
        relatorio.append("[X] VIES ALTO: Bias > 10% - modelo necessita recalibracao")
    
    if metricas['mape'] < 10:
        relatorio.append("[OK] MAPE EXCELENTE: Erro percentual < 10%")
    elif metricas['mape'] < 20:
        relatorio.append("[!] MAPE BOM: Erro percentual entre 10-20%")
    else:
        relatorio.append("[!] MAPE ALTO: Erro percentual > 20% - verificar outliers")
    
    relatorio.append("")
    relatorio.append("="*80)
    relatorio.append("FIM DO RELATORIO")
    relatorio.append("="*80)
    
    # Salvar relatório
    relatorio_texto = '\n'.join(relatorio)
    with open(OUTPUT_DIR / 'RELATORIO_BACKTEST_V2.txt', 'w', encoding='utf-8') as f:
        f.write(relatorio_texto)
    
    print("  [OK] RELATORIO_BACKTEST_V2.txt")
    print("\n" + relatorio_texto)

def main():
    """Função principal."""
    
    print("\n" + "="*80)
    print("  BACKTEST V2: MODELO COM ENA REAL")
    print("="*80)
    
    # Carregar dados
    df_ena = carregar_ena_historico()
    if df_ena is None:
        return
    
    df = carregar_dados()
    if df is None:
        return
    
    # Merge com ENA
    df = merge_com_ena(df, df_ena)
    
    # Aplicar modelo
    df = aplicar_modelo(df)
    
    # Calcular métricas
    metricas = calcular_metricas(df)
    
    # Gerar análises gráficas
    gerar_graficos_principais(df, metricas)
    gerar_analise_ena(df)
    gerar_comparacao_versoes(df)
    
    # Gerar relatório
    gerar_relatorio(df, metricas)
    
    # Salvar dados processados
    print("\n" + "="*80)
    print("  SALVANDO DADOS PROCESSADOS")
    print("="*80 + "\n")
    
    # Salvar amostra dos dados
    df_export = df[['din_instante', 'ano', 'mes', 'hora', 'dia_semana', 
                     'FD', 'R', 'ena_mwmed', 'FD_previsto', 'erro', 'erro_pct']].copy()
    df_export.to_csv(OUTPUT_DIR / 'backtest_dados_v2.csv', index=False)
    print("  [OK] backtest_dados_v2.csv")
    
    # Salvar métricas
    metricas['metricas_ano'].to_csv(OUTPUT_DIR / 'metricas_por_ano_v2.csv', index=False)
    print("  [OK] metricas_por_ano_v2.csv")
    
    print("\n" + "="*80)
    print("  BACKTEST V2 CONCLUÍDO!")
    print("="*80)
    print(f"\nTodos os arquivos salvos em:")
    print(f"  {OUTPUT_DIR}")
    print("\nArquivos gerados:")
    for arquivo in sorted(OUTPUT_DIR.glob('*')):
        print(f"  - {arquivo.name}")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()

