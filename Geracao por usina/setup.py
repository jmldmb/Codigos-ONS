"""
Script de instalação rápida para o projeto de Geração por Usina
"""
import subprocess
import sys
import os
from pathlib import Path


def install_requirements():
    """Instala as dependências do requirements.txt"""
    print("Instalando dependências...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependências instaladas com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Erro ao instalar dependências: {e}")
        return False


def create_directories():
    """Cria diretórios necessários"""
    print("Criando diretórios...")
    
    directories = [
        "output/charts",
        "output/reports", 
        "output/data",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Diretório criado: {directory}")


def run_tests():
    """Executa os testes de configuração"""
    print("Executando testes de configuração...")
    
    try:
        result = subprocess.run([sys.executable, "test_setup.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Testes passaram!")
            return True
        else:
            print("✗ Testes falharam!")
            print("Saída dos testes:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"✗ Erro ao executar testes: {e}")
        return False


def main():
    """Função principal de instalação"""
    print("=== Instalação do Orquestrador de Geração por Usina ===")
    print()
    
    # Verifica se está no diretório correto
    if not Path("orchestrator.py").exists():
        print("✗ Erro: Execute este script no diretório do projeto!")
        print("Navegue para: C:/Users/joao.barbosa/Desktop/Códigos/Codigos ONS/Geracao por usina")
        return False
    
    # Instala dependências
    if not install_requirements():
        return False
    
    # Cria diretórios
    create_directories()
    
    # Executa testes
    if not run_tests():
        print("\n⚠ Instalação concluída, mas alguns testes falharam.")
        print("Verifique os erros acima e corrija se necessário.")
        return False
    
    print("\n🎉 Instalação concluída com sucesso!")
    print("\nPróximos passos:")
    print("1. Execute: python exemplo_uso.py")
    print("2. Ou execute: python orchestrator.py --mode full")
    print("3. Consulte o README.md para mais informações")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
