"""
Backtest: Modelo de Regressão Hidro FD
=======================================

Valida o modelo de regressão usado no mini_dessem para prever
a geração de Hidrelétricas Fio d'água (FD) com base em:
- Geração Hidro Reservatório (R)
- ENA (Energia Natural Afluente)
- Mês, Hora, Dia da Semana

Modelo de Regressão:
FD = intercept + ghr*R + ena*ENA + peso_mes + peso_hora + peso_weekday

Parâmetros (de config.py do mini_dessem):
- intercept: 3563
- ghr: 0.33
- ena: 0.15
- peso_mes: {1: 1944, 2: 2737, ..., 12: 0}
- peso_hora: {0: -166, 1: -197, ..., 23: 0}
- peso_weekday: 1352 (dia útil) ou 1523 (fim de semana)
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
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "backtest_hidro_fd"
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

# ENA por mês (de data.py do mini_dessem)
ENA_dic = {
    2022: {
        1: 105544, 2: 110012, 3: 89199, 4: 74378, 5: 58387, 6: 48373,
        7: 31099, 8: 32696, 9: 29717, 10: 39761, 11: 39089, 12: 69050
    },
    2023: {
        1: 101295, 2: 86123, 3: 82417, 4: 52170, 5: 45686, 6: 38028,
        7: 30073, 8: 32609, 9: 36241, 10: 36241, 11: 41901, 12: 42209
    },
    2024: {
        1: 58303, 2: 74738, 3: 77555, 4: 74854, 5: 53068, 6: 34343,
        7: 31116, 8: 20274, 9: 17603, 10: 23475, 11: 38432, 12: 55908
    },
    2025: {
        1: 74995, 2: 81867, 3: 79098, 4: 66168, 5: 50956, 6: 41144,
        7: 32850, 8: 28908, 9: 28229, 10: 29253, 11: 38913, 12: 56694
    }
}

MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

def calcular_fd_modelo(row):
    """
    Calcula FD previsto pelo modelo de regressão.
    
    Implementação da função calcular_val_gerhidro_fd do mini_dessem.
    """
    mes = int(row['mes'])
    hora = int(row['hora'])
    is_weekday = row['dia_semana'] < 5  # 0-4 = Segunda a Sexta
    val_gerhidro_reservatorio = row['R']
    
    # Buscar ENA para o ano e mês
    ano = int(row['ano'])
    if ano in ENA_dic and mes in ENA_dic[ano]:
        ENA_arm = ENA_dic[ano][mes]
    else:
        # Se não tiver ENA, usar média dos anos disponíveis
        enas_disponiveis = [ENA_dic[a][mes] for a in ENA_dic if mes in ENA_dic[a]]
        ENA_arm = np.mean(enas_disponiveis) if enas_disponiveis else 50000
    
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

def carregar_dados():
    """Carrega dados históricos."""
    
    print("\n" + "="*80)
    print("  CARREGANDO DADOS HISTÓRICOS")
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
    df['hora'] = df['din_instante'].dt.hour
    df['dia_semana'] = df['din_instante'].dt.dayofweek
    
    # Garantir que FD e R sejam numéricos
    df['FD'] = pd.to_numeric(df['FD'], errors='coerce')
    df['R'] = pd.to_numeric(df['R'], errors='coerce')
    
    # Remover valores NaN
    df = df.dropna(subset=['FD', 'R'])
    
    print(f"  [OK] {len(df):,} registros carregados")
    print(f"  Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    print(f"  Anos: {sorted(df['ano'].unique())}")
    
    return df

def aplicar_modelo(df):
    """Aplica modelo de regressão para calcular FD previsto."""
    
    print("\n" + "="*80)
    print("  APLICANDO MODELO DE REGRESSÃO")
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
    fig.suptitle('Backtest: Modelo de Regressão Hidro FD', 
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
    plt.savefig(OUTPUT_DIR / 'backtest_principal.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] backtest_principal.png")

def gerar_analise_detalhada(df):
    """Gera análise detalhada por ano e mês."""
    
    print("\n" + "="*80)
    print("  GERANDO ANÁLISE DETALHADA")
    print("="*80 + "\n")
    
    anos = sorted(df['ano'].unique())
    
    # Figura com heatmaps
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Análise Detalhada: Erro por Hora e Mês', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Heatmap: Erro médio (Hora x Mês)
    ax = axes[0, 0]
    pivot_erro = df.pivot_table(values='erro', index='hora', columns='mes', aggfunc='mean')
    im = ax.imshow(pivot_erro.values, aspect='auto', cmap='RdBu_r', 
                  vmin=-pivot_erro.abs().max().max(), 
                  vmax=pivot_erro.abs().max().max())
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
    ax.set_title('Erro Médio (MW): Hora vs Mês', fontsize=13, fontweight='bold')
    ax.set_xticks(range(12))
    ax.set_xticklabels([MESES_PT[i+1] for i in range(12)])
    ax.set_yticks(range(0, 24, 2))
    ax.set_yticklabels(range(0, 24, 2))
    plt.colorbar(im, ax=ax, label='Erro (MW)')
    
    # 2. Heatmap: MAE (Hora x Mês)
    ax = axes[0, 1]
    pivot_mae = df.pivot_table(values='erro_abs', index='hora', columns='mes', aggfunc='mean')
    im = ax.imshow(pivot_mae.values, aspect='auto', cmap='YlOrRd')
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
    ax.set_title('MAE (MW): Hora vs Mês', fontsize=13, fontweight='bold')
    ax.set_xticks(range(12))
    ax.set_xticklabels([MESES_PT[i+1] for i in range(12)])
    ax.set_yticks(range(0, 24, 2))
    ax.set_yticklabels(range(0, 24, 2))
    plt.colorbar(im, ax=ax, label='MAE (MW)')
    
    # 3. Evolução do erro por ano
    ax = axes[1, 0]
    for ano in anos:
        df_ano = df[df['ano'] == ano]
        # Agregar por mês
        erro_mensal = df_ano.groupby('mes')['erro'].mean()
        ax.plot(erro_mensal.index, erro_mensal.values, 'o-', 
               label=f'{ano}', linewidth=2, markersize=6)
    
    ax.axhline(0, color='black', linestyle='--', linewidth=1)
    ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro Médio (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Evolução do Erro por Ano', fontsize=13, fontweight='bold')
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([MESES_PT[i] for i in range(1, 13)])
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 4. Boxplot de erro por ano
    ax = axes[1, 1]
    data_box = [df[df['ano'] == ano]['erro'].values for ano in anos]
    bp = ax.boxplot(data_box, labels=anos, patch_artist=True, showfliers=False)
    
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    ax.axhline(0, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('Ano', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Distribuição do Erro por Ano', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_detalhada.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] analise_detalhada.png")

def gerar_residuos(df):
    """Analisa resíduos do modelo."""
    
    print("\n" + "="*80)
    print("  ANÁLISE DE RESÍDUOS")
    print("="*80 + "\n")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Análise de Resíduos', fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Resíduos vs Valores previstos
    ax = axes[0, 0]
    df_sample = df.sample(min(50000, len(df)))
    ax.scatter(df_sample['FD_previsto'], df_sample['erro'], alpha=0.3, s=5)
    ax.axhline(0, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('FD Previsto (MW)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Resíduo (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Resíduos vs Valores Previstos', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 2. Resíduos vs R (Hidro Reservatório)
    ax = axes[0, 1]
    ax.scatter(df_sample['R'], df_sample['erro'], alpha=0.3, s=5)
    ax.axhline(0, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('R - Hidro Reservatório (MW)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Resíduo (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Resíduos vs Hidro Reservatório', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 3. Q-Q Plot
    ax = axes[1, 0]
    stats.probplot(df['erro'], dist="norm", plot=ax)
    ax.set_title('Q-Q Plot (Normalidade dos Resíduos)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 4. Autocorrelação dos resíduos (sample)
    ax = axes[1, 1]
    df_autocorr = df.sort_values('din_instante').head(10000)  # Primeiros 10k
    from pandas.plotting import autocorrelation_plot
    autocorrelation_plot(df_autocorr['erro'], ax=ax)
    ax.set_title('Autocorrelação dos Resíduos (primeiros 10k)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'analise_residuos.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] analise_residuos.png")

def gerar_relatorio(df, metricas):
    """Gera relatório em texto."""
    
    print("\n" + "="*80)
    print("  GERANDO RELATÓRIO")
    print("="*80 + "\n")
    
    relatorio = []
    relatorio.append("="*80)
    relatorio.append("BACKTEST: MODELO DE REGRESSÃO HIDRO FD")
    relatorio.append("="*80)
    relatorio.append("")
    
    # Informações do modelo
    relatorio.append("1. MODELO DE REGRESSÃO")
    relatorio.append("-" * 80)
    relatorio.append("FD = intercept + ghr*R + ena*ENA + peso_mes + peso_hora + peso_weekday")
    relatorio.append("")
    relatorio.append("Parâmetros:")
    relatorio.append(f"  intercept:    {REGRESSION_PARAMS['intercept']}")
    relatorio.append(f"  ghr:          {REGRESSION_PARAMS['ghr']} (coef. Hidro Reservatório)")
    relatorio.append(f"  ena:          {REGRESSION_PARAMS['ena']} (coef. ENA)")
    relatorio.append(f"  peso_weekday: {REGRESSION_PARAMS['peso_weekday']} (dia útil)")
    relatorio.append(f"  peso_fds:     {REGRESSION_PARAMS['peso_fds']} (fim de semana)")
    relatorio.append("")
    
    # Dados
    relatorio.append("2. DADOS ANALISADOS")
    relatorio.append("-" * 80)
    relatorio.append(f"Período:          {df['din_instante'].min()} até {df['din_instante'].max()}")
    relatorio.append(f"Total registros:  {len(df):,}")
    relatorio.append(f"Anos:             {', '.join(map(str, sorted(df['ano'].unique())))}")
    relatorio.append("")
    
    # Métricas gerais
    relatorio.append("3. MÉTRICAS DE DESEMPENHO GERAL")
    relatorio.append("-" * 80)
    relatorio.append(f"MAE (Erro Absoluto Médio):      {metricas['mae']:>12,.2f} MW")
    relatorio.append(f"RMSE (Raiz Erro Quadrático):    {metricas['rmse']:>12,.2f} MW")
    relatorio.append(f"MAPE (Erro Percentual Médio):   {metricas['mape']:>12,.2f} %")
    relatorio.append(f"Bias (Viés):                    {metricas['bias']:>12,.2f} MW ({metricas['bias_pct']:+.2f}%)")
    relatorio.append(f"Correlação (R):                 {metricas['corr']:>12,.4f}")
    relatorio.append(f"R²:                             {metricas['r2']:>12,.4f}")
    relatorio.append("")
    
    # Métricas por ano
    relatorio.append("4. MÉTRICAS POR ANO")
    relatorio.append("-" * 80)
    relatorio.append(f"{'Ano':<8} {'MAE (MW)':<15} {'MAPE (%)':<15} {'Bias (MW)':<15} {'R²':<10}")
    relatorio.append("-" * 80)
    for _, row in metricas['metricas_ano'].iterrows():
        relatorio.append(f"{int(row['ano']):<8} {row['mae']:>15,.0f} {row['mape']:>15,.2f} {row['bias']:>15,.0f} {row['r2']:>10,.4f}")
    relatorio.append("")
    
    # Análise de piores casos
    relatorio.append("5. ANÁLISE DE PIORES CASOS (Top 10 Maiores Erros)")
    relatorio.append("-" * 80)
    top_erros = df.nlargest(10, 'erro_abs')[['din_instante', 'FD', 'FD_previsto', 'erro', 'erro_pct']]
    relatorio.append(f"{'Data/Hora':<20} {'FD Real':<12} {'FD Prev.':<12} {'Erro':<12} {'Erro %':<10}")
    relatorio.append("-" * 80)
    for _, row in top_erros.iterrows():
        relatorio.append(f"{str(row['din_instante']):<20} {row['FD']:>12,.0f} {row['FD_previsto']:>12,.0f} "
                        f"{row['erro']:>12,.0f} {row['erro_pct']:>10,.2f}")
    relatorio.append("")
    
    # Conclusões
    relatorio.append("6. CONCLUSOES")
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
    relatorio.append("FIM DO RELATÓRIO")
    relatorio.append("="*80)
    
    # Salvar relatório
    relatorio_texto = '\n'.join(relatorio)
    with open(OUTPUT_DIR / 'RELATORIO_BACKTEST.txt', 'w', encoding='utf-8') as f:
        f.write(relatorio_texto)
    
    print("  [OK] RELATORIO_BACKTEST.txt")
    print("\n" + relatorio_texto)

def main():
    """Função principal."""
    
    print("\n" + "="*80)
    print("  BACKTEST: MODELO DE REGRESSÃO HIDRO FD")
    print("="*80)
    
    # Carregar dados
    df = carregar_dados()
    if df is None:
        return
    
    # Aplicar modelo
    df = aplicar_modelo(df)
    
    # Calcular métricas
    metricas = calcular_metricas(df)
    
    # Gerar análises gráficas
    gerar_graficos_principais(df, metricas)
    gerar_analise_detalhada(df)
    gerar_residuos(df)
    
    # Gerar relatório
    gerar_relatorio(df, metricas)
    
    # Salvar dados processados
    print("\n" + "="*80)
    print("  SALVANDO DADOS PROCESSADOS")
    print("="*80 + "\n")
    
    # Salvar amostra dos dados
    df_export = df[['din_instante', 'ano', 'mes', 'hora', 'dia_semana', 
                     'FD', 'R', 'FD_previsto', 'erro', 'erro_pct']].copy()
    df_export.to_csv(OUTPUT_DIR / 'backtest_dados.csv', index=False)
    print("  [OK] backtest_dados.csv")
    
    # Salvar métricas
    metricas['metricas_ano'].to_csv(OUTPUT_DIR / 'metricas_por_ano.csv', index=False)
    print("  [OK] metricas_por_ano.csv")
    
    print("\n" + "="*80)
    print("  BACKTEST CONCLUÍDO!")
    print("="*80)
    print(f"\nTodos os arquivos salvos em:")
    print(f"  {OUTPUT_DIR}")
    print("\nArquivos gerados:")
    for arquivo in sorted(OUTPUT_DIR.glob('*')):
        print(f"  - {arquivo.name}")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()

