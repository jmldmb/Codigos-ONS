"""
Teste da Lógica de Curtailment em Cascata
==========================================

Valida que o curtailment ocorre na ordem correta:
1. Primeiro: Rateio proporcional entre Eólica e Solar Centralizada
2. Depois: Solar Distribuída (só se eólica e centralizada zeradas)
"""

import sys
from pathlib import Path

# Adicionar o diretório src ao path (subir dois níveis: validacoes -> src -> Scripts -> src)
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

from mini_dessem.dispatch import calcular_despacho_probabilistico

def testar_curtailment_cascata():
    print("\n" + "="*90)
    print("  TESTE: Lógica de Curtailment em Cascata")
    print("="*90)
    
    # Parâmetros base
    limite_hidro = 70000
    limite_hidro_reserv = 40000
    min_hidro_reserv = 12000
    val_inflexterm = 5000
    ENA_arm = 50000
    mes, hora, is_weekday = 9, 12, True
    
    print("\n" + "-"*90)
    print("  CENÁRIO 1: Curtailment Pequeno (só prioridade 1)")
    print("-"*90)
    
    # Curtailment pequeno - deve afetar só eólica e solar centralizada proporcionalmente
    val_carga = 50000
    val_eolica = 15000
    val_solar_cent = 5000
    val_solar_dist = 10000
    val_solar_total = val_solar_cent + val_solar_dist
    
    print(f"\nCarga: {val_carga:,} MW")
    print(f"Gerações:")
    print(f"  Eólica:            {val_eolica:,} MW")
    print(f"  Solar Centralizada:{val_solar_cent:,} MW")
    print(f"  Solar Distribuída: {val_solar_dist:,} MW")
    print(f"  Solar Total:       {val_solar_total:,} MW")
    
    resultado = calcular_despacho_probabilistico(
        limite_hidro, limite_hidro_reserv, val_carga,
        val_eolica, val_solar_total, val_inflexterm,
        ENA_arm, mes, hora, is_weekday, min_hidro_reserv,
        val_gersolar_centralizada=val_solar_cent,
        val_gersolar_distribuida=val_solar_dist
    )
    
    print(f"\nResultados:")
    print(f"  Curtailment Total:      {resultado['curtailment']:>10,.0f} MW")
    print(f"  Curtailment Eólica:     {resultado['curtailment_eolica']:>10,.0f} MW")
    print(f"  Curtailment Solar Cent: {resultado['curtailment_solar_cent']:>10,.0f} MW")
    print(f"  Curtailment Solar Dist: {resultado['curtailment_solar_dist']:>10,.0f} MW")
    
    print(f"\nGerações pós-curtailment:")
    print(f"  Eólica:            {resultado['val_gereolica_depois_corte']:>10,.0f} MW (corte: {resultado['curtailment_eolica']:,.0f})")
    print(f"  Solar Centralizada:{resultado.get('val_gersolar_cent_depois_corte', 0):>10,.0f} MW (corte: {resultado['curtailment_solar_cent']:,.0f})")
    print(f"  Solar Distribuída: {resultado.get('val_gersolar_dist_depois_corte', 0):>10,.0f} MW (corte: {resultado['curtailment_solar_dist']:,.0f})")
    
    # Validação
    if resultado['curtailment_solar_dist'] == 0:
        print(f"\n[OK] Solar Distribuída NÃO foi cortada (correto para curtailment pequeno)")
    else:
        print(f"\n[ERRO] Solar Distribuída foi cortada quando não deveria!")
    
    # Verificar proporcionalidade
    if resultado['curtailment_eolica'] > 0 and resultado['curtailment_solar_cent'] > 0:
        proporcao_curtailment = resultado['curtailment_eolica'] / (resultado['curtailment_eolica'] + resultado['curtailment_solar_cent'])
        proporcao_original = val_eolica / (val_eolica + val_solar_cent)
        
        if abs(proporcao_curtailment - proporcao_original) < 0.01:
            print(f"[OK] Curtailment foi PROPORCIONAL entre eólica e solar centralizada")
        else:
            print(f"[AVISO] Curtailment não foi proporcional!")
    
    print("\n" + "-"*90)
    print("  CENÁRIO 2: Curtailment Grande (atinge distribuída)")
    print("-"*90)
    
    # Curtailment grande - deve zerar eólica e centralizada, depois cortar distribuída
    val_carga = 10000  # Carga muito baixa
    val_eolica = 15000
    val_solar_cent = 5000
    val_solar_dist = 10000
    val_solar_total = val_solar_cent + val_solar_dist
    
    print(f"\nCarga: {val_carga:,} MW (muito baixa)")
    print(f"Gerações:")
    print(f"  Eólica:            {val_eolica:,} MW")
    print(f"  Solar Centralizada:{val_solar_cent:,} MW")
    print(f"  Solar Distribuída: {val_solar_dist:,} MW")
    
    resultado2 = calcular_despacho_probabilistico(
        limite_hidro, limite_hidro_reserv, val_carga,
        val_eolica, val_solar_total, val_inflexterm,
        ENA_arm, mes, hora, is_weekday, min_hidro_reserv,
        val_gersolar_centralizada=val_solar_cent,
        val_gersolar_distribuida=val_solar_dist
    )
    
    print(f"\nResultados:")
    print(f"  Curtailment Total:      {resultado2['curtailment']:>10,.0f} MW")
    print(f"  Curtailment Eólica:     {resultado2['curtailment_eolica']:>10,.0f} MW")
    print(f"  Curtailment Solar Cent: {resultado2['curtailment_solar_cent']:>10,.0f} MW")
    print(f"  Curtailment Solar Dist: {resultado2['curtailment_solar_dist']:>10,.0f} MW")
    
    print(f"\nGerações pós-curtailment:")
    print(f"  Eólica:            {resultado2['val_gereolica_depois_corte']:>10,.0f} MW")
    print(f"  Solar Centralizada:{resultado2.get('val_gersolar_cent_depois_corte', 0):>10,.0f} MW")
    print(f"  Solar Distribuída: {resultado2.get('val_gersolar_dist_depois_corte', 0):>10,.0f} MW")
    
    # Validação
    print(f"\nValidações:")
    
    # 1. Eólica e centralizada devem estar zeradas ou próximas de zero
    if resultado2['val_gereolica_depois_corte'] < 1 and resultado2.get('val_gersolar_cent_depois_corte', 1) < 1:
        print(f"  [OK] Eólica e Solar Centralizada foram zeradas primeiro")
    else:
        print(f"  [ERRO] Eólica ({resultado2['val_gereolica_depois_corte']:.0f}) e/ou Centralizada ({resultado2.get('val_gersolar_cent_depois_corte', 0):.0f}) não foram zeradas")
    
    # 2. Solar distribuída deve ter curtailment
    if resultado2['curtailment_solar_dist'] > 0:
        print(f"  [OK] Solar Distribuída foi cortada após zerar prioridade 1")
        print(f"      Curtailment distribuída: {resultado2['curtailment_solar_dist']:,.0f} MW")
    else:
        print(f"  [INFO] Solar Distribuída não precisou ser cortada")
    
    # 3. Soma deve bater
    curtailment_soma = (resultado2['curtailment_eolica'] + 
                        resultado2['curtailment_solar_cent'] + 
                        resultado2['curtailment_solar_dist'])
    
    if abs(curtailment_soma - resultado2['curtailment']) < 0.1:
        print(f"  [OK] Soma de curtailments bate com total")
    else:
        print(f"  [ERRO] Soma não bate! Soma={curtailment_soma:.0f}, Total={resultado2['curtailment']:.0f}")
    
    print("\n" + "-"*90)
    print("  CENÁRIO 3: Sem Curtailment")
    print("-"*90)
    
    # Sem excesso - nenhum curtailment
    val_carga = 80000
    val_eolica = 10000
    val_solar_cent = 3000
    val_solar_dist = 6000
    val_solar_total = val_solar_cent + val_solar_dist
    
    resultado3 = calcular_despacho_probabilistico(
        limite_hidro, limite_hidro_reserv, val_carga,
        val_eolica, val_solar_total, val_inflexterm,
        ENA_arm, mes, hora, is_weekday, min_hidro_reserv,
        val_gersolar_centralizada=val_solar_cent,
        val_gersolar_distribuida=val_solar_dist
    )
    
    print(f"\nResultados:")
    print(f"  Curtailment Total:      {resultado3['curtailment']:>10,.0f} MW")
    print(f"  Curtailment Eólica:     {resultado3['curtailment_eolica']:>10,.0f} MW")
    print(f"  Curtailment Solar Cent: {resultado3['curtailment_solar_cent']:>10,.0f} MW")
    print(f"  Curtailment Solar Dist: {resultado3['curtailment_solar_dist']:>10,.0f} MW")
    
    if resultado3['curtailment'] == 0:
        print(f"\n[OK] Nenhum curtailment (correto - carga suficiente)")
    else:
        print(f"\n[ERRO] Houve curtailment quando não deveria!")
    
    # Resumo final
    print("\n" + "="*90)
    print("  RESUMO DOS TESTES")
    print("="*90)
    
    testes_ok = 0
    total_testes = 3
    
    # Teste 1: Distribuída preservada em curtailment pequeno
    if resultado['curtailment_solar_dist'] == 0:
        print(f"\n[OK] Teste 1: Distribuída preservada em curtailment pequeno")
        testes_ok += 1
    else:
        print(f"\n[FALHA] Teste 1")
    
    # Teste 2: Prioridade 1 zerada antes de cortar distribuída
    if (resultado2['curtailment_solar_dist'] > 0 and 
        resultado2['val_gereolica_depois_corte'] < 1 and 
        resultado2.get('val_gersolar_cent_depois_corte', 1) < 1):
        print(f"[OK] Teste 2: Cascata funcionando (prioridade 1 zerada primeiro)")
        testes_ok += 1
    else:
        print(f"[FALHA] Teste 2")
    
    # Teste 3: Sem curtailment quando não necessário
    if resultado3['curtailment'] == 0:
        print(f"[OK] Teste 3: Sem curtailment quando desnecessário")
        testes_ok += 1
    else:
        print(f"[FALHA] Teste 3")
    
    print(f"\n{testes_ok}/{total_testes} testes passaram")
    
    if testes_ok == total_testes:
        print(f"\n[OK] Lógica de curtailment em cascata funcionando corretamente!")
    else:
        print(f"\n[AVISO] Alguns testes falharam. Revisar implementação.")
    
    print("\n" + "="*90)

if __name__ == '__main__':
    testar_curtailment_cascata()

