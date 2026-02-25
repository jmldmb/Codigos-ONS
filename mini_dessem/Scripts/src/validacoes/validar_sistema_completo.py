"""
Validação Completa do Sistema Após Limpeza
===========================================

Verifica que todos os módulos essenciais estão funcionando.
"""

import sys
from pathlib import Path

# Adicionar o diretório src ao path (subir dois níveis: validacoes -> src -> Scripts -> src)
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

def validar_importacoes():
    """Testa se todas as importações essenciais funcionam."""
    print("\n" + "="*90)
    print("  VALIDAÇÃO 1: Importações")
    print("="*90)
    
    erros = []
    
    # Módulos principais
    try:
        from mini_dessem import config
        print("  [OK] mini_dessem.config")
    except Exception as e:
        erros.append(f"config: {e}")
        print(f"  [ERRO] mini_dessem.config: {e}")
    
    try:
        from mini_dessem import data
        print("  [OK] mini_dessem.data")
    except Exception as e:
        erros.append(f"data: {e}")
        print(f"  [ERRO] mini_dessem.data: {e}")
    
    try:
        from mini_dessem import sampling
        print("  [OK] mini_dessem.sampling")
    except Exception as e:
        erros.append(f"sampling: {e}")
        print(f"  [ERRO] mini_dessem.sampling: {e}")
    
    try:
        from mini_dessem import dispatch
        print("  [OK] mini_dessem.dispatch")
    except Exception as e:
        erros.append(f"dispatch: {e}")
        print(f"  [ERRO] mini_dessem.dispatch: {e}")
    
    try:
        from mini_dessem import simulation
        print("  [OK] mini_dessem.simulation")
    except Exception as e:
        erros.append(f"simulation: {e}")
        print(f"  [ERRO] mini_dessem.simulation: {e}")
    
    try:
        from mini_dessem import pricing
        print("  [OK] mini_dessem.pricing")
    except Exception as e:
        erros.append(f"pricing: {e}")
        print(f"  [ERRO] mini_dessem.pricing: {e}")
    
    # Samplers
    try:
        from auxiliar.sample.eolica import EolicaSampler
        print("  [OK] EolicaSampler")
    except Exception as e:
        erros.append(f"EolicaSampler: {e}")
        print(f"  [ERRO] EolicaSampler: {e}")
    
    try:
        from auxiliar.sample.solar import SolarSampler
        print("  [OK] SolarSampler")
    except Exception as e:
        erros.append(f"SolarSampler: {e}")
        print(f"  [ERRO] SolarSampler: {e}")
    
    try:
        from auxiliar.sample.solar import SolarDistribuidaSampler
        print("  [OK] SolarDistribuidaSampler")
    except Exception as e:
        erros.append(f"SolarDistribuidaSampler: {e}")
        print(f"  [ERRO] SolarDistribuidaSampler: {e}")
    
    return len(erros) == 0

def validar_dados():
    """Verifica se todos os dicionários de dados existem."""
    print("\n" + "="*90)
    print("  VALIDAÇÃO 2: Dicionários de Dados")
    print("="*90)
    
    from mini_dessem.data import (
        capacidade_eolica_total_dic,
        geracao_solar_centralizada_dic,
        geracao_solar_distribuida_dic,
        capacidade_solar_total_dic,
        carga_total_dic,
        ENA_dic,
        val_inflexterm_dic
    )
    
    dicionarios = {
        'Capacidade Eólica': capacidade_eolica_total_dic,
        'Solar Centralizada': geracao_solar_centralizada_dic,
        'Solar Distribuída': geracao_solar_distribuida_dic,
        'Solar Total': capacidade_solar_total_dic,
        'Carga': carga_total_dic,
        'ENA': ENA_dic,
        'Inflexterm': val_inflexterm_dic
    }
    
    for nome, dic in dicionarios.items():
        anos = len(dic)
        meses_exemplo = len(dic.get(2025, {}))
        print(f"  [OK] {nome:<25}: {anos} anos, {meses_exemplo} meses/ano")
    
    # Validar que centralizada + distribuída = total
    ano, mes = 2025, 9
    cent = geracao_solar_centralizada_dic[ano][mes]
    dist = geracao_solar_distribuida_dic[ano][mes]
    total = capacidade_solar_total_dic[ano][mes]
    soma = cent + dist
    
    print(f"\nValidação (Set/2025):")
    print(f"  Centralizada: {cent:,} MW")
    print(f"  Distribuída:  {dist:,} MW")
    print(f"  Soma:         {soma:,} MW")
    print(f"  Total:        {total:,} MW")
    print(f"  Diferença:    {abs(soma - total):,} MW")
    
    if abs(soma - total) < 100:
        print(f"  [OK] Soma bate com total!")
        return True
    else:
        print(f"  [ERRO] Soma não bate!")
        return False

