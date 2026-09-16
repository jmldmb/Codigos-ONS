"""
VERIFICAR DISTORÇÃO DO MODELO V6
=================================

Analisa o quanto a renormalização está distorcendo o perfil horário
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date

# Importar modelo V6
import sys
sys.path.insert(0, str(Path(__file__).parent))
from carga_model_v6 import sample_carga_v6, _load_params

print("="*100)
print("  VERIFICAÇÃO DE DISTORÇÃO - MODELO V6")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. ANALISAR DISTORÇÃO TEÓRICA (APENAS REGRESSÕES)
# ============================================================================
print("\n[1/2] ANALISANDO DISTORÇÃO TEÓRICA (soma das regressões)...")

params = _load_params()
regressoes = params['regressoes']
perfil_temp = params['perfil_temp']
temp_ref = params['temp_ref']

distorcoes = []

for mes in range(1, 13):
    # Temperatura típica do mês
    temp_media = temp_ref[mes]['media']
    
    # Calcular carga normalizada para temperatura típica
    carga_norm = []
    for h in range(24):
        # Temperatura da hora
        desvio = perfil_temp.get((mes, h), 0.0)
        temp_h = temp_media + desvio
        
        # Regressão
        reg = regressoes.get((mes, h), {'intercept': 1.0, 'slope': 0.0})
        carga_norm_h = reg['intercept'] + reg['slope'] * temp_h
        carga_norm.append(carga_norm_h)
    
    # Soma
    soma = sum(carga_norm)
    distorcao_pct = abs(soma - 24.0) / 24.0 * 100
    fator_correcao = 24.0 / soma
    
    distorcoes.append({
        'mes': mes,
        'temp_media': temp_media,
        'soma_carga_norm': soma,
        'distorcao_pct': distorcao_pct,
        'fator_correcao': fator_correcao
    })

df_distorcoes = pd.DataFrame(distorcoes)

print(f"\n{'Mês':>4} | {'Temp (°C)':>9} | {'Soma':>8} | {'Distorção':>10} | {'Fator Corr':>12}")
print("-"*60)
for _, row in df_distorcoes.iterrows():
    print(f"{row['mes']:>4.0f} | {row['temp_media']:>9.2f} | {row['soma_carga_norm']:>8.4f} | "
          f"{row['distorcao_pct']:>9.2f}% | {row['fator_correcao']:>12.6f}")

print(f"\n{'ESTATÍSTICAS':20s} | {'VALOR':>15s}")
print("-"*40)
print(f"{'Distorção média':20s} | {df_distorcoes['distorcao_pct'].mean():>14.2f}%")
print(f"{'Distorção mediana':20s} | {df_distorcoes['distorcao_pct'].median():>14.2f}%")
print(f"{'Distorção mínima':20s} | {df_distorcoes['distorcao_pct'].min():>14.2f}%")
print(f"{'Distorção máxima':20s} | {df_distorcoes['distorcao_pct'].max():>14.2f}%")

# ============================================================================
# 2. TESTAR EM CASOS REAIS
# ============================================================================
print("\n[2/2] TESTANDO EM CASOS REAIS (várias temperaturas)...")

casos_teste = []

for mes in [1, 4, 7, 10]:  # Jan, Abr, Jul, Out
    temp_media = temp_ref[mes]['media']
    temp_std = temp_ref[mes]['std']
    
    # Testar várias temperaturas
    for temp_offset in [-2*temp_std, -temp_std, 0, temp_std, 2*temp_std]:
        temp_teste = temp_media + temp_offset
        data_teste = date(2024, mes, 15)
        
        # Calcular soma sem renormalizar
        temp_hora = []
        carga_norm = []
        for h in range(24):
            desvio = perfil_temp.get((mes, h), 0.0)
            temp_h = temp_teste + desvio
            temp_hora.append(temp_h)
            
            reg = regressoes.get((mes, h), {'intercept': 1.0, 'slope': 0.0})
            carga_norm_h = reg['intercept'] + reg['slope'] * temp_h
            carga_norm.append(carga_norm_h)
        
        soma = sum(carga_norm)
        distorcao = abs(soma - 24.0) / 24.0 * 100
        
        casos_teste.append({
            'mes': mes,
            'temp_teste': temp_teste,
            'temp_offset_std': temp_offset / temp_std if temp_std > 0 else 0,
            'soma': soma,
            'distorcao_pct': distorcao
        })

df_casos = pd.DataFrame(casos_teste)

print(f"\n{'Mes':>4} | {'Temp (C)':>9} | {'Offset (std)':>13} | {'Soma':>8} | {'Distorcao':>10}")
print("-"*64)
for _, row in df_casos.iterrows():
    print(f"{row['mes']:>4.0f} | {row['temp_teste']:>9.2f} | {row['temp_offset_std']:>+12.1f} | "
          f"{row['soma']:>8.4f} | {row['distorcao_pct']:>9.2f}%")

print(f"\n{'ESTATÍSTICAS GERAIS':20s} | {'VALOR':>15s}")
print("-"*40)
print(f"{'Distorcao media':20s} | {df_casos['distorcao_pct'].mean():>14.2f}%")
print(f"{'Distorcao mediana':20s} | {df_casos['distorcao_pct'].median():>14.2f}%")
print(f"{'Distorcao maxima':20s} | {df_casos['distorcao_pct'].max():>14.2f}%")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*100)
print("  RESUMO: DISTORCAO DA RENORMALIZACAO")
print("="*100)

dist_media_teorica = df_distorcoes['distorcao_pct'].mean()
dist_max_teorica = df_distorcoes['distorcao_pct'].max()
dist_media_pratica = df_casos['distorcao_pct'].mean()
dist_max_pratica = df_casos['distorcao_pct'].max()

print(f"""
DISTORCAO TEORICA (temperatura media mensal):
  Media:   {dist_media_teorica:.2f}%
  Maxima:  {dist_max_teorica:.2f}%

DISTORCAO PRATICA (varias temperaturas):
  Media:   {dist_media_pratica:.2f}%
  Maxima:  {dist_max_pratica:.2f}%

INTERPRETACAO:
  A renormalizacao ajusta o perfil em ~{dist_media_pratica:.2f}% em media.
  
  Isso significa que cada hora e multiplicada por um fator de ~{1.0 + dist_media_pratica/100:.4f}
  (ou dividida se soma > 24).
  
  {"OTIMO! Distorcao muito baixa (<1%)." if dist_max_pratica < 1.0 else ""}
  {"ACEITAVEL. Distorcao moderada (1-3%)." if 1.0 <= dist_max_pratica < 3.0 else ""}
  {"ATENCAO! Distorcao alta (>3%). Revisar regressoes." if dist_max_pratica >= 3.0 else ""}
""")

print("="*100)

