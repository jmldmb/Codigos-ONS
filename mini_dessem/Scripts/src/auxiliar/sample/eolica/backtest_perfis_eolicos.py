"""
Backtest de Modelo Estocástico Eólico (AR(1))
==============================================

Valida a qualidade do modelo AR(1) com perfil horário:
1. Cobertura dos intervalos de confiança
2. Autocorrelação dos resíduos
3. Aderência do perfil médio

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
from eolica_sampler import EolicaSampler
from scipy import stats

# Configurar estilo dos gráficos
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Definir diretórios
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
DATA_PATH = BASE_DIR / "output" / "curtailment" / "eolica" / "comparacao_perfil_curtailment" / "por_mes" / "perfil_hora_por_mes.csv"
BACKTEST_DIR = BASE_DIR / "output" / "sample" / "eolica" / "backtest"
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)


def calcular_metricas_estocasticas(
    real: np.ndarray, 
    cenarios: np.ndarray,
    nivel_confianca: float = 0.95
) -> dict:
    """
    Calcula métricas para modelo estocástico
    
    Args:
        real: Perfil real (24 valores)
        cenarios: Matriz (n_cenarios, 24) com perfis simulados
        nivel_confianca: Nível de confiança para intervalos
    
    Returns:
        Dicionário com métricas
    """
    # Estatísticas dos cenários
    media_cenarios = np.mean(cenarios, axis=0)
    
    # Percentis para intervalo de confiança
    alpha = 1 - nivel_confianca
    p_lower = alpha / 2 * 100
    p_upper = (1 - alpha / 2) * 100
    
    ic_lower = np.percentile(cenarios, p_lower, axis=0)
    ic_upper = np.percentile(cenarios, p_upper, axis=0)
    
    # Métricas do perfil médio
    mae = np.mean(np.abs(real - media_cenarios))
    rmse = np.sqrt(np.mean((real - media_cenarios) ** 2))
    
    # MAPE apenas em horas com geração significativa
    mask = real > 100
    if mask.sum() > 0:
        mape = np.mean(np.abs((real[mask] - media_cenarios[mask]) / real[mask])) * 100
    else:
        mape = np.nan
    
    # Cobertura do intervalo de confiança
    dentro_ic = (real >= ic_lower) & (real <= ic_upper)
    cobertura = np.mean(dentro_ic) * 100
    
    # Correlação
    if np.std(real) > 0 and np.std(media_cenarios) > 0:
        correlacao = np.corrcoef(real, media_cenarios)[0, 1]
    else:
        correlacao = np.nan
    
    # Autocorrelação dos resíduos
    residuos = real - media_cenarios
    if len(residuos) > 1:
        autocorr_residuos = np.corrcoef(residuos[:-1], residuos[1:])[0, 1]
    else:
        autocorr_residuos = np.nan
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'correlacao': correlacao,
        'cobertura_ic': cobertura,
        'autocorr_residuos': autocorr_residuos
    }


def realizar_backtest(n_cenarios: int = 100):
    """
    Realiza backtest do modelo estocástico
    
    Args:
        n_cenarios: Número de cenários a gerar para cada mês
    """
    print("="*70)
    print("BACKTEST - MODELO ESTOCÁSTICO EÓLICO AR(1)")
    print("="*70)
    
    # Carregar dados históricos
    print(f"\n[1/6] Carregando dados históricos...")
    df_real = pd.read_csv(DATA_PATH)
    df_real['mes'] = pd.to_datetime(df_real['mes'])
    df_real['mes_num'] = df_real['mes'].dt.month
    df_real['ano'] = df_real['mes'].dt.year
    
    print(f"  ✓ {len(df_real)} registros carregados")
    print(f"  ✓ {df_real['mes'].nunique()} meses únicos")
    print(f"  ✓ Período: {df_real['mes'].min().strftime('%Y-%m')} a {df_real['mes'].max().strftime('%Y-%m')}")
    
    # Criar sampler
    print(f"\n[2/6] Inicializando sampler...")
    sampler = EolicaSampler()
    print(f"  ✓ Sampler inicializado")
    print(f"  ✓ Gerando {n_cenarios} cenários por mês para validação")
    
    # Realizar backtest
    print(f"\n[3/6] Executando backtest...")
    print("  " + "-"*66)
    
    resultados = []
    
    for mes_data, grupo in df_real.groupby('mes'):
        ano = mes_data.year
        mes = mes_data.month
        
        # Perfil real do mês
        perfil_real = grupo.set_index('hora')['potencial_total_mwh_media'].values
        
        # Calcular MWmédios
        n_dias = pd.Period(f'{ano}-{mes:02d}').days_in_month
        total_mensal = perfil_real.sum() * n_dias
        n_horas = n_dias * 24
        mw_medios = total_mensal / n_horas
        
        # Gerar múltiplos cenários
        cenarios = sampler.gerar_multiplos_cenarios(
            mes=mes,
            mw_medios=mw_medios,
            n_cenarios=n_cenarios,
            seed=42  # Reprodutibilidade
        )
        
        # Calcular métricas
        metricas = calcular_metricas_estocasticas(perfil_real, cenarios)
        
        resultados.append({
            'ano': ano,
            'mes': mes,
            'mes_data': mes_data,
            'mw_medios': mw_medios,
            'total_real_dia_mwh': perfil_real.sum(),
            'n_cenarios': n_cenarios,
            **metricas
        })
        
        # Printar resultado
        status = "✓" if metricas['cobertura_ic'] >= 90 else "⚠"
        print(f"  {status} {mes_data.strftime('%Y-%m')}: "
              f"MAE={metricas['mae']:>6.1f}, "
              f"MAPE={metricas['mape']:>5.2f}%, "
              f"Cob={metricas['cobertura_ic']:>5.1f}%, "
              f"Corr={metricas['correlacao']:>5.3f}")
    
    df_resultados = pd.DataFrame(resultados)
    
    # Métricas agregadas
    print("\n[4/6] Métricas Agregadas:")
    print("  " + "-"*66)
    print(f"  MAE médio:                 {df_resultados['mae'].mean():>8.2f} MWh")
    print(f"  RMSE médio:                {df_resultados['rmse'].mean():>8.2f} MWh")
    print(f"  MAPE médio:                {df_resultados['mape'].mean():>8.2f}%")
    print(f"  Correlação média:          {df_resultados['correlacao'].mean():>8.3f}")
    print(f"  Cobertura IC95 média:      {df_resultados['cobertura_ic'].mean():>8.2f}%")
    print(f"  Autocorr. resíduos média:  {df_resultados['autocorr_residuos'].mean():>8.3f}")
    
    # Interpretação da cobertura
    cobertura_media = df_resultados['cobertura_ic'].mean()
    print(f"\n  Interpretação da Cobertura:")
    if cobertura_media >= 93 and cobertura_media <= 97:
        print(f"    ✅ EXCELENTE: Cobertura ~95% indica calibração perfeita!")
    elif cobertura_media >= 90:
        print(f"    ✅ BOA: Modelo bem calibrado")
    elif cobertura_media >= 80:
        print(f"    ⚠️  RAZOÁVEL: Modelo subestima incerteza")
    else:
        print(f"    ⚠️  RUIM: Intervalos muito estreitos")
    
    # Interpretação da autocorrelação dos resíduos
    autocorr_media = df_resultados['autocorr_residuos'].mean()
    print(f"\n  Autocorrelação dos Resíduos:")
    if abs(autocorr_media) < 0.2:
        print(f"    ✅ EXCELENTE: Resíduos não correlacionados (modelo captura bem AR)")
    elif abs(autocorr_media) < 0.5:
        print(f"    ✅ BOA: Baixa correlação residual")
    else:
        print(f"    ⚠️  ATENÇÃO: Resíduos ainda correlacionados (considerar ARMA)")
    
    # Estatísticas por mês do ano
    print("\n[5/6] Métricas por Mês do Ano:")
    print("  " + "-"*66)
    metricas_por_mes = df_resultados.groupby('mes').agg({
        'mae': 'mean',
        'mape': 'mean',
        'cobertura_ic': 'mean'
    }).round(2)
    
    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    for mes_num in sorted(metricas_por_mes.index):
        row = metricas_por_mes.loc[mes_num]
        print(f"  {meses_nomes[mes_num-1]:3s}: "
              f"MAE={row['mae']:>7.1f} MWh, "
              f"MAPE={row['mape']:>5.2f}%, "
              f"Cob={row['cobertura_ic']:>5.1f}%")
    
    # Salvar métricas
    metricas_file = BACKTEST_DIR / "metricas_backtest.csv"
    df_resultados.to_csv(metricas_file, index=False)
    print(f"\n  ✓ Métricas salvas em: {metricas_file}")
    
    # Gerar visualizações
    print("\n[6/6] Gerando visualizações...")
    criar_graficos_backtest(df_real, df_resultados, sampler, n_cenarios)
    
    # Conclusão
    print("\n" + "="*70)
    print("BACKTEST CONCLUÍDO!")
    print("="*70)
    
    print(f"\n📊 Resumo Final:")
    print(f"   MAPE médio:         {df_resultados['mape'].mean():.2f}%")
    print(f"   Cobertura IC95:     {df_resultados['cobertura_ic'].mean():.2f}%")
    print(f"   Correlação:         {df_resultados['correlacao'].mean():.3f}")
    print(f"   Autocorr. resíduos: {df_resultados['autocorr_residuos'].mean():.3f}")
    
    # Avaliação final
    if df_resultados['cobertura_ic'].mean() >= 90 and df_resultados['mape'].mean() < 10:
        print("\n   ✅ MODELO VALIDADO: Excelente performance!")
    elif df_resultados['cobertura_ic'].mean() >= 80:
        print("\n   ✅ MODELO BOM: Performance adequada")
    else:
        print("\n   ⚠️  MODELO NECESSITA AJUSTES")
    
    return df_resultados


def criar_graficos_backtest(df_real, df_metricas, sampler, n_cenarios):
    """
    Cria visualizações do backtest
    """
    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    fig = plt.figure(figsize=(20, 16))
    
    # 1. MAPE ao longo do tempo
    ax1 = plt.subplot(4, 3, 1)
    ax1.plot(df_metricas['mes_data'], df_metricas['mape'], 'o-', 
             linewidth=2, markersize=6, color='steelblue')
    ax1.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='Limite 10%')
    ax1.axhline(y=df_metricas['mape'].mean(), color='red', linestyle='--', 
                alpha=0.5, label=f'Média: {df_metricas["mape"].mean():.2f}%')
    ax1.set_title('MAPE ao Longo do Tempo', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Mês')
    ax1.set_ylabel('MAPE (%)')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # 2. Cobertura IC95 ao longo do tempo
    ax2 = plt.subplot(4, 3, 2)
    ax2.plot(df_metricas['mes_data'], df_metricas['cobertura_ic'], 'o-',
             linewidth=2, markersize=6, color='green')
    ax2.axhline(y=95, color='red', linestyle='--', alpha=0.5, label='Esperado: 95%')
    ax2.axhline(y=df_metricas['cobertura_ic'].mean(), color='blue', 
                linestyle='--', alpha=0.5, 
                label=f'Média: {df_metricas["cobertura_ic"].mean():.1f}%')
    ax2.set_title('Cobertura do Intervalo de Confiança (95%)', 
                  fontsize=11, fontweight='bold')
    ax2.set_xlabel('Mês')
    ax2.set_ylabel('Cobertura (%)')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 100])
    
    # 3. Autocorrelação dos resíduos
    ax3 = plt.subplot(4, 3, 3)
    ax3.plot(df_metricas['mes_data'], df_metricas['autocorr_residuos'], 'o-',
             linewidth=2, markersize=6, color='purple')
    ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax3.axhline(y=df_metricas['autocorr_residuos'].mean(), color='blue',
                linestyle='--', alpha=0.5,
                label=f'Média: {df_metricas["autocorr_residuos"].mean():.3f}')
    ax3.set_title('Autocorrelação dos Resíduos', fontsize=11, fontweight='bold')
    ax3.set_xlabel('Mês')
    ax3.set_ylabel('Autocorrelação')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # 4. Exemplo de melhor mês - Envelope de cenários
    ax4 = plt.subplot(4, 3, 4)
    
    idx_melhor = df_metricas['cobertura_ic'].apply(lambda x: abs(x - 95)).idxmin()
    melhor_mes = df_metricas.loc[idx_melhor]
    
    grupo_melhor = df_real[df_real['mes'] == melhor_mes['mes_data']]
    perfil_real = grupo_melhor.set_index('hora')['potencial_total_mwh_media'].values
    
    cenarios_melhor = sampler.gerar_multiplos_cenarios(
        melhor_mes['mes'], melhor_mes['mw_medios'], n_cenarios, seed=42
    )
    
    # Envelope
    p05 = np.percentile(cenarios_melhor, 5, axis=0)
    p25 = np.percentile(cenarios_melhor, 25, axis=0)
    p50 = np.percentile(cenarios_melhor, 50, axis=0)
    p75 = np.percentile(cenarios_melhor, 75, axis=0)
    p95 = np.percentile(cenarios_melhor, 95, axis=0)
    
    ax4.fill_between(range(24), p05, p95, alpha=0.2, color='blue', label='P05-P95')
    ax4.fill_between(range(24), p25, p75, alpha=0.3, color='blue', label='P25-P75')
    ax4.plot(range(24), p50, 'b-', linewidth=2, label='Mediana')
    ax4.plot(range(24), perfil_real, 'ro-', linewidth=2, 
             markersize=5, label='Real')
    
    ax4.set_title(f'Envelope de Cenários: {melhor_mes["mes_data"].strftime("%Y-%m")} '
                  f'(Cob={melhor_mes["cobertura_ic"]:.1f}%)',
                  fontsize=11, fontweight='bold')
    ax4.set_xlabel('Hora do Dia')
    ax4.set_ylabel('Geração (MWh)')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(range(0, 24, 2))
    
    # 5. Exemplo de pior mês
    ax5 = plt.subplot(4, 3, 5)
    
    idx_pior = df_metricas['mape'].idxmax()
    pior_mes = df_metricas.loc[idx_pior]
    
    grupo_pior = df_real[df_real['mes'] == pior_mes['mes_data']]
    perfil_real_pior = grupo_pior.set_index('hora')['potencial_total_mwh_media'].values
    
    cenarios_pior = sampler.gerar_multiplos_cenarios(
        pior_mes['mes'], pior_mes['mw_medios'], n_cenarios, seed=42
    )
    
    p05_pior = np.percentile(cenarios_pior, 5, axis=0)
    p95_pior = np.percentile(cenarios_pior, 95, axis=0)
    p50_pior = np.percentile(cenarios_pior, 50, axis=0)
    
    ax5.fill_between(range(24), p05_pior, p95_pior, alpha=0.2, color='blue')
    ax5.plot(range(24), p50_pior, 'b-', linewidth=2, label='Mediana')
    ax5.plot(range(24), perfil_real_pior, 'ro-', linewidth=2, 
             markersize=5, label='Real')
    
    ax5.set_title(f'Maior Erro: {pior_mes["mes_data"].strftime("%Y-%m")} '
                  f'(MAPE={pior_mes["mape"]:.2f}%)',
                  fontsize=11, fontweight='bold')
    ax5.set_xlabel('Hora do Dia')
    ax5.set_ylabel('Geração (MWh)')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3)
    ax5.set_xticks(range(0, 24, 2))
    
    # 6. Distribuição de MAPE
    ax6 = plt.subplot(4, 3, 6)
    ax6.hist(df_metricas['mape'], bins=20, color='steelblue', 
             edgecolor='black', alpha=0.7)
    ax6.axvline(x=df_metricas['mape'].mean(), color='red',
                linestyle='--', linewidth=2,
                label=f'Média: {df_metricas["mape"].mean():.2f}%')
    ax6.set_title('Distribuição do MAPE', fontsize=11, fontweight='bold')
    ax6.set_xlabel('MAPE (%)')
    ax6.set_ylabel('Frequência')
    ax6.legend(fontsize=9)
    ax6.grid(True, alpha=0.3, axis='y')
    
    # 7. Scatter: Real vs Previsto (médias dos cenários)
    ax7 = plt.subplot(4, 3, 7)
    
    todos_reais = []
    todos_previstos = []
    
    for _, row in df_metricas.iterrows():
        grupo = df_real[df_real['mes'] == row['mes_data']]
        perfil_real = grupo.set_index('hora')['potencial_total_mwh_media'].values
        
        cenarios = sampler.gerar_multiplos_cenarios(
            row['mes'], row['mw_medios'], 50, seed=42
        )
        perfil_prev = np.mean(cenarios, axis=0)
        
        todos_reais.extend(perfil_real)
        todos_previstos.extend(perfil_prev)
    
    ax7.scatter(todos_reais, todos_previstos, alpha=0.4, s=20, color='steelblue')
    
    min_val = min(min(todos_reais), min(todos_previstos))
    max_val = max(max(todos_reais), max(todos_previstos))
    ax7.plot([min_val, max_val], [min_val, max_val], 'r--',
             linewidth=2, label='Ajuste Perfeito')
    
    ax7.set_title('Real vs Previsto (Média dos Cenários)',
                  fontsize=11, fontweight='bold')
    ax7.set_xlabel('Real (MWh)')
    ax7.set_ylabel('Previsto (MWh)')
    ax7.legend(fontsize=9)
    ax7.grid(True, alpha=0.3)
    
    # 8. MAPE por mês do ano
    ax8 = plt.subplot(4, 3, 8)
    
    metricas_por_mes_ano = df_metricas.groupby('mes')['mape'].mean()
    x = list(metricas_por_mes_ano.index)
    y = metricas_por_mes_ano.values
    
    colors = plt.cm.RdYlGn_r(y / max(y) if max(y) > 0 else 1)
    ax8.bar(x, y, color=colors, edgecolor='black', alpha=0.7)
    ax8.axhline(y=10, color='orange', linestyle='--', alpha=0.5)
    ax8.set_title('MAPE por Mês do Ano', fontsize=11, fontweight='bold')
    ax8.set_xlabel('Mês')
    ax8.set_ylabel('MAPE (%)')
    ax8.set_xticks(x)
    ax8.set_xticklabels([meses_nomes[m-1] for m in x], rotation=45)
    ax8.grid(True, alpha=0.3, axis='y')
    
    # 9. Cobertura por mês do ano
    ax9 = plt.subplot(4, 3, 9)
    
    cobertura_por_mes = df_metricas.groupby('mes')['cobertura_ic'].mean()
    x = list(cobertura_por_mes.index)
    y = cobertura_por_mes.values
    
    colors = ['green' if abs(v - 95) < 5 else 'orange' for v in y]
    ax9.bar(x, y, color=colors, edgecolor='black', alpha=0.7)
    ax9.axhline(y=95, color='red', linestyle='--', alpha=0.5, label='Esperado')
    ax9.set_title('Cobertura IC95 por Mês', fontsize=11, fontweight='bold')
    ax9.set_xlabel('Mês')
    ax9.set_ylabel('Cobertura (%)')
    ax9.set_xticks(x)
    ax9.set_xticklabels([meses_nomes[m-1] for m in x], rotation=45)
    ax9.legend(fontsize=9)
    ax9.grid(True, alpha=0.3, axis='y')
    ax9.set_ylim([80, 100])
    
    # 10. Exemplo de cenários individuais (Setembro)
    ax10 = plt.subplot(4, 3, 10)
    
    mes_exemplo = 9
    dados_set = df_metricas[df_metricas['mes'] == mes_exemplo]
    if len(dados_set) > 0:
        row_set = dados_set.iloc[0]
        
        # Gerar alguns cenários
        cenarios_viz = sampler.gerar_multiplos_cenarios(
            mes_exemplo, row_set['mw_medios'], 10, seed=123
        )
        
        for i, cenario in enumerate(cenarios_viz):
            ax10.plot(range(24), cenario, alpha=0.3, linewidth=1, color='gray')
        
        # Média
        media_cenarios = np.mean(cenarios_viz, axis=0)
        ax10.plot(range(24), media_cenarios, 'b-', linewidth=3, 
                 label='Média (10 cenários)', alpha=0.8)
        
        ax10.set_title('Visualização de Cenários Individuais (Setembro)',
                      fontsize=11, fontweight='bold')
        ax10.set_xlabel('Hora do Dia')
        ax10.set_ylabel('Geração (MWh)')
        ax10.legend(fontsize=9)
        ax10.grid(True, alpha=0.3)
        ax10.set_xticks(range(0, 24, 2))
    
    # 11. Q-Q Plot (Normalidade dos resíduos)
    ax11 = plt.subplot(4, 3, 11)
    
    # Coletar resíduos de todos os meses
    residuos_totais = []
    
    for _, row in df_metricas.iterrows():
        grupo = df_real[df_real['mes'] == row['mes_data']]
        perfil_real = grupo.set_index('hora')['potencial_total_mwh_media'].values
        
        cenarios = sampler.gerar_multiplos_cenarios(
            row['mes'], row['mw_medios'], 50, seed=42
        )
        media_cenarios = np.mean(cenarios, axis=0)
        
        residuos = (perfil_real - media_cenarios) / np.std(cenarios, axis=0)
        residuos_totais.extend(residuos[~np.isnan(residuos)])
    
    stats.probplot(residuos_totais, dist="norm", plot=ax11)
    ax11.set_title('Q-Q Plot (Normalidade dos Resíduos)',
                   fontsize=11, fontweight='bold')
    ax11.grid(True, alpha=0.3)
    
    # 12. Perfil médio geral: Real vs Modelo
    ax12 = plt.subplot(4, 3, 12)
    
    # Perfil real médio (média de todos os meses)
    perfil_real_geral = df_real.groupby('hora')['potencial_total_mwh_media'].mean()
    
    # Perfil modelo médio (média dos perfis determinísticos)
    perfis_modelo = []
    for mes_num in range(1, 13):
        if mes_num in sampler.perfis:
            prop = sampler.perfis[mes_num]['perfil_proporcional']
            perfil_modelo = np.array([prop[h] for h in range(24)])
            perfis_modelo.append(perfil_modelo)
    
    perfil_modelo_geral = np.mean(perfis_modelo, axis=0)
    perfil_modelo_geral = perfil_modelo_geral / perfil_modelo_geral.sum() * perfil_real_geral.sum()
    
    ax12.plot(range(24), perfil_real_geral.values, 'o-', linewidth=2,
              label='Real', markersize=6, color='blue')
    ax12.plot(range(24), perfil_modelo_geral, 's--', linewidth=2,
              label='Modelo', markersize=6, color='orange', alpha=0.8)
    ax12.set_title('Perfil Médio Geral: Real vs Modelo',
                   fontsize=11, fontweight='bold')
    ax12.set_xlabel('Hora do Dia')
    ax12.set_ylabel('Geração Média (MWh)')
    ax12.legend(fontsize=9)
    ax12.grid(True, alpha=0.3)
    ax12.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    
    # Salvar
    fig_path = BACKTEST_DIR / "backtest_perfis_eolicos.png"
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Gráficos salvos em: {fig_path}")
    
    plt.close()


if __name__ == "__main__":
    # Executar backtest com 100 cenários
    df_metricas = realizar_backtest(n_cenarios=100)