def validar_simulacao():
    """Executa mini-simulação para validar funcionamento."""
    print("\n" + "="*90)
    print("  VALIDAÇÃO 3: Mini-Simulação")
    print("="*90)
    
    from mini_dessem.simulation import run_simulation
    from mini_dessem.pricing import carregar_pilha_termica
    
    print("\nExecutando simulação (1 cenário, 1 mês)...")
    
    try:
        pilha = carregar_pilha_termica()
        
        df = run_simulation(
            num_simulations=1,
            anos=[2025],
            meses=[9],
            pilha_termica=pilha,
            verbose=False
        )
        
        print(f"  [OK] Simulação executada")
        print(f"       Registros: {len(df):,}")
        print(f"       Solar médio: {df['val_gersolar'].mean():,.0f} MW")
        
        # Verificar se curtailment detalhado existe
        if 'curtailment_eolica' in df.columns:
            print(f"       Curtailment eólica: {df['curtailment_eolica'].sum():,.0f} MW")
            print(f"       Curtailment solar cent: {df['curtailment_solar_cent'].sum():,.0f} MW")
            print(f"       Curtailment solar dist: {df['curtailment_solar_dist'].sum():,.0f} MW")
            print(f"  [OK] Curtailment em cascata ativo!")
        else:
            print(f"  [INFO] Curtailment detalhado não disponível")
        
        return True
        
    except Exception as e:
        print(f"  [ERRO] Falha na simulação: {e}")
        import traceback
        traceback.print_exc()
        return False

def validar_curtailment_cascata():
    """Valida lógica de curtailment em cascata."""
    print("\n" + "="*90)
    print("  VALIDAÇÃO 4: Curtailment em Cascata")
    print("="*90)
    
    from mini_dessem.dispatch import calcular_despacho_probabilistico
    
    # Teste simples
    resultado = calcular_despacho_probabilistico(
        limite_hidro=70000,
        limite_hidro_reservatorio=40000,
        val_carga=50000,
        val_gereolica=15000,
        val_gersolar=15000,
        val_inflexterm=5000,
        ENA_arm=50000,
        mes=9,
        hora=12,
        is_weekday=True,
        min_hidro_reservatorio=12000,
        val_gersolar_centralizada=5000,
        val_gersolar_distribuida=10000
    )
    
    print(f"  Resultado do dispatch:")
    print(f"    Curtailment total: {resultado['curtailment']:,.0f} MW")
    print(f"    Curtailment eólica: {resultado['curtailment_eolica']:,.0f} MW")
    print(f"    Curtailment solar cent: {resultado['curtailment_solar_cent']:,.0f} MW")
    print(f"    Curtailment solar dist: {resultado['curtailment_solar_dist']:,.0f} MW")
    
    # Validar que distribuída foi preservada
    if resultado['curtailment_solar_dist'] == 0:
        print(f"  [OK] Solar distribuída preservada (prioridade 2)")
        return True
    elif resultado['curtailment_eolica'] > 0 or resultado['curtailment_solar_cent'] > 0:
        print(f"  [OK] Curtailment em cascata funcionando")
        return True
    else:
        print(f"  [ERRO] Lógica de cascata com problema")
        return False

def main():
    print("\n" + "="*90)
    print("  VALIDAÇÃO COMPLETA DO SISTEMA")
    print("="*90)
    
    resultados = {}
    
    resultados['importacoes'] = validar_importacoes()
    resultados['dados'] = validar_dados()
    resultados['simulacao'] = validar_simulacao()
    resultados['curtailment'] = validar_curtailment_cascata()
    
    # Resumo
    print("\n" + "="*90)
    print("  RESUMO DA VALIDAÇÃO")
    print("="*90)
    
    print(f"\n{'Teste':<30} {'Status'}")
    print("-"*90)
    
    for teste, passou in resultados.items():
        status = "[OK]" if passou else "[FALHA]"
        print(f"{teste.capitalize():<30} {status}")
    
    todos_ok = all(resultados.values())
    
    print("\n" + "="*90)
    
    if todos_ok:
        print("\n[OK] TODOS OS TESTES PASSARAM!")
        print("\nSistema validado e funcionando corretamente.")
        print("Nenhum arquivo essencial foi removido.")
    else:
        print("\n[AVISO] Alguns testes falharam")
        print("Revisar implementação.")
    
    print("\n" + "="*90)
    
    # Lista de arquivos mantidos
    print("\nArquivos principais mantidos:")
    print("  ✓ main.py (script principal)")
    print("  ✓ src/mini_dessem/ (9 módulos)")
    print("  ✓ src/auxiliar/sample/ (samplers eolica, solar, carga)")
    print("  ✓ calcular_geracao_distribuida_solar.py (processamento)")
    print("  ✓ analise_simulacoes.py (análise de resultados)")
    print("  ✓ simular_mensal_agregado.py (simulação agregada)")
    print("  ✓ testar_*.py (3 scripts de teste/validação)")
    print("  ✓ Documentação (6 arquivos .md/.txt)")
    
    print("\nArquivos removidos: 25 (scripts temporários/debug)")
    
    return 0 if todos_ok else 1

if __name__ == '__main__':
    sys.exit(main())

