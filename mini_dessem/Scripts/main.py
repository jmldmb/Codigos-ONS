"""
Script principal para executar simulações do Mini DESSEM

Este script executa simulações Monte Carlo do sistema energético brasileiro
e gera análises e visualizações dos resultados.

Uso:
    python main.py [opções]

Exemplos:
    # Executar com configurações padrão
    python main.py
    
    # Executar com número personalizado de simulações
    python main.py --num-simulations 200
    
    # Executar para anos específicos
    python main.py --anos 2024 2025 2026
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Adicionar o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mini_dessem.simulation import run_simulation
from mini_dessem.pricing import carregar_pilha_termica
from mini_dessem.config import OUTPUT_DIR, DEFAULT_NUM_SIMULATIONS, ANOS_SIMULAR, MESES_SIMULAR
from mini_dessem.data import eh_dado_historico


def _imprimir_info_dados(anos, meses):
    """Imprime informação sobre quais dados são históricos vs projetados."""
    print("\n" + "=" * 70)
    print("  FONTE DOS DADOS: HISTORICO vs PROJETADO")
    print("=" * 70)
    
    # Agrupar por ano
    for ano in sorted(anos):
        meses_historicos = []
        meses_projetados = []
        
        for mes in sorted(meses):
            if eh_dado_historico(ano, mes):
                meses_historicos.append(mes)
            else:
                meses_projetados.append(mes)
        
        if meses_historicos and meses_projetados:
            # Ano misto (parte histórico, parte projeção)
            print(f"\n{ano}:")
            print(f"   [HISTORICO] Meses: {meses_historicos}")
            print(f"   [PROJECAO]  Meses: {meses_projetados}")
        elif meses_historicos:
            # Só histórico
            print(f"\n{ano}: [HISTORICO] - Todos os meses")
        elif meses_projetados:
            # Só projeção
            print(f"\n{ano}: [PROJECAO] - Todos os meses")
    
    print()


def parse_arguments():
    """Parse argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description='Mini DESSEM - Simulação de Despacho Energético',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--num-simulations', '-n',
        type=int,
        default=DEFAULT_NUM_SIMULATIONS,
        help='Número de simulações Monte Carlo por mês/ano'
    )
    
    parser.add_argument(
        '--anos',
        nargs='+',
        type=int,
        default=ANOS_SIMULAR,
        help='Anos para simular (ex: 2024 2025 2026)'
    )
    
    parser.add_argument(
        '--meses',
        nargs='+',
        type=int,
        default=MESES_SIMULAR,
        help='Meses para simular (ex: 1 2 3 para Jan-Mar)'
    )
    
    parser.add_argument(
        '--weekday',
        action='store_true',
        default=True,
        help='Simular dias de semana'
    )
    
    parser.add_argument(
        '--weekend',
        action='store_true',
        help='Simular fins de semana (sobrescreve --weekday)'
    )
    
    parser.add_argument(
        '--pilha-termica',
        type=str,
        help='Caminho para arquivo Excel com pilha térmica'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=str(OUTPUT_DIR),
        help='Diretório para salvar resultados'
    )
    
    
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso (sem output de progresso)'
    )
    
    return parser.parse_args()


