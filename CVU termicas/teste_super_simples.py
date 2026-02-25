"""
Teste super simples para identificar onde está travando
"""

print("=== INICIANDO TESTE ===")

# Teste 1: Importações básicas
print("1. Testando importações...")
import pandas as pd
import yaml
from pathlib import Path
print("   ✓ Importações OK")

# Teste 2: Diretório atual
print("\n2. Testando diretório atual...")
current_dir = Path.cwd()
print(f"   Diretório atual: {current_dir}")

# Teste 3: Procurar CVU termicas
print("\n3. Procurando CVU termicas...")
cvu_dir = current_dir / "CVU termicas"
if cvu_dir.exists():
    print(f"   ✓ CVU termicas encontrado: {cvu_dir}")
else:
    print("   ✗ CVU termicas não encontrado")

# Teste 4: Verificar arquivos
print("\n4. Verificando arquivos...")
if cvu_dir.exists():
    config_file = cvu_dir / "config.yaml"
    if config_file.exists():
        print(f"   ✓ config.yaml encontrado")
        
        # Teste 5: Carregar config
        print("\n5. Carregando configuração...")
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            print(f"   ✓ Configuração carregada")
            
            # Teste 6: Verificar raw_data
            raw_data_path = cvu_dir / config['paths']['raw_data']
            print(f"\n6. Raw data path: {raw_data_path}")
            
            if raw_data_path.exists():
                print("   ✓ Raw data path existe")
                
                # Teste 7: Listar arquivos
                print("\n7. Listando arquivos...")
                files = list(raw_data_path.iterdir())
                print(f"   Arquivos encontrados: {len(files)}")
                
                # Teste 8: Verificar arquivo de capacidade
                capacity_file = raw_data_path / "CAPACIDADE_GERACAO.parquet"
                if capacity_file.exists():
                    print(f"   ✓ CAPACIDADE_GERACAO.parquet existe")
                    
                    # Teste 9: Tentar ler parquet
                    print("\n9. Tentando ler parquet...")
                    try:
                        df = pd.read_parquet(capacity_file)
                        print(f"   ✓ Parquet lido: {len(df)} registros")
                    except Exception as e:
                        print(f"   ✗ Erro ao ler parquet: {e}")
                else:
                    print("   ✗ CAPACIDADE_GERACAO.parquet não encontrado")
            else:
                print("   ✗ Raw data path não existe")
        except Exception as e:
            print(f"   ✗ Erro ao carregar config: {e}")
    else:
        print("   ✗ config.yaml não encontrado")
else:
    print("   ✗ CVU termicas não encontrado")

print("\n=== TESTE CONCLUÍDO ===") 