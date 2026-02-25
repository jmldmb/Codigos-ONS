#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INSTALADOR DE DEPENDÊNCIAS - PREÇOS DE ENERGIA BR
=================================================

Script para instalar automaticamente as dependências necessárias.
"""

import subprocess
import sys
from pathlib import Path

def instalar_dependencia(pacote):
    """Instala uma dependência específica."""
    try:
        print(f"Instalando {pacote}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", pacote
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f" {pacote} instalado com sucesso")
            return True
        else:
            print(f" Erro ao instalar {pacote}: {result.stderr}")
            return False
            
    except Exception as e:
        print(f" Erro ao instalar {pacote}: {e}")
        return False

def main():
    """Função principal."""
    print(" INSTALADOR DE DEPENDÊNCIAS")
    print("=" * 50)
    
    # Lista de dependências essenciais
    dependencias = [
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "requests>=2.28.0",
        "urllib3>=1.26.0",
        "jinja2>=3.0.0",
        "PyYAML>=6.0",
        "pyarrow>=10.0.0"
    ]
    
    sucessos = 0
    falhas = 0
    
    for dependencia in dependencias:
        if instalar_dependencia(dependencia):
            sucessos += 1
        else:
            falhas += 1
    
    print("\n" + "=" * 50)
    print(" RESUMO DA INSTALAÇÃO")
    print("=" * 50)
    print(f" Sucessos: {sucessos}")
    print(f" Falhas: {falhas}")
    
    if falhas == 0:
        print("\n Todas as dependências foram instaladas com sucesso!")
        print(" Você pode agora executar o orquestrador:")
        print("   python orchestrator.py")
        return True
    else:
        print(f"\n {falhas} dependência(s) falharam na instalação.")
        print("Tente instalar manualmente as que falharam.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 