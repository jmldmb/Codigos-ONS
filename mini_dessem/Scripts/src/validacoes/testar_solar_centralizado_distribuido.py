"""
Teste e Validação da Separação Solar: Centralizada vs Distribuída
===================================================================

Valida que:
1. Médias mensais batem com data.py
2. Soma centralizada + distribuída = total esperado
3. Perfis horários fazem sentido
4. Simulação completa funciona corretamente
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Adicionar o diretório src ao path (subir dois níveis: validacoes -> src -> Scripts -> src)
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

from mini_dessem.simulation import run_simulation
from mini_dessem.pricing import carregar_pilha_termica
from mini_dessem.data import (
    geracao_solar_centralizada_dic,
    geracao_solar_distribuida_dic,
    capacidade_solar_total_dic
)
from mini_dessem.config import SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA

def testar_medias_mensais():
    """Testa se soma centralizada + distribuída = total"""
    
    print("\n" + "="*90)
    print("  TESTE 1: Validação de Médias Mensais")
    print("="*90)
    
    print(f"\n{'Ano-Mês':<10} {'Centr':<10} {'Distr':<10} {'Soma':<10} {'Total':<10} {'Diferença':<12} {'Status'}")
    print("-"*90)
    
    problemas = 0
    
    for ano in [2024, 2025, 2026]:
        for mes in range(1, 13):
            cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
            dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
            soma = cent + dist
            total = capacidade_solar_total_dic.get(ano, {}).get(mes, 0)
            
            if total > 0:
                dif_pct = abs(soma - total) / total * 100
                status = "OK" if dif_pct < 1 else "ERRO!"
                
                if dif_pct >= 1:
                    problemas += 1
                
                print(f"{ano}-{mes:02d}    {cent:<10,} {dist:<10,} {soma:<10,} {total:<10,} {dif_pct:>+10.2f}%  {status}")
    
    if problemas == 0:
        print(f"\n[OK] Todas as somas estão corretas!")
    else:
        print(f"\n[AVISO] {problemas} meses com diferenças!")
    
    return problemas == 0

def testar_simulacao_completa():
    """Executa simulação completa de teste"""
    
    print("\n" + "="*90)
    print("  TESTE 2: Simulação Completa (Setembro/2025)")
    print("="*90)
    
    print(f"\nModo de separação: {'HABILITADO' if SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA else 'DESABILITADO'}")
    
    # Valores esperados
    ano, mes = 2025, 9
    cent_esperado = geracao_solar_centralizada_dic[ano][mes]
    dist_esperado = geracao_solar_distribuida_dic[ano][mes]
    total_esperado = capacidade_solar_total_dic[ano][mes]
    
    print(f"\nValores em data.py (Setembro/2025):")
    print(f"  Centralizada:  {cent_esperado:,} MW")
    print(f"  Distribuída:   {dist_esperado:,} MW")
    print(f"  Total:         {total_esperado:,} MW ({cent_esperado + dist_esperado:,} MW)")
    
    # Executar simulação
    print(f"\nExecutando simulação (1 cenário)...")
    print("-"*90)
    
    pilha = carregar_pilha_termica()
    
    df = run_simulation(
        num_simulations=1,
        anos=[ano],
        meses=[mes],
        pilha_termica=pilha,
        verbose=False
    )
    
    if len(df) == 0:
        print("\n[ERRO] Simulação não gerou resultados!")
        return False
    
    # Analisar resultados
    media_solar = df['val_gersolar'].mean()
    
    print(f"\n" + "="*90)
    print("  RESULTADOS")
    print("="*90)
    
    print(f"\nMédia Solar Gerada: {media_solar:,.0f} MW")
    print(f"Total Esperado:     {total_esperado:,.0f} MW")
    
    dif_pct = abs(media_solar - total_esperado) / total_esperado * 100
    
    print(f"\nDiferença: {dif_pct:+.2f}%")
    
    if dif_pct < 1:
        print("[OK] Simulação está correta!")
        status = True
    else:
        print("[AVISO] Diferença maior que esperado!")
        status = False
    
    # Estatísticas adicionais
    print(f"\nEstatísticas da simulação:")
    print(f"  Registros: {len(df)}")
    print(f"  Solar Min/Max: {df['val_gersolar'].min():.0f} / {df['val_gersolar'].max():.0f} MW")
    print(f"  Desvio padrão: {df['val_gersolar'].std():.0f} MW")
    
    return status

def comparar_perfis():
    """Compara perfis centralizada vs distribuída (validação final da hipótese)"""
    
    print("\n" + "="*90)
    print("  TESTE 3: Comparação de Perfis - Validação da Hipótese")
    print("="*90)
    
    import json
    
    base_dir = Path(__file__).parent.parent / "output" / "sample" / "solar_distribuida"
    
    with open(base_dir / "perfis_horarios_centralizada.json", 'r', encoding='utf-8') as f:
        perfis_cent = json.load(f)
    
    with open(base_dir / "perfis_horarios_distribuida.json", 'r', encoding='utf-8') as f:
        perfis_dist = json.load(f)
    
    # Analisar setembro (mês de teste)
    mes = 9
    
    prop_cent = {int(k): v for k, v in perfis_cent[str(mes)]['perfil_proporcional'].items()}
    prop_dist = {int(k): v for k, v in perfis_dist[str(mes)]['perfil_proporcional'].items()}
    
    print(f"\nSetembro - Comparação hora a hora:")
    print(f"{'Hora':<6} {'Centr (%)':<12} {'Distr (%)':<12} {'Diferença':<12} {'Observação'}")
    print("-"*90)
    
    diferencas_significativas = []
    
    for hora in range(24):
        cent = prop_cent[hora] * 100
        dist = prop_dist[hora] * 100
        dif = dist - cent
        
        obs = ""
        if cent > 1 or dist > 1:  # Horas com geração
            if abs(dif) > 2:
                diferencas_significativas.append((hora, dif))
                obs = "<-- DIFERENTE"
        
        if cent > 0.5 or dist > 0.5:
            print(f"{hora:02d}h   {cent:>10.2f}  {dist:>10.2f}  {dif:>+9.2f}   {obs}")
    
    # Hora de pico
    hora_pico_cent = max(prop_cent.items(), key=lambda x: x[1])[0]
    hora_pico_dist = max(prop_dist.items(), key=lambda x: x[1])[0]
    
    print(f"\nHoras de pico:")
    print(f"  Centralizada: {hora_pico_cent:02d}h ({prop_cent[hora_pico_cent]*100:.2f}%)")
    print(f"  Distribuída:  {hora_pico_dist:02d}h ({prop_dist[hora_pico_dist]*100:.2f}%)")
    
    if hora_pico_cent != hora_pico_dist:
        print(f"  → Picos DIFERENTES! ({abs(hora_pico_dist - hora_pico_cent)}h de diferença)")
    
    print(f"\nDiferenças significativas (>2%) em {len(diferencas_significativas)} horas:")
    for hora, dif in diferencas_significativas[:5]:
        print(f"  {hora:02d}h: {dif:+.2f}%")
    
    # Conclusão
    print("\n" + "-"*90)
    print("  VALIDAÇÃO DA HIPÓTESE")
    print("-"*90)
    
    if len(diferencas_significativas) >= 5 and hora_pico_cent != hora_pico_dist:
        print("\n[CONFIRMADO] Perfis são SIGNIFICATIVAMENTE DIFERENTES")
        print("  → Justifica modelagem separada")
        print("  → Distribuída tem pico mais cedo e mais concentrado")
        return True
    elif len(diferencas_significativas) >= 3:
        print("\n[PARCIAL] Perfis têm algumas diferenças")
        print("  → Modelagem separada pode trazer ganhos")
        return True
    else:
        print("\n[NEGADO] Perfis são bastante similares")
        print("  → Modelagem separada pode não ser necessária")
        return False

def main():
    print("\n" + "="*90)
    print("  VALIDAÇÃO COMPLETA: Solar Centralizada vs Distribuída")
    print("="*90)
    
    print(f"\nConfiguração:")
    print(f"  SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA = {SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA}")
    
    resultados = {}
    
    # Teste 1
    resultados['medias'] = testar_medias_mensais()
    
    # Teste 2
    resultados['simulacao'] = testar_simulacao_completa()
    
    # Teste 3
    resultados['perfis'] = comparar_perfis()
    
    # Resumo final
    print("\n" + "="*90)
    print("  RESUMO FINAL")
    print("="*90)
    
    print(f"\nTestes:")
    print(f"  [{'OK' if resultados['medias'] else 'FALHA'}] Validação de médias mensais")
    print(f"  [{'OK' if resultados['simulacao'] else 'AVISO'}] Simulação completa")
    print(f"  [{'OK' if resultados['perfis'] else 'INFO'}] Perfis são diferentes")
    
    todos_ok = all(resultados.values())
    
    if todos_ok:
        print("\n[OK] Todos os testes passaram!")
        print("\nSistema pronto para uso com separação centralizada/distribuída.")
    elif resultados['medias'] and resultados['simulacao']:
        print("\n[OK] Testes críticos passaram")
        print("Sistema funcional.")
    else:
        print("\n[AVISO] Alguns testes falharam")
        print("Revisar configurações.")
    
    print("\n" + "="*90)
    
    return 0 if todos_ok else 1

if __name__ == '__main__':
    sys.exit(main())

