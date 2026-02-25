"""
Backtest de Perfis Horários Solares
====================================

Valida a qualidade dos perfis gerados comparando com dados históricos.

Objetivo: Avaliar se o perfil horário médio representa bem os dias reais.

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

# Configurar estilo dos gráficos
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Definir diretórios
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
DATA_PATH = BASE_DIR / "output" / "curtailment" / "solar" / "comparacao_perfil_curtailment" / "por_mes" / "perfil_hora_por_mes.csv"
BACKTEST_DIR = BASE_DIR / "output" / "sample" / "solar" / "backtest"
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)


def calcular_metricas(real: np.ndarray, previsto: np.ndarray) -> dict:
    """
    Calcula métricas de erro entre perfis horários
    
    Args:
        real: Perfil horário real (24 valores)
        previsto: Perfil horário previsto pelo modelo (24 valores)
    
    Returns:
        Dicionário com métricas
    """
    # MAE e RMSE em todas as horas
    mae = np.mean(np.abs(real - previsto))
    rmse = np.sqrt(np.mean((real - previsto) ** 2))
    
    # MAPE apenas nas horas de geração significativa (> 100 MWh)
    # Evita divisão por valores muito pequenos (noites)
    mask = real > 100
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
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
        'correlacao': correlacao
    }


def realizar_backtest():
    """
    Realiza backtest comparando perfis do modelo com dados reais
    
    Para cada mês histórico:
    1. Calcula MWmédios real daquele mês
    2. Gera perfil usando o modelo
    3. Compara com perfil real (média horária dos dias do mês)
    4. Calcula métricas de erro
    """
    print("="*70)
    print("BACKTEST - PERFIS HORÁRIOS SOLARES")
    print("="*70)
    
    # Carregar dados históricos
    print("\n[1/6] Carregando dados históricos...")
    df_real = pd.read_csv(DATA_PATH)
    df_real['mes'] = pd.to_datetime(df_real['mes'])
    df_real['mes_num'] = df_real['mes'].dt.month
    df_real['ano'] = df_real['mes'].dt.year
    
    print(f"  ✓ {len(df_real)} registros carregados")
    print(f"  ✓ {df_real['mes'].nunique()} meses únicos")
    print(f"  ✓ Período: {df_real['mes'].min().strftime('%Y-%m')} a {df_real['mes'].max().strftime('%Y-%m')}")
    
    # Criar sampler
    print("\n[2/6] Inicializando sampler...")
    sampler = SolarSampler()
    print("  ✓ Sampler inicializado com perfis médios")
    
    # Gerar previsões para cada mês histórico
    print("\n[3/6] Gerando previsões e comparando com dados reais...")
    print("  " + "-"*66)
    
    resultados = []
    
    for mes_data, grupo in df_real.groupby('mes'):
        ano = mes_data.year
        mes = mes_data.month
        
        # Perfil real: média horária dos dias deste mês específico
        # Os dados já são médias diárias por hora
        perfil_real = grupo.set_index('hora')['potencial_total_mwh_media'].values
        
        # Calcular MWmédios deste mês
        n_dias = pd.Period(f'{ano}-{mes:02d}').days_in_month
        total_mensal = perfil_real.sum() * n_dias  # média diária × n_dias
        n_horas = n_dias * 24
        mw_medios = total_mensal / n_horas
        
        # Gerar perfil previsto pelo modelo
        perfil_previsto = sampler.gerar_perfil_dia(mes, mw_medios)
        
        # Calcular métricas
        metricas = calcular_metricas(perfil_real, perfil_previsto)
        
        resultados.append({
            'ano': ano,
            'mes': mes,
            'mes_data': mes_data,
            'mw_medios': mw_medios,
            'total_real_mwh': perfil_real.sum(),
            'total_previsto_mwh': perfil_previsto.sum(),
            **metricas
        })
        
        # Printar resultado
        status = "✓" if metricas['mape'] < 10 else "⚠"
        print(f"  {status} {mes_data.strftime('%Y-%m')}: "
              f"MAE={metricas['mae']:>7.1f} MWh, "
              f"MAPE={metricas['mape']:>5.2f}%, "
              f"R²={metricas['r2']:>6.3f}, "
              f"Corr={metricas['correlacao']:>6.3f}")
    
    df_resultados = pd.DataFrame(resultados)
    
    # Métricas agregadas
    print("\n[4/6] Métricas Agregadas:")
    print("  " + "-"*66)
    print(f"  MAE médio:         {df_resultados['mae'].mean():>10.2f} MWh")
    print(f"  RMSE médio:        {df_resultados['rmse'].mean():>10.2f} MWh")
    print(f"  MAPE médio:        {df_resultados['mape'].mean():>10.2f}%")
    print(f"  R² médio:          {df_resultados['r2'].mean():>10.3f}")
    print(f"  Correlação média:  {df_resultados['correlacao'].mean():>10.3f}")
    
    # Estatísticas por mês do ano
    print("\n[5/6] Métricas por Mês do Ano:")
    print("  " + "-"*66)
    metricas_por_mes = df_resultados.groupby('mes').agg({
        'mae': 'mean',
        'mape': 'mean',
        'r2': 'mean'
    }).round(2)
    
    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    for mes_num in sorted(metricas_por_mes.index):
        row = metricas_por_mes.loc[mes_num]
        print(f"  {meses_nomes[mes_num-1]:3s}: "
              f"MAE={row['mae']:>7.1f} MWh, "
              f"MAPE={row['mape']:>5.2f}%, "
              f"R²={row['r2']:>6.3f}")
    
    # Salvar métricas
    metricas_file = BACKTEST_DIR / "metricas_backtest.csv"
    df_resultados.to_csv(metricas_file, index=False)
    print(f"\n  ✓ Métricas salvas em: {metricas_file}")
    
    # Gerar visualizações
    print("\n[6/6] Gerando visualizações...")
    criar_graficos_backtest(df_real, df_resultados, sampler)
    
    # Classificação da qualidade
    mape_medio = df_resultados['mape'].mean()
    print("\n" + "="*70)
    print("BACKTEST CONCLUÍDO!")
    print("="*70)
    print(f"\n📊 Resumo Final:")
    print(f"   MAPE médio: {mape_medio:.2f}%")
    print(f"   R² médio: {df_resultados['r2'].mean():.3f}")
    print(f"   Correlação média: {df_resultados['correlacao'].mean():.3f}")
    
    if mape_medio < 5:
        print("\n   ✅ Qualidade EXCELENTE (MAPE < 5%)")
    elif mape_medio < 10:
        print("\n   ✅ Qualidade MUITO BOA (MAPE < 10%)")
    elif mape_medio < 20:
        print("\n   ⚠️  Qualidade BOA (MAPE < 20%)")
    else:
        print("\n   ⚠️  Qualidade RAZOÁVEL (MAPE >= 20%)")
    
    return df_resultados


def criar_graficos_backtest(df_real, df_metricas, sampler):
    """
    Cria visualizações do backtest
    """
    fig = plt.figure(figsize=(20, 14))
    
    # 1. MAPE ao longo do tempo
    ax1 = plt.subplot(3, 3, 1)
    ax1.plot(df_metricas['mes_data'], df_metricas['mape'], 'o-', 
             linewidth=2, markersize=6, color='steelblue')
    ax1.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='Limite 10%')
    ax1.axhline(y=df_metricas['mape'].mean(), color='red', linestyle='--', 
                alpha=0.5, label=f'Média: {df_metricas["mape"].mean():.2f}%')
    ax1.set_title('MAPE ao Longo do Tempo', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Mês')
    ax1.set_ylabel('MAPE (%)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Distribuição do MAPE
    ax2 = plt.subplot(3, 3, 2)
    ax2.hist(df_metricas['mape'], bins=15, color='steelblue', 
             edgecolor='black', alpha=0.7)
    ax2.axvline(x=df_metricas['mape'].mean(), color='red', 
                linestyle='--', linewidth=2, 
                label=f'Média: {df_metricas["mape"].mean():.2f}%')
    ax2.set_title('Distribuição do MAPE', fontsize=12, fontweight='bold')
    ax2.set_xlabel('MAPE (%)')
    ax2.set_ylabel('Frequência')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 3. R² ao longo do tempo
    ax3 = plt.subplot(3, 3, 3)
    ax3.plot(df_metricas['mes_data'], df_metricas['r2'], 'o-', 
             linewidth=2, markersize=6, color='green')
    ax3.axhline(y=df_metricas['r2'].mean(), color='red', 
                linestyle='--', alpha=0.5,
                label=f'Média: {df_metricas["r2"].mean():.3f}')
    ax3.set_title('R² ao Longo do Tempo', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Mês')
    ax3.set_ylabel('R²')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Comparação de perfis - Exemplo de mês bom
    ax4 = plt.subplot(3, 3, 4)
    
    # Pegar mês com menor MAPE
    idx_melhor = df_metricas['mape'].idxmin()
    melhor_mes = df_metricas.loc[idx_melhor]
    
    grupo_melhor = df_real[df_real['mes'] == melhor_mes['mes_data']]
    perfil_real_melhor = grupo_melhor.set_index('hora')['potencial_total_mwh_media'].values
    perfil_prev_melhor = sampler.gerar_perfil_dia(melhor_mes['mes'], melhor_mes['mw_medios'])
    
    ax4.plot(range(24), perfil_real_melhor, 'o-', linewidth=2, 
             label='Real', markersize=6, color='blue')
    ax4.plot(range(24), perfil_prev_melhor, 's--', linewidth=2, 
             label='Modelo', markersize=6, color='orange', alpha=0.8)
    ax4.set_title(f'Melhor Ajuste: {melhor_mes["mes_data"].strftime("%Y-%m")} '
                  f'(MAPE={melhor_mes["mape"]:.2f}%)', 
                  fontsize=12, fontweight='bold')
    ax4.set_xlabel('Hora do Dia')
    ax4.set_ylabel('Geração (MWh)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(range(0, 24, 2))
    
    # 5. Comparação de perfis - Exemplo de mês com maior erro
    ax5 = plt.subplot(3, 3, 5)
    
    idx_pior = df_metricas['mape'].idxmax()
    pior_mes = df_metricas.loc[idx_pior]
    
    grupo_pior = df_real[df_real['mes'] == pior_mes['mes_data']]
    perfil_real_pior = grupo_pior.set_index('hora')['potencial_total_mwh_media'].values
    perfil_prev_pior = sampler.gerar_perfil_dia(pior_mes['mes'], pior_mes['mw_medios'])
    
    ax5.plot(range(24), perfil_real_pior, 'o-', linewidth=2, 
             label='Real', markersize=6, color='blue')
    ax5.plot(range(24), perfil_prev_pior, 's--', linewidth=2, 
             label='Modelo', markersize=6, color='orange', alpha=0.8)
    ax5.set_title(f'Maior Erro: {pior_mes["mes_data"].strftime("%Y-%m")} '
                  f'(MAPE={pior_mes["mape"]:.2f}%)', 
                  fontsize=12, fontweight='bold')
    ax5.set_xlabel('Hora do Dia')
    ax5.set_ylabel('Geração (MWh)')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    ax5.set_xticks(range(0, 24, 2))
    
    # 6. Correlação Real vs Previsto (scatter)
    ax6 = plt.subplot(3, 3, 6)
    
    # Juntar todos os valores reais e previstos
    todos_reais = []
    todos_previstos = []
    
    for _, row in df_metricas.iterrows():
        grupo = df_real[df_real['mes'] == row['mes_data']]
        perfil_real = grupo.set_index('hora')['potencial_total_mwh_media'].values
        perfil_prev = sampler.gerar_perfil_dia(row['mes'], row['mw_medios'])
        
        todos_reais.extend(perfil_real)
        todos_previstos.extend(perfil_prev)
    
    ax6.scatter(todos_reais, todos_previstos, alpha=0.5, s=20)
    
    # Linha de referência (perfeito)
    min_val = min(min(todos_reais), min(todos_previstos))
    max_val = max(max(todos_reais), max(todos_previstos))
    ax6.plot([min_val, max_val], [min_val, max_val], 'r--', 
             linewidth=2, label='Ajuste Perfeito')
    
    ax6.set_title('Real vs Previsto (Todos os Valores)', 
                  fontsize=12, fontweight='bold')
    ax6.set_xlabel('Real (MWh)')
    ax6.set_ylabel('Previsto (MWh)')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    # 7. Métricas por mês do ano
    ax7 = plt.subplot(3, 3, 7)
    
    metricas_por_mes = df_metricas.groupby('mes')[['mape']].mean()
    
    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    x = list(metricas_por_mes.index)
    y = metricas_por_mes['mape'].values
    colors = plt.cm.RdYlGn_r(y / max(y))  # Vermelho = erro alto
    
    ax7.bar(x, y, color=colors, edgecolor='black', alpha=0.7)
    ax7.axhline(y=10, color='orange', linestyle='--', alpha=0.5)
    ax7.set_title('MAPE por Mês do Ano', fontsize=12, fontweight='bold')
    ax7.set_xlabel('Mês')
    ax7.set_ylabel('MAPE (%)')
    ax7.set_xticks(x)
    ax7.set_xticklabels([meses_nomes[m-1] for m in x], rotation=45)
    ax7.grid(True, alpha=0.3, axis='y')
    
    # 8. Erro absoluto médio por hora do dia
    ax8 = plt.subplot(3, 3, 8)
    
    erros_por_hora = np.zeros(24)
    n_meses = 0
    
    for _, row in df_metricas.iterrows():
        grupo = df_real[df_real['mes'] == row['mes_data']]
        perfil_real = grupo.set_index('hora')['potencial_total_mwh_media'].values
        perfil_prev = sampler.gerar_perfil_dia(row['mes'], row['mw_medios'])
        
        erros_por_hora += np.abs(perfil_real - perfil_prev)
        n_meses += 1
    
    erros_por_hora /= n_meses
    
    ax8.bar(range(24), erros_por_hora, color='coral', 
            edgecolor='darkred', alpha=0.7)
    ax8.set_title('Erro Absoluto Médio por Hora', fontsize=12, fontweight='bold')
    ax8.set_xlabel('Hora do Dia')
    ax8.set_ylabel('MAE (MWh)')
    ax8.grid(True, alpha=0.3, axis='y')
    ax8.set_xticks(range(0, 24, 2))
    
    # 9. Boxplot de MAPE por mês do ano
    ax9 = plt.subplot(3, 3, 9)
    
    dados_boxplot = [df_metricas[df_metricas['mes'] == m]['mape'].values 
                     for m in range(1, 13) if m in df_metricas['mes'].values]
    labels_boxplot = [meses_nomes[m-1] for m in range(1, 13) 
                      if m in df_metricas['mes'].values]
    
    bp = ax9.boxplot(dados_boxplot, labels=labels_boxplot, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
    
    ax9.set_title('Distribuição de MAPE por Mês', fontsize=12, fontweight='bold')
    ax9.set_xlabel('Mês')
    ax9.set_ylabel('MAPE (%)')
    ax9.grid(True, alpha=0.3, axis='y')
    plt.setp(ax9.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # Salvar figura
    fig_path = BACKTEST_DIR / "backtest_perfis_solares.png"
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Gráficos salvos em: {fig_path}")
    
    plt.close()


if __name__ == "__main__":
    df_metricas = realizar_backtest()








