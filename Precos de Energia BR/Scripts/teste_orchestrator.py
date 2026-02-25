#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TESTE DO ORQUESTRADOR - PREÇOS DE ENERGIA BR
============================================

Script para testar o orquestrador antes da execução completa.
"""

import sys
from pathlib import Path
import logging

# Configurar logging simples
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def testar_estrutura():
    """Testa se a estrutura de arquivos está correta."""
    print(" Testando estrutura de arquivos...")
    
    # Detectar diretório base
    if hasattr(sys, '_getframe'):
        BASE = Path(__file__).resolve().parent
    else:
        BASE = Path.cwd()
    
    # Verificar se estamos no diretório correto
    if BASE.name != "Scripts":
        for parent in BASE.parents:
            scripts_dir = parent / "Scripts"
            if scripts_dir.exists():
                BASE = scripts_dir
                break
    
    ROOT = BASE.parent
    
    # Lista de arquivos necessários
    arquivos_necessarios = [
        BASE / "orchestrator.py",
        BASE / "config.yaml",
        BASE / "plot_utils.py",
        BASE / "data_ingest.py",
        ROOT / "templates" / "report.html.jinja"
    ]
    
    # Lista de diretórios necessários
    diretorios_necessarios = [
        ROOT / "Data" / "processed" / "pld",
        ROOT / "templates",
        ROOT / "charts",
        ROOT / "report_out"
    ]
    
    print(f" BASE: {BASE}")
    print(f" ROOT: {ROOT}")
    
    # Verificar arquivos
    print("\n Verificando arquivos...")
    for arquivo in arquivos_necessarios:
        if arquivo.exists():
            print(f" {arquivo.name}")
        else:
            print(f" {arquivo.name} - NÃO ENCONTRADO")
            return False
    
    # Verificar diretórios
    print("\n Verificando diretórios...")
    for diretorio in diretorios_necessarios:
        if diretorio.exists():
            print(f" {diretorio.name}")
        else:
            print(f" {diretorio.name} - NÃO ENCONTRADO (será criado)")
    
    return True

def testar_imports():
    """Testa se os módulos podem ser importados."""
    print("\n🧪 Testando importações...")
    
    try:
        # Adicionar diretório ao path
        if hasattr(sys, '_getframe'):
            BASE = Path(__file__).resolve().parent
        else:
            BASE = Path.cwd()
        
        if str(BASE) not in sys.path:
            sys.path.append(str(BASE))
        
        # Testar importações
        import yaml
        print(" yaml")
        
        import pandas as pd
        print(" pandas")
        
        import matplotlib.pyplot as plt
        print(" matplotlib")
        
        from jinja2 import Environment, FileSystemLoader
        print(" jinja2")
        
        # Testar módulos do projeto
        import plot_utils
        print(" plot_utils")
        
        from data_ingest import update_all
        print(" data_ingest")
        
        return True
        
    except ImportError as e:
        print(f" Erro de importação: {e}")
        return False

def testar_config():
    """Testa se a configuração pode ser carregada."""
    print("\n Testando configuração...")
    
    try:
        if hasattr(sys, '_getframe'):
            BASE = Path(__file__).resolve().parent
        else:
            BASE = Path.cwd()
        
        config_path = BASE / "config.yaml"
        
        if not config_path.exists():
            print(f" Arquivo de configuração não encontrado: {config_path}")
            return False
        
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        charts = config.get("charts", [])
        print(f" Configuração carregada: {len(charts)} gráficos configurados")
        
        for i, chart in enumerate(charts, 1):
            print(f"   {i}. {chart.get('name', 'N/A')} ({chart.get('kind', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f" Erro ao carregar configuração: {e}")
        return False

def testar_dados():
    """Testa se os dados estão disponíveis."""
    print("\n Testando dados...")
    
    try:
        if hasattr(sys, '_getframe'):
            BASE = Path(__file__).resolve().parent
        else:
            BASE = Path.cwd()
        
        ROOT = BASE.parent
        parq_path = ROOT / "Data" / "processed" / "pld" / "base_master.parquet"
        
        if not parq_path.exists():
            print(f" Arquivo de dados não encontrado: {parq_path}")
            print("   Execute primeiro: python precos_BR_corrigido.py")
            return False
        
        import pandas as pd
        df = pd.read_parquet(parq_path)
        print(f" Dados carregados: {len(df)} registros")
        print(f"   Período: {df['Data'].min()} até {df['Data'].max()}")
        print(f"   Submercados: {df['Submercado'].unique()}")
        
        return True
        
    except Exception as e:
        print(f" Erro ao carregar dados: {e}")
        return False

def main():
    """Função principal de teste."""
    print("🧪 TESTE DO ORQUESTRADOR")
    print("=" * 50)
    
    testes = [
        ("Estrutura de arquivos", testar_estrutura),
        ("Importações", testar_imports),
        ("Configuração", testar_config),
        ("Dados", testar_dados)
    ]
    
    resultados = []
    
    for nome, teste in testes:
        try:
            resultado = teste()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f" Erro no teste '{nome}': {e}")
            resultados.append((nome, False))
    
    # Resumo
    print("\n" + "=" * 50)
    print(" RESUMO DOS TESTES")
    print("=" * 50)
    
    sucessos = 0
    for nome, resultado in resultados:
        status = " PASSOU" if resultado else " FALHOU"
        print(f"{nome}: {status}")
        if resultado:
            sucessos += 1
    
    print(f"\n Resultado: {sucessos}/{len(resultados)} testes passaram")
    
    if sucessos == len(resultados):
        print("\n Todos os testes passaram! O orquestrador está pronto.")
        print(" Execute: python orchestrator.py")
        return True
    else:
        print("\n Alguns testes falharam. Corrija os problemas antes de executar o orquestrador.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 