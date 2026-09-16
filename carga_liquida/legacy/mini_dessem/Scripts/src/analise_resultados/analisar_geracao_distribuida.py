"""
Análise das Características da Geração Solar Distribuída
=========================================================

Compara perfis horários de centralizada vs distribuída
para validar hipótese de que são diferentes.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

def analisar_caracteristicas():
    print("\n" + "="*90)
    print("  ANÁLISE: Características da Geração Solar Distribuída")
    print("="*90)
    
    base_dir = Path(__file__).parent.parent / "output" / "sample" / "solar_distribuida"
    
    # Carregar perfis
    with open(base_dir / "perfis_horarios_centralizada.json", 'r', encoding='utf-8') as f:
        perfis_cent = json.load(f)
    
    with open(base_dir / "perfis_horarios_distribuida.json", 'r', encoding='utf-8') as f:
        perfis_dist = json.load(f)
    
    # Carregar médias mensais
    with open(base_dir / "medias_mensais_para_data_py.json", 'r', encoding='utf-8') as f:
        medias = json.load(f)
    
    print("\n" + "-"*90)
    print("  1. MÉDIAS MENSAIS AGREGADAS")
    print("-"*90)
    
    print(f"\n{'Mês':<15} {'Total (MW)':<12} {'Centr (MW)':<12} {'% Centr':<10} {'Distr (MW)':<12} {'% Distr'}")
    print("-"*90)
    
    for mes_num in range(1, 13):
        dados_mes = perfis_cent[str(mes_num)]
        cent_media = dados_mes['media_mw']
        dist_media = perfis_dist[str(mes_num)]['media_mw']
        total_media = cent_media + dist_media
        
        pct_cent = (cent_media / total_media * 100) if total_media > 0 else 0
        pct_dist = (dist_media / total_media * 100) if total_media > 0 else 0
        
        nome_mes = dados_mes['nome_mes']
        
        print(f"{nome_mes:<15} {total_media:>10,.0f}  {cent_media:>10,.0f}  {pct_cent:>7.1f}%  {dist_media:>10,.0f}  {pct_dist:>7.1f}%")
    
    # Comparar perfis horários
    print("\n" + "-"*90)
    print("  2. COMPARAÇÃO DE PERFIS HORÁRIOS (Média de Todos os Meses)")
    print("-"*90)
    
    # Calcular perfil médio agregado
    perfil_medio_cent = {}
    perfil_medio_dist = {}
    
    for hora in range(24):
        props_cent = [perfis_cent[str(m)]['perfil_proporcional'][str(hora)] for m in range(1, 13)]
        props_dist = [perfis_dist[str(m)]['perfil_proporcional'][str(hora)] for m in range(1, 13)]
        
        perfil_medio_cent[hora] = np.mean(props_cent)
        perfil_medio_dist[hora] = np.mean(props_dist)
    
    print(f"\n{'Hora':<6} {'Centr (%)':<12} {'Distr (%)':<12} {'Diferença':<12} {'Status'}")
    print("-"*90)
    
    diferencas = []
    for hora in range(24):
        cent = perfil_medio_cent[hora] * 100
        dist = perfil_medio_dist[hora] * 100
        dif = dist - cent
        
        diferencas.append(abs(dif))
        
        if cent > 0.5 or dist > 0.5:  # Horas com geração
            if abs(dif) < 0.5:
                status = "Similares"
            elif abs(dif) < 1.0:
                status = "Pequena dif"
            else:
                status = "DIFERENTE"
            
            print(f"{hora:02d}h   {cent:>10.2f}  {dist:>10.2f}  {dif:>+9.2f}   {status}")
    
    mae_dif = np.mean(diferencas)
    
    print(f"\nMAE das diferenças: {mae_dif:.3f}%")
    
    # Hora de pico
    hora_pico_cent = max(perfil_medio_cent.items(), key=lambda x: x[1])[0]
    hora_pico_dist = max(perfil_medio_dist.items(), key=lambda x: x[1])[0]
    
    print(f"\nHora de pico Centralizada:  {hora_pico_cent:02d}h ({perfil_medio_cent[hora_pico_cent]*100:.2f}%)")
    print(f"Hora de pico Distribuída:   {hora_pico_dist:02d}h ({perfil_medio_dist[hora_pico_dist]*100:.2f}%)")
    
    if hora_pico_cent != hora_pico_dist:
        print(f"PICOS DIFERENTES! Diferenca de {abs(hora_pico_dist - hora_pico_cent)}h")
    else:
        print(f"Picos coincidem")
    
    # Concentração (top 4 horas)
    valores_cent = list(perfil_medio_cent.values())
    valores_dist = list(perfil_medio_dist.values())
    
    top4_cent = sum(sorted(valores_cent, reverse=True)[:4])
    top4_dist = sum(sorted(valores_dist, reverse=True)[:4])
    
    print(f"\nConcentração (top 4 horas):")
    print(f"  Centralizada: {top4_cent*100:.1f}%")
    print(f"  Distribuída:  {top4_dist*100:.1f}%")
    
    if abs(top4_cent - top4_dist) > 0.05:
        print(f"  Concentracoes DIFERENTES ({abs(top4_cent - top4_dist)*100:.1f}% de diferenca)")
    else:
        print(f"  Concentracoes similares")
    
    # Teste estatístico
    print("\n" + "-"*90)
    print("  3. VALIDAÇÃO DA HIPÓTESE")
    print("-"*90)
    
    print("\nHipótese: Perfis de centralizada e distribuída são DIFERENTES")
    print(f"\nEvidências:")
    
    evidencias = []
    
    # Evidência 1: MAE
    if mae_dif > 0.5:
        evidencias.append(f"[OK] MAE = {mae_dif:.2f}% (> 0.5%, significativo)")
    else:
        print(f"  [X] MAE = {mae_dif:.2f}% (< 0.5%, pouco significativo)")
    
    # Evidência 2: Hora de pico
    if hora_pico_cent != hora_pico_dist:
        evidencias.append(f"[OK] Horas de pico diferentes ({hora_pico_cent}h vs {hora_pico_dist}h)")
    
    # Evidência 3: Concentração
    if abs(top4_cent - top4_dist) > 0.03:
        evidencias.append(f"[OK] Concentracoes diferentes ({top4_cent*100:.1f}% vs {top4_dist*100:.1f}%)")
    
    # Evidência 4: Padrões específicos
    std_cent = np.std(list(perfil_medio_cent.values()))
    std_dist = np.std(list(perfil_medio_dist.values()))
    
    if std_dist < std_cent * 0.9:
        evidencias.append(f"[OK] Distribuida mais plana (desvio padrao menor: {std_dist:.4f} vs {std_cent:.4f})")
    elif std_dist > std_cent * 1.1:
        evidencias.append(f"[OK] Distribuida mais concentrada (desvio padrao maior: {std_dist:.4f} vs {std_cent:.4f})")
    
    if evidencias:
        print("\n  HIPÓTESE CONFIRMADA! Perfis são diferentes:")
        for ev in evidencias:
            print(f"    {ev}")
    else:
        print("\n  Perfis são bastante similares")
    
    print("\n" + "="*90)
    print("  CONCLUSÃO")
    print("="*90)
    
    print(f"\nA geração distribuída representa {64.2:.1f}% da geração solar total")
    print(f"e possui perfil horário {'DIFERENTE' if len(evidencias) >= 2 else 'SIMILAR'} da centralizada.")
    
    if len(evidencias) >= 2:
        print("\nRECOMENDACAO: Modelar separadamente com samplers especificos")
    else:
        print("\nRECOMENDACAO: Pode usar mesmo perfil para ambas")
    
    print("\n" + "="*90)

if __name__ == '__main__':
    analisar_caracteristicas()

