"""
Teste rápido: Executar uma simulação pequena para verificar que ENA real está funcionando
"""

import sys
from pathlib import Path

# Adicionar diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mini_dessem.simulation import run_simulation

def main():
    print("\n" + "="*70)
    print("TESTE RÁPIDO: Simulação com ENA Real")
    print("="*70 + "\n")
    
    print("Executando simulação pequena...")
    print("  - Ano: 2025")
    print("  - Mês: Janeiro (com dados reais de ENA)")
    print("  - Cenários: 1")
    print()
    
    # Executar simulação pequena
    df = run_simulation(
        num_simulations=1,
        anos=[2025],
        meses=[1],
        verbose=True
    )
    
    print("\n" + "="*70)
    print("RESULTADO:")
    print("="*70)
    
    if len(df) > 0:
        print(f"\n✅ Simulação executada com sucesso!")
        print(f"   Total de registros: {len(df):,}")
        print(f"   ENA usado: {df['ENA_arm'].iloc[0]:,.0f} MW")
        print()
        
        # Verificar se é o valor real
        ena_esperado_real = 96473  # Sabemos que janeiro/2025 tem valor real
        ena_usado = df['ENA_arm'].iloc[0]
        
        if abs(ena_usado - ena_esperado_real) < 1:
            print("✅ CONFIRMADO: Sistema está usando dados REAIS de ENA!")
            print(f"   Valor esperado (real): {ena_esperado_real:,.0f} MW")
            print(f"   Valor usado:           {ena_usado:,.0f} MW")
        else:
            print("⚠️ AVISO: Valor de ENA diferente do esperado")
            print(f"   Valor esperado (real): {ena_esperado_real:,.0f} MW")
            print(f"   Valor usado:           {ena_usado:,.0f} MW")
    else:
        print("\n❌ Erro: Simulação não gerou resultados")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()

