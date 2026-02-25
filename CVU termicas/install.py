"""
Script de instalação das dependências do projeto CVU Termicas
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Instala as dependências do requirements.txt"""
    print("Instalando dependências do projeto CVU Termicas...")
    
    try:
        # Verificar se pip está disponível
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
        
        # Instalar dependências
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        
        print("✅ Dependências instaladas com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False
    except FileNotFoundError:
        print("❌ pip não encontrado. Verifique se o Python está instalado corretamente.")
        return False

def create_directories():
    """Cria os diretórios necessários se não existirem"""
    print("Criando estrutura de diretórios...")
    
    directories = [
        "data/raw",
        "data/processed", 
        "data/viz",
        "output/charts",
        "output/reports",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Diretório criado/verificado: {directory}")

def main():
    """Função principal"""
    print("=" * 50)
    print("INSTALADOR CVU TERMICAS")
    print("=" * 50)
    
    # Criar diretórios
    create_directories()
    
    # Instalar dependências
    if install_requirements():
        print("\n" + "=" * 50)
        print("✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 50)
        print("\nPara executar o projeto:")
        print("1. Pipeline completo: python main.py")
        print("2. Apenas atualização de dados: python main.py --mode update")
        print("3. Apenas visualizações: python main.py --mode viz")
        print("4. Apenas relatório: python main.py --mode report")
        print("\nPara mais informações, consulte o README.md")
    else:
        print("\n❌ INSTALAÇÃO FALHOU!")
        print("Verifique se o Python e pip estão instalados corretamente.")

if __name__ == "__main__":
    main() 