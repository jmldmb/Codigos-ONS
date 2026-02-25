#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INSTALAÇÃO MANUAL DE DEPENDÊNCIAS
=================================

Script simples para instalar as dependências do teste de WhatsApp.
Use este script se o configurar_whatsapp.py não funcionar.
"""

import subprocess
import sys
import os

def instalar_pacote(nome_pacote):
    """Instala um pacote específico."""
    print(f"📦 Instalando {nome_pacote}...")
    
    try:
        # Tentar com python -m pip
        comando = [sys.executable, "-m", "pip", "install", nome_pacote]
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=300)
        
        if resultado.returncode == 0:
            print(f"✅ {nome_pacote} instalado com sucesso!")
            return True
        else:
            print(f"❌ Erro ao instalar {nome_pacote}:")
            print(f"   {resultado.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout ao instalar {nome_pacote}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def verificar_pacote(nome_pacote):
    """Verifica se um pacote está instalado."""
    try:
        if nome_pacote == "pywhatkit":
            import pywhatkit
            return True
        elif nome_pacote == "Pillow":
            from PIL import Image
            return True
        elif nome_pacote == "requests":
            import requests
            return True
        else:
            __import__(nome_pacote)
            return True
    except ImportError:
        return False

def main():
    """Função principal."""
    print("🔧 INSTALAÇÃO MANUAL DE DEPENDÊNCIAS")
    print("=" * 50)
    
    # Lista de pacotes para instalar
    pacotes = [
        ("pywhatkit", "pywhatkit>=5.4"),
        ("Pillow", "Pillow>=9.0.0"),
        ("requests", "requests>=2.25.0")
    ]
    
    print("Verificando pacotes já instalados...")
    for nome, _ in pacotes:
        if verificar_pacote(nome):
            print(f"✅ {nome} já está instalado")
        else:
            print(f"❌ {nome} não encontrado")
    
    print("\nIniciando instalação...")
    sucessos = 0
    falhas = 0
    
    for nome, pacote in pacotes:
        if not verificar_pacote(nome):
            if instalar_pacote(pacote):
                sucessos += 1
            else:
                falhas += 1
        else:
            print(f"⏭️ {nome} já instalado, pulando...")
            sucessos += 1
    
    print(f"\n📊 RESUMO:")
    print(f"   ✅ Sucessos: {sucessos}")
    print(f"   ❌ Falhas: {falhas}")
    
    if falhas == 0:
        print("\n🎉 Todas as dependências foram instaladas com sucesso!")
        print("Agora você pode executar: python teste_whatsapp.py")
    else:
        print(f"\n⚠️ {falhas} dependência(s) falharam na instalação.")
        print("Tente instalar manualmente:")
        for nome, pacote in pacotes:
            if not verificar_pacote(nome):
                print(f"   pip install {pacote}")

if __name__ == "__main__":
    main() 