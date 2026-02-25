"""
Análise Separada - Centralizada vs Distribuída
==============================================

Analisa os perfis de geração solar separadamente:
- Centralizada: características, perfis, séries sintéticas
- Distribuída: características, perfis, séries sintéticas
- Comparação entre os dois tipos

Para cada tipo gera:
1. Séries sintéticas completas
2. Análise de características (horário de pico, shape, etc)
3. Comparação com dados reais quando disponíveis
4. Visualizações detalhadas

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
from datetime import datetime
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
OUTPUT_DIR = BASE_DIR / "output" / "sample"

# Diretórios de output por tipo
CENT_DIR = OUTPUT_DIR / "solar" / "analise_detalhada"
DIST_DIR = OUTPUT_DIR / "solar_distribuida" / "analise_detalhada"
COMP_DIR = OUTPUT_DIR / "solar_comparacao" / "analise_cent_vs_dist"

# Criar diretórios
CENT_DIR.mkdir(parents=True, exist_ok=True)
DIST_DIR.mkdir(parents=True, exist_ok=True)
COMP_DIR.mkdir(parents=True, exist_ok=True)

# Caminhos de dados
DATA_BALANCO = BASE_DIR / "Data" / "raw_data"
DATA_CURTAILMENT = BASE_DIR / "output" / "curtailment" / "solar" / "comparacao_perfil_curtailment"


def carregar_dados_reais_separados(ano, mes):
    """
    Carrega dados reais SEPARADOS (centralizada dos arquivos de curtailment)
    e calcula distribuída por diferença
    
    Returns:
        DataFrame com: data_hora, hora, total_real, cent_real, dist_real
    """
    # Carregar total do BALANCO_ENERGIA
    arquivo_balanco = DATA_BALANCO / f"BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx"
    
    if not arquivo_balanco.exists():
        return None
    
    try:
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
        
        # Tentar carregar dados de curtailment (centralizada)
        arquivo_curtailment = DATA_CURTAILMENT / "por_mes" / f"{ano}_{mes:02d}_curtailment.csv"
        
        if arquivo_curtailment.exists():
            df_curt = pd.read_csv(arquivo_curtailment)
            df_curt = df_curt[df_curt['id_subsistema'] == 'SIN'].copy()
            df_curt['din_instante'] = pd.to_datetime(df_curt['din_instante'], errors='coerce')
            
            # Merge
            df_merged = pd.merge(
                df_balanco[['din_instante', 'val_gersolar']],
                df_curt[['din_instante', 'potencial_total_mwh']],
                on='din_instante',
                how='left'
            )
            
            df_merged['total_real'] = df_merged['val_gersolar']
            df_merged['cent_real'] = df_merged['potencial_total_mwh']
            df_merged['dist_real'] = df_merged['total_real'] - df_merged['cent_real']
            
            # Preparar saída
            df_saida = df_merged[['din_instante', 'total_real', 'cent_real', 'dist_real']].copy()
            df_saida.columns = ['data_hora', 'total_real', 'cent_real', 'dist_real']
            df_saida['hora'] = df_saida['data_hora'].dt.hour
            df_saida = df_saida.sort_values('data_hora').reset_index(drop=True)
            
            return df_saida
        else:
            # Sem dados de curtailment, retornar apenas total
            df_saida = df_balanco[['din_instante', 'val_gersolar']].copy()
            df_saida.columns = ['data_hora', 'total_real']
            df_saida['hora'] = df_saida['data_hora'].dt.hour
            df_saida['cent_real'] = np.nan
            df_saida['dist_real'] = np.nan
            df_saida = df_saida.sort_values('data_hora').reset_index(drop=True)
            
            return df_saida
        
    except Exception as e:
        print(f"  ⚠ Erro ao processar {ano}-{mes:02d}: {e}")
        return None


def gerar_serie_sintetica_separada(sampler_cent, sampler_dist, ano, mes):
    """
    Gera série sintética SEPARADA para centralizada e distribuída
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


