"""
Processamento de Perfis Horários Eólicos
=========================================

Este script processa dados históricos de geração eólica e estima:
1. Perfis horários médios por mês (μ_h,m)
2. Parâmetros do modelo AR(1): φ (autocorrelação) e σ_ε (variância do ruído)

Autor: ONS
Data: Novembro 2024
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
import json
from pathlib import Path

# Definir diretórios
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
DATA_PATH = BASE_DIR / "output" / "curtailment" / "eolica" / "comparacao_perfil_curtailment" / "por_mes" / "perfil_hora_por_mes.csv"
OUTPUT_DIR = BASE_DIR / "output" / "sample" / "eolica"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def estimar_parametros_ar1(serie_temporal: np.ndarray) -> dict:
    """
    Estima parâmetros do modelo AR(1) de uma série temporal
    
    Args:
        serie_temporal: Array com valores temporais
    
    Returns:
        dict com 'phi' (coef. autocorrelação) e 'sigma_epsilon' (desvio do ruído)
    """
    # Remover média
    serie_demean = serie_temporal - np.mean(serie_temporal)
    
    # Estimar φ via autocorrelação lag-1
    if len(serie_demean) > 1:
        phi = np.corrcoef(serie_demean[:-1], serie_demean[1:])[0, 1]
        
        # Limitar φ para estabilidade (processo estacionário)
        phi = np.clip(phi, -0.99, 0.99)
    else:
        phi = 0.0
    
    # Estimar σ_ε usando resíduos do modelo AR(1)
    if len(serie_demean) > 1 and abs(phi) > 0.01:
        residuos = serie_demean[1:] - phi * serie_demean[:-1]
        sigma_epsilon = np.std(residuos)
    else:
        sigma_epsilon = np.std(serie_demean)
    
    return {
        'phi': float(phi),
        'sigma_epsilon': float(sigma_epsilon)
    }


def processar_perfis_horarios():
    """
    Processa dados históricos e extrai:
    1. Perfis horários médios por mês
    2. Parâmetros AR(1) para variabilidade estocástica
    
    Returns:
        tuple: (perfis, parametros_ar1)
    """
    print("="*70)
    print("PROCESSAMENTO DE PERFIS HORÁRIOS EÓLICOS (AR(1))")
    print("="*70)
    
    # Carregar dados
    print(f"\n[1/5] Carregando dados de: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['mes'] = pd.to_datetime(df['mes'])
    df['mes_num'] = df['mes'].dt.month
    df['ano'] = df['mes'].dt.year
    
    print(f"  ✓ {len(df)} registros carregados")
    print(f"  ✓ Período: {df['mes'].min().strftime('%Y-%m')} a {df['mes'].max().strftime('%Y-%m')}")
    
    # Calcular perfis médios e parâmetros AR(1) por mês
    print("\n[2/5] Calculando perfis horários e parâmetros AR(1) por mês...")
    
    perfis = {}
    parametros_ar1 = {}
    
    for mes_num in range(1, 13):
        dados_mes = df[df['mes_num'] == mes_num]
        
        if len(dados_mes) == 0:
            print(f"  ⚠️  Mês {mes_num:02d}: Sem dados")
            continue
        
        # Perfil horário médio (média entre todos os dias deste mês)
        perfil_hora = dados_mes.groupby('hora')['potencial_total_mwh_media'].mean()
        
        # Total diário típico
        total_diario = perfil_hora.sum()
        
        # Proporção de cada hora
        proporcoes = (perfil_hora / total_diario).to_dict()
        
        # Estimar parâmetros AR(1)
        # Calcular resíduos normalizados para cada observação deste mês
        residuos_normalizados = []
        
        for mes_data, grupo_mes_especifico in dados_mes.groupby('mes'):
            perfil_mes_especifico = grupo_mes_especifico.set_index('hora')['potencial_total_mwh_media']
            
            # Resíduos normalizados = (observado - médio) / médio
            residuo_normalizado = (perfil_mes_especifico - perfil_hora) / (perfil_hora + 1e-10)
            residuos_normalizados.extend(residuo_normalizado.values)
        
        residuos_array = np.array(residuos_normalizados)
        params_ar1 = estimar_parametros_ar1(residuos_array)
        
        perfis[mes_num] = {
            'mes': mes_num,
            'nome_mes': pd.Timestamp(2024, mes_num, 1).strftime('%B'),
            'n_observacoes': len(dados_mes['mes'].unique()),
            'total_diario_medio_mwh': float(total_diario),
            'perfil_absoluto_mwh': {int(k): float(v) for k, v in perfil_hora.items()},
            'perfil_proporcional': {int(k): float(v) for k, v in proporcoes.items()}
        }
        
        parametros_ar1[mes_num] = {
            'mes': mes_num,
            'nome_mes': perfis[mes_num]['nome_mes'],
            'phi': params_ar1['phi'],
            'sigma_epsilon': params_ar1['sigma_epsilon'],
            'n_observacoes': perfis[mes_num]['n_observacoes']
        }
        
        print(f"  ✓ Mês {mes_num:02d} ({perfis[mes_num]['nome_mes']:>9s}): "
              f"{perfis[mes_num]['n_observacoes']} obs, "
              f"φ={params_ar1['phi']:.3f}, "
              f"σ_ε={params_ar1['sigma_epsilon']:.4f}")
    
    # Estatísticas dos perfis
    print("\n[3/5] Estatísticas dos perfis:")
    
    for mes_num in sorted(perfis.keys()):
        prop = perfis[mes_num]['perfil_proporcional']
        hora_min = min(prop.items(), key=lambda x: x[1])[0]
        hora_max = max(prop.items(), key=lambda x: x[1])[0]
        valor_max = prop[hora_max] * 100
        
        print(f"  • {perfis[mes_num]['nome_mes']:>9s}: "
              f"Mín={hora_min:02d}h, Máx={hora_max:02d}h ({valor_max:.2f}% do total)")
    
    # Estatísticas AR(1)
    print("\n[4/5] Estatísticas dos parâmetros AR(1):")
    phis = [p['phi'] for p in parametros_ar1.values()]
    sigmas = [p['sigma_epsilon'] for p in parametros_ar1.values()]
    
    print(f"  • φ (autocorrelação) médio: {np.mean(phis):.3f} (min={np.min(phis):.3f}, max={np.max(phis):.3f})")
    print(f"  • σ_ε (ruído) médio: {np.mean(sigmas):.4f} (min={np.min(sigmas):.4f}, max={np.max(sigmas):.4f})")
    
    if np.mean(phis) > 0.7:
        print(f"  → ALTA autocorrelação: modelo AR(1) é apropriado!")
    
    # Salvar perfis e parâmetros
    print("\n[5/5] Salvando perfis e parâmetros...")
    
    # Salvar perfis horários
    perfis_file = OUTPUT_DIR / "perfis_horarios.json"
    with open(perfis_file, 'w', encoding='utf-8') as f:
        json.dump(perfis, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Perfis salvos em: {perfis_file}")
    
    # Salvar parâmetros AR(1)
    params_file = OUTPUT_DIR / "parametros_ar1.json"
    with open(params_file, 'w', encoding='utf-8') as f:
        json.dump(parametros_ar1, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Parâmetros AR(1) salvos em: {params_file}")
    
    # Salvar também em CSV para fácil visualização
    df_perfis = []
    for mes_num, dados in perfis.items():
        for hora, proporcao in dados['perfil_proporcional'].items():
            df_perfis.append({
                'mes': mes_num,
                'nome_mes': dados['nome_mes'],
                'hora': hora,
                'proporcao': proporcao,
                'perfil_absoluto_mwh': dados['perfil_absoluto_mwh'][hora]
            })
    
    pd.DataFrame(df_perfis).to_csv(OUTPUT_DIR / "perfis_horarios.csv", index=False)
    print(f"  ✓ Perfis salvos em CSV")
    
    print("\n" + "="*70)
    print("PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
    print("="*70)
    
    return perfis, parametros_ar1


if __name__ == "__main__":
    perfis, parametros = processar_perfis_horarios()








