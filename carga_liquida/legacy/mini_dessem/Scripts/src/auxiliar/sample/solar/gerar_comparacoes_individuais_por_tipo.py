"""
Gerar Comparações Mensais Individualizadas por Tipo
===================================================

Gera gráficos de comparação SEPARADOS para:
- Centralizada: real vs sintético
- Distribuída: real vs sintético

Para cada mês, cria um gráfico detalhado com:
1. Série temporal completa
2. Scatter plot (correlação)
3. Perfil médio por hora do dia

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
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mini_dessem.data import (
    geracao_solar_centralizada_dic,
    geracao_solar_distribuida_dic,
    capacidade_solar_total_dic
)

# Definir diretórios
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "sample" / "solar_comparacao"

# Diretórios de output por tipo
CENT_COMP_DIR = OUTPUT_DIR / "comparacao_real_centralizada"
DIST_COMP_DIR = OUTPUT_DIR / "comparacao_real_distribuida"

# Criar diretórios
CENT_COMP_DIR.mkdir(parents=True, exist_ok=True)
DIST_COMP_DIR.mkdir(parents=True, exist_ok=True)

# Caminhos de dados
DATA_BALANCO = BASE_DIR / "Data" / "raw_data"
DATA_CURTAILMENT = BASE_DIR / "output" / "curtailment" / "solar" / "comparacao_perfil_curtailment"


def carregar_dados_reais_separados(ano, mes):
    """
    Carrega dados reais SEPARADOS (centralizada e distribuída)
    Usa perfil_hora_por_mes.csv para centralizada e BALANCO_ENERGIA para total
    """
    try:
        # Carregar dados de curtailment consolidados (contém centralizada)
        arquivo_curtailment = DATA_CURTAILMENT / "por_mes" / "perfil_hora_por_mes.csv"
        
        if not arquivo_curtailment.exists():
            return None
        
        df_curt = pd.read_csv(arquivo_curtailment)
        df_curt['mes'] = pd.to_datetime(df_curt['mes'], errors='coerce')
        df_curt = df_curt[(df_curt['mes'].dt.year == ano) & 
                          (df_curt['mes'].dt.month == mes)].copy()
        
        if len(df_curt) == 0:
            return None
        
        # Carregar total do BALANCO_ENERGIA
        arquivo_balanco = DATA_BALANCO / f"BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx"
        
        if not arquivo_balanco.exists():
            return None
        
        df_balanco = pd.read_excel(arquivo_balanco, sheet_name=0)
        
        # Filtrar SIN
        id_col = None
        for cand in ['id_subsistema', 'id_subsistena', 'nom_subsistema']:
            if cand in df_balanco.columns:
                id_col = cand
                break
        
        if id_col is not None:
            df_balanco[id_col] = df_balanco[id_col].astype(str).str.upper().str.strip()
            df_balanco = df_balanco[df_balanco[id_col] == 'SIN'].copy()
        
        # Processar datas
        df_balanco['din_instante'] = pd.to_datetime(df_balanco['din_instante'], errors='coerce')
        df_balanco = df_balanco.dropna(subset=['din_instante'])
        
        # Filtrar mês
        df_balanco = df_balanco[(df_balanco['din_instante'].dt.year == ano) & 
                                (df_balanco['din_instante'].dt.month == mes)].copy()
        
        if len(df_balanco) == 0:
            return None
        
        df_balanco['val_gersolar'] = pd.to_numeric(df_balanco['val_gersolar'], errors='coerce')
        
        # Merge pelo timestamp
        df_merged = pd.merge(
            df_balanco[['din_instante', 'val_gersolar']],
            df_curt[['hora', 'potencial_total_mwh_media']],
            left_on=df_balanco['din_instante'].dt.hour,
            right_on='hora',
            how='inner'
        )
        
        df_merged['total_real'] = df_merged['val_gersolar']
        df_merged['cent_real'] = df_merged['potencial_total_mwh_media']
        df_merged['dist_real'] = df_merged['total_real'] - df_merged['cent_real']
        
        # Preparar saída
        df_saida = df_merged[['din_instante', 'total_real', 'cent_real', 'dist_real', 'hora']].copy()
        df_saida.columns = ['data_hora', 'total_real', 'cent_real', 'dist_real', 'hora']
        df_saida = df_saida.sort_values('data_hora').reset_index(drop=True)
        
        return df_saida
        
    except Exception as e:
        print(f"  ⚠ Erro ao processar {ano}-{mes:02d}: {e}")
        import traceback
        traceback.print_exc()
        return None


def gerar_serie_sintetica_separada(sampler_cent, sampler_dist, ano, mes):
    """
    Gera série sintética SEPARADA
    """
    mw_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
    mw_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
    
    if mw_cent == 0 or mw_dist == 0:
        return None
    
    n_dias = calendar.monthrange(ano, mes)[1]
    
    dados = []
    
    for dia in range(1, n_dias + 1):
        perfil_cent = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        
        for hora in range(24):
            data_hora = pd.Timestamp(year=ano, month=mes, day=dia, hour=hora)
            
            dados.append({
                'data_hora': data_hora,
                'hora': hora,
                'cent_sint': perfil_cent[hora],
                'dist_sint': perfil_dist[hora],
                'total_sint': perfil_cent[hora] + perfil_dist[hora]
            })
    
    return pd.DataFrame(dados)


def calcular_metricas(real, sintetico):
    """
    Calcula métricas entre real e sintético
    """
    # Remover NaNs
    mask = ~(np.isnan(real) | np.isnan(sintetico))
    real_clean = real[mask]
    sint_clean = sintetico[mask]
    
    if len(real_clean) == 0:
        return None
    
    # MAE e RMSE
    mae = np.mean(np.abs(real_clean - sint_clean))
    rmse = np.sqrt(np.mean((real_clean - sint_clean) ** 2))
    
    # MAPE
    mask_sig = real_clean > 50
    if mask_sig.sum() > 0:
        mape = np.mean(np.abs((real_clean[mask_sig] - sint_clean[mask_sig]) / real_clean[mask_sig])) * 100
    else:
        mape = np.nan
    
    # R²
    ss_res = np.sum((real_clean - sint_clean) ** 2)
    ss_tot = np.sum((real_clean - np.mean(real_clean)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    
    # Correlação
    if np.std(real_clean) > 0 and np.std(sint_clean) > 0:
        correlacao = np.corrcoef(real_clean, sint_clean)[0, 1]
    else:
        correlacao = np.nan
    
    # Bias
    bias = np.mean(sint_clean - real_clean)
    bias_pct = (bias / np.mean(real_clean)) * 100 if np.mean(real_clean) > 0 else np.nan
    
    return {
        'n_registros': len(real_clean),
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
        'correlacao': correlacao,
        'bias': bias,
        'bias_pct': bias_pct
    }


def criar_grafico_comparacao_tipo(df_comparacao, ano, mes, metricas, tipo, col_real, col_sint):
    """
    Cria gráfico de comparação para um tipo específico
    
    Args:
        tipo: 'Centralizada' ou 'Distribuída'
        col_real: nome da coluna com dados reais
        col_sint: nome da coluna com dados sintéticos
    """
    cor = 'blue' if tipo == 'Centralizada' else 'orange'
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle(f'Comparação Real vs Sintético - {tipo} - {ano}-{mes:02d}', 
                 fontsize=16, fontweight='bold')
    
    # 1. Série temporal completa
    ax = axes[0]
    ax.plot(df_comparacao['data_hora'], df_comparacao[col_real], 
            '-', linewidth=1, label='Real', alpha=0.8, color='black')
    ax.plot(df_comparacao['data_hora'], df_comparacao[col_sint], 
            '-', linewidth=1, label='Sintético', alpha=0.7, color=cor)
    
    ax.set_title('Série Temporal Completa', fontsize=12, fontweight='bold')
    ax.set_xlabel('Data/Hora')
    ax.set_ylabel(f'Geração Solar {tipo} (MW)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Adicionar métricas
    textstr = f'MAPE: {metricas["mape"]:.2f}%\nR²: {metricas["r2"]:.3f}\nMAE: {metricas["mae"]:.1f} MW\nBias: {metricas["bias_pct"]:.2f}%'
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 2. Scatter plot Real vs Sintético
    ax = axes[1]
    scatter = ax.scatter(df_comparacao[col_real], df_comparacao[col_sint], 
                        alpha=0.5, s=15, c=df_comparacao['hora'], cmap='viridis')
    
    # Linha de referência
    min_val = min(df_comparacao[col_real].min(), df_comparacao[col_sint].min())
    max_val = max(df_comparacao[col_real].max(), df_comparacao[col_sint].max())
    ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Ajuste Perfeito')
    
    ax.set_title('Real vs Sintético (todos os pontos)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Real (MW)')
    ax.set_ylabel('Sintético (MW)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax, label='Hora do Dia')
    
    # 3. Perfil médio por hora do dia
    ax = axes[2]
    
    perfil_real = df_comparacao.groupby('hora')[col_real].mean()
    perfil_sint = df_comparacao.groupby('hora')[col_sint].mean()
    perfil_erro = perfil_sint - perfil_real
    
    horas = range(24)
    ax.plot(horas, perfil_real, 'o-', linewidth=2, markersize=6, 
            label='Real (média)', color='black')
    ax.plot(horas, perfil_sint, 's--', linewidth=2, markersize=6, 
            label='Sintético (média)', color=cor, alpha=0.7)
    
    # Área de erro
    ax2 = ax.twinx()
    ax2.bar(horas, perfil_erro, alpha=0.3, color='gray', label='Erro (Sint - Real)')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_ylabel('Erro (MW)', fontsize=11)
    ax2.legend(loc='upper right')
    
    # Marcar hora de pico
    hora_pico_real = perfil_real.idxmax()
    hora_pico_sint = perfil_sint.idxmax()
    ax.axvline(x=hora_pico_real, color='black', linestyle='--', alpha=0.3, linewidth=1)
    ax.axvline(x=hora_pico_sint, color=cor, linestyle='--', alpha=0.3, linewidth=1)
    
    ax.set_title(f'Perfil Médio por Hora | Pico Real: {hora_pico_real}h | Pico Sintético: {hora_pico_sint}h', 
                fontsize=12, fontweight='bold')
    ax.set_xlabel('Hora do Dia')
    ax.set_ylabel('Geração Solar (MW)', fontsize=11)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24))
    
    plt.tight_layout()
    
    # Salvar figura
    output_dir = CENT_COMP_DIR if tipo == 'Centralizada' else DIST_COMP_DIR
    fig_path = output_dir / f"{ano}_{mes:02d}_comparacao_{tipo.lower()}.png"
    plt.savefig(fig_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    
    return fig_path


def processar_comparacoes_por_tipo():
    """
    Processa comparações individuais para cada tipo
    """
    print("="*80)
    print("COMPARAÇÕES MENSAIS INDIVIDUALIZADAS POR TIPO")
    print("="*80)
    
    # Criar samplers
    print("\n[1/4] Inicializando samplers...")
    sampler_cent = SolarSampler()
    sampler_dist = SolarDistribuidaSampler()
    print("  ✓ Samplers inicializados")
    
    # Definir meses
    meses_processar = []
    for ano in [2024, 2025]:
        inicio = 4 if ano == 2024 else 1
        fim = 12 if ano == 2024 else 10
        for mes in range(inicio, fim + 1):
            meses_processar.append((ano, mes))
    
    print(f"\n[2/4] Processando {len(meses_processar)} meses...")
    print("  " + "-"*76)
    
    metricas_cent = []
    metricas_dist = []
    
    n_cent = 0
    n_dist = 0
    
    for ano, mes in meses_processar:
        print(f"\n  Processando {ano}-{mes:02d}...")
        
        # Carregar dados reais
        df_real = carregar_dados_reais_separados(ano, mes)
        
        if df_real is None:
            print(f"    ⚠ Sem dados reais separados disponíveis")
            continue
        
        print(f"    ✓ Dados reais carregados: {len(df_real)} registros")
        
        # Gerar sintético
        df_sint = gerar_serie_sintetica_separada(sampler_cent, sampler_dist, ano, mes)
        
        if df_sint is None:
            print(f"    ⚠ Erro ao gerar série sintética")
            continue
        
        # Merge
        df_comp = pd.merge(df_real, df_sint, on=['data_hora', 'hora'], how='inner')
        
        print(f"    ✓ Comparação: {len(df_comp)} registros pareados")
        
        # CENTRALIZADA
        if not df_comp['cent_real'].isna().all():
            metricas_c = calcular_metricas(df_comp['cent_real'].values, df_comp['cent_sint'].values)
            
            if metricas_c:
                metricas_c['ano'] = ano
                metricas_c['mes'] = mes
                metricas_c['ano_mes'] = f"{ano}-{mes:02d}"
                metricas_cent.append(metricas_c)
                
                # Criar gráfico
                fig_path_c = criar_grafico_comparacao_tipo(
                    df_comp, ano, mes, metricas_c, 
                    'Centralizada', 'cent_real', 'cent_sint'
                )
                
                print(f"    ✓ Centralizada: MAPE={metricas_c['mape']:.2f}%, R²={metricas_c['r2']:.3f}")
                print(f"      Gráfico salvo: {fig_path_c.name}")
                n_cent += 1
        
        # DISTRIBUÍDA
        if not df_comp['dist_real'].isna().all():
            metricas_d = calcular_metricas(df_comp['dist_real'].values, df_comp['dist_sint'].values)
            
            if metricas_d:
                metricas_d['ano'] = ano
                metricas_d['mes'] = mes
                metricas_d['ano_mes'] = f"{ano}-{mes:02d}"
                metricas_dist.append(metricas_d)
                
                # Criar gráfico
                fig_path_d = criar_grafico_comparacao_tipo(
                    df_comp, ano, mes, metricas_d, 
                    'Distribuída', 'dist_real', 'dist_sint'
                )
                
                print(f"    ✓ Distribuída:  MAPE={metricas_d['mape']:.2f}%, R²={metricas_d['r2']:.3f}")
                print(f"      Gráfico salvo: {fig_path_d.name}")
                n_dist += 1
    
    # Salvar métricas
    print("\n[3/4] Consolidando métricas...")
    
    if metricas_cent:
        df_metricas_cent = pd.DataFrame(metricas_cent)
        df_metricas_cent.to_csv(CENT_COMP_DIR / "metricas_centralizada.csv", index=False)
        print(f"  ✓ Centralizada: {len(df_metricas_cent)} meses")
        print(f"    MAPE médio: {df_metricas_cent['mape'].mean():.2f}%")
        print(f"    R² médio: {df_metricas_cent['r2'].mean():.3f}")
    
    if metricas_dist:
        df_metricas_dist = pd.DataFrame(metricas_dist)
        df_metricas_dist.to_csv(DIST_COMP_DIR / "metricas_distribuida.csv", index=False)
        print(f"  ✓ Distribuída: {len(df_metricas_dist)} meses")
        print(f"    MAPE médio: {df_metricas_dist['mape'].mean():.2f}%")
        print(f"    R² médio: {df_metricas_dist['r2'].mean():.3f}")
    
    # Criar gráficos resumo
    print("\n[4/4] Gerando gráficos resumo...")
    
    if metricas_cent and metricas_dist:
        criar_grafico_resumo_tipos(df_metricas_cent, df_metricas_dist)
    
    # Resumo final
    print("\n" + "="*80)
    print("PROCESSAMENTO CONCLUÍDO!")
    print("="*80)
    
    print(f"\n📊 GRÁFICOS GERADOS:")
    print(f"  - Centralizada:  {n_cent} gráficos em {CENT_COMP_DIR}")
    print(f"  - Distribuída:   {n_dist} gráficos em {DIST_COMP_DIR}")
    
    if metricas_cent:
        print(f"\n📈 CENTRALIZADA:")
        print(f"  - MAPE médio:    {df_metricas_cent['mape'].mean():.2f}%")
        print(f"  - R² médio:      {df_metricas_cent['r2'].mean():.3f}")
        print(f"  - MAE médio:     {df_metricas_cent['mae'].mean():.1f} MW")
        print(f"  - Bias médio:    {df_metricas_cent['bias_pct'].mean():.2f}%")
    
    if metricas_dist:
        print(f"\n📈 DISTRIBUÍDA:")
        print(f"  - MAPE médio:    {df_metricas_dist['mape'].mean():.2f}%")
        print(f"  - R² médio:      {df_metricas_dist['r2'].mean():.3f}")
        print(f"  - MAE médio:     {df_metricas_dist['mae'].mean():.1f} MW")
        print(f"  - Bias médio:    {df_metricas_dist['bias_pct'].mean():.2f}%")
    
    print("\n" + "="*80)
    
    return df_metricas_cent if metricas_cent else None, df_metricas_dist if metricas_dist else None


def criar_grafico_resumo_tipos(df_cent, df_dist):
    """
    Cria gráfico resumo comparando as métricas dos dois tipos
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Resumo de Performance - Centralizada vs Distribuída', 
                 fontsize=16, fontweight='bold')
    
    # 1. MAPE
    ax = axes[0, 0]
    ax.plot(df_cent['ano_mes'], df_cent['mape'], 'o-', linewidth=2, markersize=6, 
            label='Centralizada', color='blue')
    ax.plot(df_dist['ano_mes'], df_dist['mape'], 's-', linewidth=2, markersize=6, 
            label='Distribuída', color='orange')
    ax.set_title('MAPE por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('MAPE (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 2. R²
    ax = axes[0, 1]
    ax.plot(df_cent['ano_mes'], df_cent['r2'], 'o-', linewidth=2, markersize=6, 
            label='Centralizada', color='blue')
    ax.plot(df_dist['ano_mes'], df_dist['r2'], 's-', linewidth=2, markersize=6, 
            label='Distribuída', color='orange')
    ax.set_title('R² por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('R²')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 3. MAE
    ax = axes[0, 2]
    ax.plot(df_cent['ano_mes'], df_cent['mae'], 'o-', linewidth=2, markersize=6, 
            label='Centralizada', color='blue')
    ax.plot(df_dist['ano_mes'], df_dist['mae'], 's-', linewidth=2, markersize=6, 
            label='Distribuída', color='orange')
    ax.set_title('MAE por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('MAE (MW)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 4. Distribuição MAPE
    ax = axes[1, 0]
    ax.hist(df_cent['mape'], bins=10, alpha=0.6, label='Centralizada', 
            color='blue', edgecolor='black')
    ax.hist(df_dist['mape'], bins=10, alpha=0.6, label='Distribuída', 
            color='orange', edgecolor='black')
    ax.set_title('Distribuição de MAPE', fontsize=12, fontweight='bold')
    ax.set_xlabel('MAPE (%)')
    ax.set_ylabel('Frequência')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 5. Bias
    ax = axes[1, 1]
    ax.plot(df_cent['ano_mes'], df_cent['bias_pct'], 'o-', linewidth=2, markersize=6, 
            label='Centralizada', color='blue')
    ax.plot(df_dist['ano_mes'], df_dist['bias_pct'], 's-', linewidth=2, markersize=6, 
            label='Distribuída', color='orange')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_title('Bias por Mês', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Bias (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 6. Tabela resumo
    ax = axes[1, 2]
    ax.axis('off')
    
    resumo_texto = [
        ['Métrica', 'Centralizada', 'Distribuída'],
        ['MAPE (%)', f"{df_cent['mape'].mean():.2f}", f"{df_dist['mape'].mean():.2f}"],
        ['R²', f"{df_cent['r2'].mean():.3f}", f"{df_dist['r2'].mean():.3f}"],
        ['MAE (MW)', f"{df_cent['mae'].mean():.1f}", f"{df_dist['mae'].mean():.1f}"],
        ['Bias (%)', f"{df_cent['bias_pct'].mean():.2f}", f"{df_dist['bias_pct'].mean():.2f}"],
        ['Corr', f"{df_cent['correlacao'].mean():.3f}", f"{df_dist['correlacao'].mean():.3f}"]
    ]
    
    table = ax.table(cellText=resumo_texto, cellLoc='center', loc='center',
                     colWidths=[0.35, 0.325, 0.325])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    
    for i in range(3):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax.set_title('Resumo Comparativo', fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout()
    fig_path = OUTPUT_DIR / "resumo_comparativo_tipos.png"
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Gráfico resumo salvo: {fig_path.name}")


if __name__ == "__main__":
    df_cent, df_dist = processar_comparacoes_por_tipo()