def calcular_metricas_tipo(real, sintetico, tipo):
    """
    Calcula métricas para um tipo específico
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
        'tipo': tipo,
        'n_registros': len(real_clean),
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'r2': r2,
        'correlacao': correlacao,
        'bias': bias,
        'bias_pct': bias_pct,
        'media_real': np.mean(real_clean),
        'media_sint': np.mean(sint_clean)
    }


def analisar_caracteristicas_perfil(sampler, tipo, meses_analisar):
    """
    Analisa características do perfil (hora de pico, shape, etc)
    """
    dados = []
    
    for ano, mes in meses_analisar:
        mw = (geracao_solar_centralizada_dic if tipo == 'Centralizada' 
              else geracao_solar_distribuida_dic).get(ano, {}).get(mes, 0)
        
        if mw == 0:
            continue
        
        # Gerar perfil
        perfil = sampler.gerar_perfil_dia(mes, mw)
        
        # Características
        hora_pico = np.argmax(perfil)
        valor_pico = np.max(perfil)
        valor_medio = np.mean(perfil)
        
        # Horas com geração > 10% do pico
        horas_ativas = np.sum(perfil > (valor_pico * 0.1))
        
        # Assimetria do perfil
        centro_massa = np.sum(np.arange(24) * perfil) / np.sum(perfil)
        
        # Concentração (quanto % está nas 6h centrais)
        inicio_central = max(0, hora_pico - 3)
        fim_central = min(24, hora_pico + 4)
        geracao_central = np.sum(perfil[inicio_central:fim_central])
        concentracao_pct = (geracao_central / np.sum(perfil)) * 100
        
        dados.append({
            'ano': ano,
            'mes': mes,
            'ano_mes': f"{ano}-{mes:02d}",
            'tipo': tipo,
            'mw_medios': mw,
            'hora_pico': hora_pico,
            'valor_pico': valor_pico,
            'valor_medio': valor_medio,
            'fator_pico': valor_pico / valor_medio if valor_medio > 0 else 0,
            'horas_ativas': horas_ativas,
            'centro_massa': centro_massa,
            'concentracao_6h_pct': concentracao_pct
        })
    
    return pd.DataFrame(dados)


def criar_graficos_comparacao_tipos(df_carac_cent, df_carac_dist):
    """
    Cria gráficos comparando características entre centralizada e distribuída
    """
    fig, axes = plt.subplots(3, 3, figsize=(20, 15))
    fig.suptitle('Análise Comparativa - Centralizada vs Distribuída', 
                 fontsize=18, fontweight='bold')
    
    # 1. Hora de Pico
    ax = axes[0, 0]
    ax.plot(df_carac_cent['ano_mes'], df_carac_cent['hora_pico'], 
            'o-', linewidth=2, markersize=6, label='Centralizada', color='blue')
    ax.plot(df_carac_dist['ano_mes'], df_carac_dist['hora_pico'], 
            's-', linewidth=2, markersize=6, label='Distribuída', color='orange')
    ax.axhline(y=14, color='blue', linestyle='--', alpha=0.3, label='Esperado Cent (14h)')
    ax.axhline(y=11, color='orange', linestyle='--', alpha=0.3, label='Esperado Dist (11h)')
    ax.set_title('Hora do Pico', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Hora')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 2. MWmédios
    ax = axes[0, 1]
    ax.plot(df_carac_cent['ano_mes'], df_carac_cent['mw_medios'], 
            'o-', linewidth=2, markersize=6, label='Centralizada', color='blue')
    ax.plot(df_carac_dist['ano_mes'], df_carac_dist['mw_medios'], 
            's-', linewidth=2, markersize=6, label='Distribuída', color='orange')
    ax.set_title('MWmédios', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('MW')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 3. Proporção Cent/Dist
    ax = axes[0, 2]
    total = df_carac_cent['mw_medios'] + df_carac_dist['mw_medios']
    prop_cent = (df_carac_cent['mw_medios'] / total) * 100
    prop_dist = (df_carac_dist['mw_medios'] / total) * 100
    
    x = np.arange(len(df_carac_cent))
    ax.bar(x, prop_cent, label='Centralizada', alpha=0.7, color='blue')
    ax.bar(x, prop_dist, bottom=prop_cent, label='Distribuída', alpha=0.7, color='orange')
    ax.set_title('Proporção (%)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Proporção (%)')
    ax.set_xticks(x[::2])
    ax.set_xticklabels(df_carac_cent['ano_mes'].iloc[::2], rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. Fator de Pico
    ax = axes[1, 0]
    ax.plot(df_carac_cent['ano_mes'], df_carac_cent['fator_pico'], 
            'o-', linewidth=2, markersize=6, label='Centralizada', color='blue')
    ax.plot(df_carac_dist['ano_mes'], df_carac_dist['fator_pico'], 
            's-', linewidth=2, markersize=6, label='Distribuída', color='orange')
    ax.set_title('Fator de Pico (Pico/Média)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Fator')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 5. Horas Ativas (>10% pico)
    ax = axes[1, 1]
    ax.plot(df_carac_cent['ano_mes'], df_carac_cent['horas_ativas'], 
            'o-', linewidth=2, markersize=6, label='Centralizada', color='blue')
    ax.plot(df_carac_dist['ano_mes'], df_carac_dist['horas_ativas'], 
            's-', linewidth=2, markersize=6, label='Distribuída', color='orange')
    ax.set_title('Horas Ativas (>10% pico)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Horas')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 6. Centro de Massa
    ax = axes[1, 2]
    ax.plot(df_carac_cent['ano_mes'], df_carac_cent['centro_massa'], 
            'o-', linewidth=2, markersize=6, label='Centralizada', color='blue')
    ax.plot(df_carac_dist['ano_mes'], df_carac_dist['centro_massa'], 
            's-', linewidth=2, markersize=6, label='Distribuída', color='orange')
    ax.set_title('Centro de Massa (hora)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('Hora')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 7. Concentração (6h centrais)
    ax = axes[2, 0]
    ax.plot(df_carac_cent['ano_mes'], df_carac_cent['concentracao_6h_pct'], 
            'o-', linewidth=2, markersize=6, label='Centralizada', color='blue')
    ax.plot(df_carac_dist['ano_mes'], df_carac_dist['concentracao_6h_pct'], 
            's-', linewidth=2, markersize=6, label='Distribuída', color='orange')
    ax.set_title('Concentração nas 6h Centrais (%)', fontsize=12, fontweight='bold')
    ax.set_xlabel('Mês')
    ax.set_ylabel('% da Geração')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
    
    # 8. Distribuições de Hora de Pico
    ax = axes[2, 1]
    ax.hist(df_carac_cent['hora_pico'], bins=range(7, 19), alpha=0.6, 
            label='Centralizada', color='blue', edgecolor='black')
    ax.hist(df_carac_dist['hora_pico'], bins=range(7, 19), alpha=0.6, 
            label='Distribuída', color='orange', edgecolor='black')
    ax.set_title('Distribuição de Hora de Pico', fontsize=12, fontweight='bold')
    ax.set_xlabel('Hora')
    ax.set_ylabel('Frequência')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 9. Resumo Estatístico
    ax = axes[2, 2]
    ax.axis('off')
    
    resumo_texto = [
        ['Característica', 'Cent', 'Dist', 'Δ'],
        ['Hora Pico (h)', 
         f"{df_carac_cent['hora_pico'].mean():.1f}",
         f"{df_carac_dist['hora_pico'].mean():.1f}",
         f"{df_carac_cent['hora_pico'].mean() - df_carac_dist['hora_pico'].mean():.1f}"],
        ['Fator Pico', 
         f"{df_carac_cent['fator_pico'].mean():.2f}",
         f"{df_carac_dist['fator_pico'].mean():.2f}",
         f"{df_carac_cent['fator_pico'].mean() - df_carac_dist['fator_pico'].mean():.2f}"],
        ['Horas Ativas', 
         f"{df_carac_cent['horas_ativas'].mean():.1f}",
         f"{df_carac_dist['horas_ativas'].mean():.1f}",
         f"{df_carac_cent['horas_ativas'].mean() - df_carac_dist['horas_ativas'].mean():.1f}"],
        ['Concentr. 6h (%)', 
         f"{df_carac_cent['concentracao_6h_pct'].mean():.1f}",
         f"{df_carac_dist['concentracao_6h_pct'].mean():.1f}",
         f"{df_carac_cent['concentracao_6h_pct'].mean() - df_carac_dist['concentracao_6h_pct'].mean():.1f}"],
        ['Proporção (%)', 
         f"{prop_cent.mean():.1f}",
         f"{prop_dist.mean():.1f}",
         '-']
    ]
    
    table = ax.table(cellText=resumo_texto, cellLoc='center', loc='center',
                     colWidths=[0.4, 0.2, 0.2, 0.2])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.5)
    
    for i in range(4):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax.set_title('Resumo Comparativo', fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout()
    fig_path = COMP_DIR / "comparacao_caracteristicas.png"
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    return fig_path


def criar_graficos_perfis_mensais(sampler_cent, sampler_dist, meses_exemplo):
    """
    Cria gráficos com perfis mensais lado a lado
    """
    n_meses = len(meses_exemplo)
    n_rows = (n_meses + 2) // 3
    
    fig, axes = plt.subplots(n_rows, 3, figsize=(18, 5*n_rows))
    fig.suptitle('Perfis Horários Mensais - Centralizada vs Distribuída', 
                 fontsize=16, fontweight='bold')
    
    for idx, (ano, mes) in enumerate(meses_exemplo):
        if idx >= n_rows * 3:
            break
        
        row = idx // 3
        col = idx % 3
        ax = axes[row, col] if n_rows > 1 else axes[col]
        
        # Buscar MWmédios
        mw_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
        mw_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
        
        if mw_cent == 0 or mw_dist == 0:
            continue
        
        # Gerar perfis
        perfil_cent = sampler_cent.gerar_perfil_dia(mes, mw_cent)
        perfil_dist = sampler_dist.gerar_perfil_dia(mes, mw_dist)
        
        # Normalizar para % do dia
        perfil_cent_norm = (perfil_cent / perfil_cent.sum()) * 100
        perfil_dist_norm = (perfil_dist / perfil_dist.sum()) * 100
        
        horas = range(24)
        
        # Plotar
        ax.fill_between(horas, 0, perfil_cent_norm, alpha=0.3, label='Centralizada', color='blue')
        ax.fill_between(horas, 0, perfil_dist_norm, alpha=0.3, label='Distribuída', color='orange')
        ax.plot(horas, perfil_cent_norm, 'o-', linewidth=2, markersize=4, color='blue')
        ax.plot(horas, perfil_dist_norm, 's-', linewidth=2, markersize=4, color='orange')
        
        # Marcar picos
        pico_cent = np.argmax(perfil_cent_norm)
        pico_dist = np.argmax(perfil_dist_norm)
        ax.axvline(x=pico_cent, color='blue', linestyle='--', alpha=0.5, linewidth=1)
        ax.axvline(x=pico_dist, color='orange', linestyle='--', alpha=0.5, linewidth=1)
        
        # Proporções
        total = mw_cent + mw_dist
        prop_cent = (mw_cent / total) * 100
        prop_dist = (mw_dist / total) * 100
        
        ax.set_title(f'{ano}-{mes:02d} | Cent: {prop_cent:.0f}% (pico {pico_cent}h) | '
                    f'Dist: {prop_dist:.0f}% (pico {pico_dist}h)', 
                    fontsize=10, fontweight='bold')
        ax.set_xlabel('Hora do Dia', fontsize=9)
        ax.set_ylabel('% da Geração Diária', fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 3))
    
    # Esconder axes vazios
    for idx in range(len(meses_exemplo), n_rows * 3):
        row = idx // 3
        col = idx % 3
        ax = axes[row, col] if n_rows > 1 else axes[col]
        ax.axis('off')
    
    plt.tight_layout()
    fig_path = COMP_DIR / "perfis_mensais_comparacao.png"
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    return fig_path


def processar_analise_completa():
    """
    Processa análise completa separada por tipo
    """
    print("="*80)
    print("ANÁLISE SEPARADA - CENTRALIZADA VS DISTRIBUÍDA")
    print("="*80)
    
    # Criar samplers
    print("\n[1/6] Inicializando samplers...")
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
    
    # Analisar características dos perfis
    print("\n[2/6] Analisando características dos perfis...")
    df_carac_cent = analisar_caracteristicas_perfil(sampler_cent, 'Centralizada', meses_processar)
    df_carac_dist = analisar_caracteristicas_perfil(sampler_dist, 'Distribuída', meses_processar)
    
    print(f"  ✓ Centralizada: {len(df_carac_cent)} meses analisados")
    print(f"    - Hora pico média: {df_carac_cent['hora_pico'].mean():.1f}h")
    print(f"    - Fator pico médio: {df_carac_cent['fator_pico'].mean():.2f}")
    
    print(f"  ✓ Distribuída: {len(df_carac_dist)} meses analisados")
    print(f"    - Hora pico média: {df_carac_dist['hora_pico'].mean():.1f}h")
    print(f"    - Fator pico médio: {df_carac_dist['fator_pico'].mean():.2f}")
    
    # Salvar características
    df_carac_cent.to_csv(CENT_DIR / "caracteristicas_perfil.csv", index=False)
    df_carac_dist.to_csv(DIST_DIR / "caracteristicas_perfil.csv", index=False)
    print("  ✓ Características salvas")
    
    # Comparar com dados reais quando disponível
    print("\n[3/6] Comparando com dados reais (quando disponível)...")
    resultados_cent = []
    resultados_dist = []
    
    for ano, mes in meses_processar:
        # Carregar dados reais
        df_real = carregar_dados_reais_separados(ano, mes)
        
        if df_real is None:
            continue
        
        # Gerar sintético
        df_sint = gerar_serie_sintetica_separada(sampler_cent, sampler_dist, ano, mes)
        
        if df_sint is None:
            continue
        
        # Merge
        df_comp = pd.merge(df_real, df_sint, on=['data_hora', 'hora'], how='inner')
        
        # Calcular métricas para centralizada
        if not df_comp['cent_real'].isna().all():
            metricas_cent = calcular_metricas_tipo(
                df_comp['cent_real'].values, 
                df_comp['cent_sint'].values,
                'Centralizada'
            )
            if metricas_cent:
                metricas_cent['ano'] = ano
                metricas_cent['mes'] = mes
                metricas_cent['ano_mes'] = f"{ano}-{mes:02d}"
                resultados_cent.append(metricas_cent)
                print(f"  ✓ {ano}-{mes:02d} Centralizada: MAPE={metricas_cent['mape']:.2f}%, R²={metricas_cent['r2']:.3f}")
        
        # Calcular métricas para distribuída
        if not df_comp['dist_real'].isna().all():
            metricas_dist = calcular_metricas_tipo(
                df_comp['dist_real'].values, 
                df_comp['dist_sint'].values,
                'Distribuída'
            )
            if metricas_dist:
                metricas_dist['ano'] = ano
                metricas_dist['mes'] = mes
                metricas_dist['ano_mes'] = f"{ano}-{mes:02d}"
                resultados_dist.append(metricas_dist)
                print(f"  ✓ {ano}-{mes:02d} Distribuída:  MAPE={metricas_dist['mape']:.2f}%, R²={metricas_dist['r2']:.3f}")
    
    # Salvar métricas
    if resultados_cent:
        df_metricas_cent = pd.DataFrame(resultados_cent)
        df_metricas_cent.to_csv(CENT_DIR / "metricas_validacao.csv", index=False)
        print(f"\n  ✓ Centralizada: {len(df_metricas_cent)} meses com dados reais")
        print(f"    MAPE médio: {df_metricas_cent['mape'].mean():.2f}%")
        print(f"    R² médio: {df_metricas_cent['r2'].mean():.3f}")
    
    if resultados_dist:
        df_metricas_dist = pd.DataFrame(resultados_dist)
        df_metricas_dist.to_csv(DIST_DIR / "metricas_validacao.csv", index=False)
        print(f"  ✓ Distribuída: {len(df_metricas_dist)} meses com dados reais")
        print(f"    MAPE médio: {df_metricas_dist['mape'].mean():.2f}%")
        print(f"    R² médio: {df_metricas_dist['r2'].mean():.3f}")
    
    # Gerar gráficos
    print("\n[4/6] Gerando gráficos de comparação de características...")
    fig1_path = criar_graficos_comparacao_tipos(df_carac_cent, df_carac_dist)
    print(f"  ✓ Salvo: {fig1_path.name}")
    
    print("\n[5/6] Gerando gráficos de perfis mensais...")
    fig2_path = criar_graficos_perfis_mensais(sampler_cent, sampler_dist, meses_processar)
    print(f"  ✓ Salvo: {fig2_path.name}")
    
    # Gerar séries sintéticas consolidadas
    print("\n[6/6] Gerando séries sintéticas consolidadas...")
    todas_series = []
    
    for ano, mes in meses_processar:
        df_sint = gerar_serie_sintetica_separada(sampler_cent, sampler_dist, ano, mes)
        if df_sint is not None:
            df_sint['ano'] = ano
            df_sint['mes'] = mes
            todas_series.append(df_sint)
    
    if todas_series:
        df_todas = pd.concat(todas_series, ignore_index=True)
        df_todas.to_csv(COMP_DIR / "series_sinteticas_separadas.csv", index=False)
        print(f"  ✓ {len(df_todas):,} registros salvos")
    
    # Resumo final
    print("\n" + "="*80)
    print("RESUMO FINAL")
    print("="*80)
    
    print("\n📊 CENTRALIZADA:")
    print(f"  - Hora pico média:        {df_carac_cent['hora_pico'].mean():.1f}h")
    print(f"  - Fator pico médio:       {df_carac_cent['fator_pico'].mean():.2f}x")
    print(f"  - Concentração 6h:        {df_carac_cent['concentracao_6h_pct'].mean():.1f}%")
    print(f"  - Horas ativas:           {df_carac_cent['horas_ativas'].mean():.1f}h")
    if resultados_cent:
        print(f"  - MAPE vs Real:           {df_metricas_cent['mape'].mean():.2f}%")
        print(f"  - R² vs Real:             {df_metricas_cent['r2'].mean():.3f}")
    
    print("\n📊 DISTRIBUÍDA:")
    print(f"  - Hora pico média:        {df_carac_dist['hora_pico'].mean():.1f}h")
    print(f"  - Fator pico médio:       {df_carac_dist['fator_pico'].mean():.2f}x")
    print(f"  - Concentração 6h:        {df_carac_dist['concentracao_6h_pct'].mean():.1f}%")
    print(f"  - Horas ativas:           {df_carac_dist['horas_ativas'].mean():.1f}h")
    if resultados_dist:
        print(f"  - MAPE vs Real:           {df_metricas_dist['mape'].mean():.2f}%")
        print(f"  - R² vs Real:             {df_metricas_dist['r2'].mean():.3f}")
    
    total = df_carac_cent['mw_medios'] + df_carac_dist['mw_medios']
    prop_cent = (df_carac_cent['mw_medios'] / total * 100).mean()
    prop_dist = (df_carac_dist['mw_medios'] / total * 100).mean()
    
    print(f"\n📈 PROPORÇÕES:")
    print(f"  - Centralizada:           {prop_cent:.1f}%")
    print(f"  - Distribuída:            {prop_dist:.1f}%")
    
    dif_pico = df_carac_cent['hora_pico'].mean() - df_carac_dist['hora_pico'].mean()
    print(f"\n⏰ DIFERENÇA DE PICOS:")
    print(f"  - Diferença temporal:     {dif_pico:.1f}h")
    
    print(f"\n📁 ARQUIVOS GERADOS:")
    print(f"  - Centralizada:           {CENT_DIR}")
    print(f"  - Distribuída:            {DIST_DIR}")
    print(f"  - Comparação:             {COMP_DIR}")
    
    print("\n" + "="*80)
    print("ANÁLISE CONCLUÍDA!")
    print("="*80)
    
    return df_carac_cent, df_carac_dist


if __name__ == "__main__":
    df_carac_cent, df_carac_dist = processar_analise_completa()




