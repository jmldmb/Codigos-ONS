#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INICIADOR DO SERVIDOR
=====================

Script simples para iniciar o servidor web do orquestrador central.
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def main():
    """Função principal."""
    print("Iniciando Orquestrador Central...")
    print("=" * 50)
    
    # Caminho para o scheduler
    scheduler_path = Path(__file__).parent / "scheduler.py"
    
    try:
        # Iniciar o servidor
        print("Iniciando servidor web...")
        process = subprocess.Popen([
            sys.executable, str(scheduler_path), "--servidor"
        ])
        
        # Aguardar um pouco e abrir o navegador
        time.sleep(2)
        webbrowser.open('http://localhost:8080')
        
        print("Servidor iniciado!")
        print("Interface web aberta em: http://localhost:8080")
        print("Pressione Ctrl+C para parar")
        
        # Manter o processo rodando
        process.wait()
        
    except KeyboardInterrupt:
        print("\nServidor parado pelo usuário")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"Erro ao iniciar servidor: {e}")

if __name__ == "__main__":
    main() 