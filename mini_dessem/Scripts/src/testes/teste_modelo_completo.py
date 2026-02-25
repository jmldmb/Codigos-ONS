"""
Script de teste pequeno para validar o modelo completo do Mini DESSEM

Teste rápido com:
- Poucos meses (ex: Janeiro e Julho de 2024)
- Poucos cenários (5-10)
- Validação dos samples calibrados (eólica, solar, carga)
"""

import sys
from pathlib import Path
from datetime import datetime

# Adicionar o diretório src ao path (subir dois níveis: testes -> src -> Scripts -> src)
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

from mini_dessem.simulation import run_simulation
from mini_dessem.pricing import carregar_pilha_termica
from mini_dessem.config import OUTPUT_DIR

def main():
    """Função principal do teste."""
    print("=" * 80)
    print("  TESTE DO MODELO COMPLETO - Mini DESSEM")
    print("=" * 80)
    print(f"\nData/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[CONFIG] Configuração do teste:")
    print("  - Anos: 2024, 2025")
    print("  - Meses: Janeiro (1) e Julho (7)")
    print("  - Cenários: 5 por mês/ano")
    print("  - Tipo de dia: Mês completo (dias úteis + finais de semana)")
    print("\n" + "=" * 80)
    
    # Parâmetros do teste
    num_simulations = 5  # Poucos cenários para teste rápido
    anos = [2024, 2025]  # 2 anos
    meses = [1, 7]  # Janeiro e Julho (representam períodos diferentes)
    
    print("\n[1/3] Carregando pilha térmica...")
    try:
        pilha_termica = carregar_pilha_termica()
        print(f"   [OK] Pilha térmica carregada: {len(pilha_termica)} usinas")
    except Exception as e:
        print(f"   [ERRO] Não foi possível carregar pilha térmica: {e}")
        return 1
    
    print("\n[2/3] Executando simulação...")
    print("   Obs: Cada cenário simula o mês completo (dias úteis + FDS)")
    print()
    
    try:
        df_resultados = run_simulation(
            num_simulations=num_simulations,
            anos=anos,
            meses=meses,
            is_weekday=True,  # Ignorado (simulação sempre faz mês completo)
            pilha_termica=pilha_termica,
            verbose=True
        )
        
        if len(df_resultados) == 0:
            print("\n[ERRO] Nenhum resultado foi gerado!")
            return 1
        
        print("\n" + "=" * 80)
        print("[3/3] ANÁLISE DOS RESULTADOS")
        print("=" * 80)
        
        # Informações gerais
        print(f"\nTotal de registros horários: {len(df_resultados):,}")
        print(f"Cenários realizados: {df_resultados['simulacao'].nunique()}")
        print(f"Anos simulados: {sorted(df_resultados['ano'].unique())}")
        print(f"Meses simulados: {sorted(df_resultados['mes'].unique())}")
        
        # Distribuição por tipo de dia
        if 'tipo_dia' in df_resultados.columns:
            print("\nDistribuição por tipo de dia:")
            registros_util = (df_resultados['tipo_dia'] == 'util').sum()
            registros_fds = (df_resultados['tipo_dia'] == 'fds').sum()
            pct_util = (registros_util / len(df_resultados)) * 100
            pct_fds = (registros_fds / len(df_resultados)) * 100
            print(f"   Dias úteis: {registros_util:,} horas ({pct_util:.1f}%)")
            print(f"   Finais de semana: {registros_fds:,} horas ({pct_fds:.1f}%)")
        
        # Estatísticas de geração
        print("\n" + "-" * 80)
        print("GERAÇÃO (valores médios)")
        print("-" * 80)
        print(f"   Eólica: {df_resultados['val_gereolica'].mean():,.1f} MW")
        print(f"      Min: {df_resultados['val_gereolica'].min():,.1f} MW")
        print(f"      Max: {df_resultados['val_gereolica'].max():,.1f} MW")
        print(f"      Std: {df_resultados['val_gereolica'].std():,.1f} MW")
        
        print(f"\n   Solar: {df_resultados['val_gersolar'].mean():,.1f} MW")
        print(f"      Min: {df_resultados['val_gersolar'].min():,.1f} MW")
        print(f"      Max: {df_resultados['val_gersolar'].max():,.1f} MW")
        print(f"      Std: {df_resultados['val_gersolar'].std():,.1f} MW")
        
        print(f"\n   Carga: {df_resultados['val_carga'].mean():,.1f} MW")
        print(f"      Min: {df_resultados['val_carga'].min():,.1f} MW")
        print(f"      Max: {df_resultados['val_carga'].max():,.1f} MW")
        print(f"      Std: {df_resultados['val_carga'].std():,.1f} MW")
        
        # Estatísticas de despacho
        print("\n" + "-" * 80)
        print("DESPACHO")
        print("-" * 80)
        print(f"   Térmica: {df_resultados['val_term_despacho'].mean():,.1f} MW")
        print(f"      Min: {df_resultados['val_term_despacho'].min():,.1f} MW")
        print(f"      Max: {df_resultados['val_term_despacho'].max():,.1f} MW")
        
        print(f"\n   Hidro Total: {df_resultados['val_gerhidro_total'].mean():,.1f} MW")
        print(f"      Reservatório: {df_resultados['val_gerhidro_reservatorio'].mean():,.1f} MW")
        print(f"      Fio d'água: {df_resultados['val_gerhidro_fd'].mean():,.1f} MW")
        
        # Curtailment
        curtailment_total = df_resultados['curtailment'].sum()
        curtailment_ocorrencias = (df_resultados['curtailment'] > 0).sum()
        curtailment_pct = (curtailment_ocorrencias / len(df_resultados)) * 100
        print(f"\n   Curtailment:")
        print(f"      Total: {curtailment_total:,.0f} MWh")
        print(f"      Ocorrências: {curtailment_ocorrencias:,} horas ({curtailment_pct:.2f}%)")
        
        # PLD
        print("\n" + "-" * 80)
        print("PLD (Preço de Liquidação das Diferenças)")
        print("-" * 80)
        print(f"   Média: R$ {df_resultados['pld'].mean():.2f}/MWh")
        print(f"   Mediana: R$ {df_resultados['pld'].median():.2f}/MWh")
        print(f"   Mínimo: R$ {df_resultados['pld'].min():.2f}/MWh")
        print(f"   Máximo: R$ {df_resultados['pld'].max():.2f}/MWh")
        print(f"   Desvio: R$ {df_resultados['pld'].std():.2f}/MWh")
        
        # Distribuição de PLD
        print("\n   Distribuição do PLD:")
        print(f"      P10: R$ {df_resultados['pld'].quantile(0.10):.2f}/MWh")
        print(f"      P25: R$ {df_resultados['pld'].quantile(0.25):.2f}/MWh")
        print(f"      P50: R$ {df_resultados['pld'].quantile(0.50):.2f}/MWh")
        print(f"      P75: R$ {df_resultados['pld'].quantile(0.75):.2f}/MWh")
        print(f"      P90: R$ {df_resultados['pld'].quantile(0.90):.2f}/MWh")
        
        # Análise por mês
        print("\n" + "-" * 80)
        print("ANÁLISE POR MÊS/ANO")
        print("-" * 80)
        
        for ano in sorted(df_resultados['ano'].unique()):
            for mes in sorted(df_resultados[df_resultados['ano'] == ano]['mes'].unique()):
                df_mes = df_resultados[(df_resultados['ano'] == ano) & (df_resultados['mes'] == mes)]
                
                nome_mes = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                           "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes]
                
                print(f"\n{nome_mes}/{ano}:")
                print(f"   Registros: {len(df_mes):,} horas")
                print(f"   Eólica média: {df_mes['val_gereolica'].mean():,.1f} MW")
                print(f"   Solar média: {df_mes['val_gersolar'].mean():,.1f} MW")
                print(f"   Carga média: {df_mes['val_carga'].mean():,.1f} MW")
                print(f"   PLD médio: R$ {df_mes['pld'].mean():.2f}/MWh")
                print(f"   Curtailment: {df_mes['curtailment'].sum():,.0f} MWh")
        
        # Verificar erros de balanceamento
        erros = df_resultados['val_erro'].sum()
        if erros > 0:
            print(f"\n[AVISO] {erros} erros de balanceamento detectados")
        
        # Salvar resultados
        print("\n" + "=" * 80)
        print("SALVANDO RESULTADOS")
        print("=" * 80)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Salvar em Parquet
        parquet_file = output_dir / f'teste_modelo_{timestamp}.parquet'
        df_resultados.to_parquet(parquet_file, index=False, compression='snappy')
        tamanho_mb = parquet_file.stat().st_size / (1024 * 1024)
        print(f"\n[OK] Salvo em Parquet: {parquet_file.name} ({tamanho_mb:.2f} MB)")
        
        # Salvar em Excel
        try:
            excel_file = output_dir / f'teste_modelo_{timestamp}.xlsx'
            df_resultados.to_excel(excel_file, index=False)
            tamanho_mb = excel_file.stat().st_size / (1024 * 1024)
            print(f"[OK] Salvo em Excel: {excel_file.name} ({tamanho_mb:.2f} MB)")
        except Exception as e:
            print(f"[AVISO] Não foi possível salvar Excel: {e}")
        
        print("\n" + "=" * 80)
        print("  [OK] TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
        print("\nPróximos passos:")
        print("  1. Verifique se os valores de geração estão realistas")
        print("  2. Analise a distribuição do PLD")
        print("  3. Se OK, aumente o número de cenários e meses para simulação completa")
        print("  4. Use o arquivo main.py para simulações maiores")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n[AVISO] Teste interrompido pelo usuário")
        return 1
        
    except Exception as e:
        print(f"\n\n[ERRO] Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