def main():
    """Função principal."""
    # Configurar encoding para Windows
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass
    
    # Parse argumentos
    args = parse_arguments()
    
    # Configurar output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    verbose = not args.quiet
    
    # Banner
    if verbose:
        print("\n" + "=" * 70)
        print("  Mini DESSEM - Simulacao de Despacho Energetico")
        print("=" * 70)
        print(f"\nData/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Diretorio de saida: {output_dir}")
        print(f"Simulacoes por mes: {args.num_simulations}")
        print(f"Anos: {args.anos}")
        print(f"Meses: {args.meses}")
        print(f"Tipo de dia: {'Fim de semana' if args.weekend else 'Dia util'}")
        print()
        
        # Mostrar quais dados são históricos vs projetados
        _imprimir_info_dados(args.anos, args.meses)
    
    # Carregar pilha térmica
    if verbose:
        print("=" * 70)
        print("  [1/3] CARREGANDO PILHA TERMICA")
        print("=" * 70)
    
    try:
        if args.pilha_termica:
            if verbose:
                print(f"   Arquivo: {args.pilha_termica}")
            pilha_termica = carregar_pilha_termica(args.pilha_termica)
        else:
            if verbose:
                print("   Usando pilha termica padrao...")
            pilha_termica = carregar_pilha_termica()
        
        if verbose:
            print(f"   [OK] Pilha termica carregada com {len(pilha_termica)} registros")
            print()
    except Exception as e:
        print(f"   [ERRO] Falha ao carregar pilha termica: {e}")
        return 1
    
    # Executar simulação
    try:
        if verbose:
            print("=" * 70)
            print("  [2/3] EXECUTANDO SIMULACAO MONTE CARLO")
            print("=" * 70)
            print()
        
        df_resultados = run_simulation(
            num_simulations=args.num_simulations,
            anos=args.anos,
            meses=args.meses,
            is_weekday=not args.weekend,
            pilha_termica=pilha_termica,
            verbose=verbose
        )
        
        # Timestamp único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. SALVAR EM PARQUET (formato eficiente)
        if verbose:
            print(f"\n{'='*70}")
            print("  [3/3] SALVANDO RESULTADOS")
            print(f"{'='*70}")
        
        parquet_file = output_dir / f'resultados_simulacao_{timestamp}.parquet'
        
        if verbose:
            print(f"\n[1/2] Salvando em Parquet (formato eficiente)...")
            print(f"      Arquivo: {parquet_file.name}")
            print(f"      Compactacao: Snappy")
        
        df_resultados.to_parquet(parquet_file, index=False, compression='snappy')
        
        if verbose:
            tamanho_parquet = parquet_file.stat().st_size / (1024 * 1024)
            print(f"      [OK] Arquivo salvo! Tamanho: {tamanho_parquet:.1f} MB")
        
        # Verificar se há resultados
        if len(df_resultados) == 0:
            if verbose:
                print("\n" + "=" * 70)
                print("  [AVISO] NENHUM RESULTADO FOI GERADO!")
                print("=" * 70)
            return 1
        
        # 2. GERAR ESTATÍSTICAS E GRÁFICOS
        if verbose:
            print(f"\n[2] Gerando estatísticas resumidas...")
            print(f"\n{'='*70}")
            print("  ESTATISTICAS RESUMIDAS")
            print(f"{'='*70}")
            print(f"\nTotal de registros: {len(df_resultados):,}")
            print(f"Simulacoes realizadas: {df_resultados['simulacao'].nunique()}")
            print(f"Anos simulados: {sorted(df_resultados['ano'].unique())}")
            print(f"Meses simulados: {sorted(df_resultados['mes'].unique())}")
            
            # Estatísticas por tipo de dia
            if 'tipo_dia' in df_resultados.columns:
                registros_util = (df_resultados['tipo_dia'] == 'util').sum()
                registros_fds = (df_resultados['tipo_dia'] == 'fds').sum()
                pct_util = (registros_util / len(df_resultados)) * 100
                pct_fds = (registros_fds / len(df_resultados)) * 100
                print(f"\nDistribuicao:")
                print(f"   Dias uteis: {registros_util:,} ({pct_util:.1f}%)")
                print(f"   Finais de semana: {registros_fds:,} ({pct_fds:.1f}%)")
            
            print("\nGeração:")
            print(f"   Eolica media: {df_resultados['val_gereolica'].mean():.2f} MW")
            print(f"   Solar media: {df_resultados['val_gersolar'].mean():.2f} MW")
            print(f"   Carga media: {df_resultados['val_carga'].mean():.2f} MW")
            
            print("\nPLD:")
            print(f"   Media: R$ {df_resultados['pld'].mean():.2f}/MWh")
            print(f"   Mediana: R$ {df_resultados['pld'].median():.2f}/MWh")
            print(f"   Min/Max: R$ {df_resultados['pld'].min():.2f} / R$ {df_resultados['pld'].max():.2f}/MWh")
            
            print("\nDespacho Termico:")
            print(f"   Media: {df_resultados['val_term_despacho'].mean():.2f} MW")
            print(f"   Maximo: {df_resultados['val_term_despacho'].max():.2f} MW")
            
            print("\nCurtailment:")
            curtailment_total = df_resultados['curtailment'].sum()
            curtailment_ocorrencias = (df_resultados['curtailment'] > 0).sum()
            curtailment_pct = (curtailment_ocorrencias / len(df_resultados)) * 100
            print(f"   Total: {curtailment_total:,.0f} MWh")
            print(f"   Ocorrencias: {curtailment_ocorrencias:,} ({curtailment_pct:.2f}% das horas)")
            
            print(f"\nErros de balanceamento: {df_resultados['val_erro'].sum()}")
        
        # 3. SALVAR EM EXCEL (formato de compatibilidade)
        if verbose:
            print(f"\n[2/2] Salvando em Excel (formato de compatibilidade)...")
        
        excel_file = output_dir / f'resultados_simulacao_{timestamp}.xlsx'
        
        try:
            if verbose:
                print(f"      Arquivo: {excel_file.name}")
                print(f"      [  ...  ] Processando (pode demorar)...", end="", flush=True)
            
            df_resultados.to_excel(excel_file, index=False)
            
            if verbose:
                print(f"\r      [  OK   ] Processando (pode demorar)...                    ")
                tamanho_excel = excel_file.stat().st_size / (1024 * 1024)
                print(f"      [OK] Arquivo salvo! Tamanho: {tamanho_excel:.1f} MB")
        except Exception as e:
            if verbose:
                print(f"\r      [AVISO] Nao foi possivel salvar Excel: {e}                    ")
                print(f"               Use o arquivo Parquet para analises.")
        
        if verbose:
            print("\n" + "=" * 70)
            print("  [OK] SIMULACAO CONCLUIDA COM SUCESSO!")
            print("=" * 70)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n[AVISO] Simulacao interrompida pelo usuario.")
        return 1
    
    except Exception as e:
        print(f"\n\n[ERRO] Erro durante a simulacao: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

