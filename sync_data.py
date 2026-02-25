#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_data.py - Sistema de Sincronização de Dados
================================================

Script para backup e restore de dados do projeto Codigos ONS.
Garante que todos os arquivos sejam colocados nos diretórios corretos.

Uso:
    # Fazer backup dos dados
    python sync_data.py --backup --output "D:/Backup_Codigos_ONS"
    
    # Restaurar dados
    python sync_data.py --restore --source "D:/Backup_Codigos_ONS"
    
    # Verificar estrutura
    python sync_data.py --verify

Autor: Sistema Codigos ONS
Data: 2026-02-24
"""

import os
import json
import hashlib
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import sys

class DataSync:
    """Classe para sincronização de dados do projeto."""
    
    def __init__(self, project_root: str = None):
        """
        Inicializa o sincronizador.
        
        Args:
            project_root: Caminho raiz do projeto (padrão: diretório atual)
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.structure_file = self.project_root / "data_structure.json"
        self.manifest_file = self.project_root / "data_manifest.json"
        
        # Carregar estrutura do projeto
        if self.structure_file.exists():
            with open(self.structure_file, 'r', encoding='utf-8') as f:
                self.structure = json.load(f)
        else:
            print("⚠️  Aviso: data_structure.json não encontrado")
            self.structure = {}
    
    def calculate_md5(self, filepath: Path) -> str:
        """Calcula hash MD5 de um arquivo."""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"⚠️  Erro ao calcular MD5 de {filepath}: {e}")
            return ""
    
    def get_data_files(self) -> List[Dict]:
        """
        Escaneia o projeto e retorna lista de todos os arquivos de dados.
        
        Returns:
            Lista de dicionários com informações dos arquivos
        """
        print("\n📦 Escaneando arquivos de dados...")
        
        data_extensions = {'.parquet', '.csv', '.xls', '.xlsx', '.xlsm'}
        data_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Ignorar pastas específicas
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'venv', '.venv', 'venv_merit_order'}]
            
            for file in files:
                filepath = Path(root) / file
                ext = filepath.suffix.lower()
                
                if ext in data_extensions:
                    rel_path = filepath.relative_to(self.project_root)
                    file_size = filepath.stat().st_size
                    
                    file_info = {
                        'path': str(rel_path).replace('\\', '/'),
                        'size': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2),
                        'modified': datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
                        'md5': self.calculate_md5(filepath) if file_size < 100 * 1024 * 1024 else "skipped_large_file"
                    }
                    data_files.append(file_info)
        
        return data_files
    
    def create_manifest(self) -> Dict:
        """
        Cria manifesto com informações de todos os arquivos de dados.
        
        Returns:
            Dicionário com o manifesto
        """
        print("\n📋 Criando manifesto de dados...")
        
        data_files = self.get_data_files()
        
        manifest = {
            'project': 'Codigos ONS',
            'created': datetime.now().isoformat(),
            'total_files': len(data_files),
            'total_size_mb': round(sum(f['size'] for f in data_files) / (1024 * 1024), 2),
            'total_size_gb': round(sum(f['size'] for f in data_files) / (1024 * 1024 * 1024), 2),
            'files': data_files
        }
        
        # Salvar manifesto
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Manifesto criado: {len(data_files)} arquivos ({manifest['total_size_gb']:.2f} GB)")
        
        return manifest
    
    def backup(self, output_dir: str):
        """
        Faz backup de todos os arquivos de dados.
        
        Args:
            output_dir: Diretório de destino do backup
        """
        print("\n" + "="*70)
        print("🔄 INICIANDO BACKUP DE DADOS")
        print("="*70)
        
        # Criar manifesto
        manifest = self.create_manifest()
        
        # Criar diretório de backup
        backup_path = Path(output_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Diretório de backup: {backup_path}")
        print(f"📊 Total de arquivos: {manifest['total_files']}")
        print(f"💾 Tamanho total: {manifest['total_size_gb']:.2f} GB")
        
        # Copiar manifesto
        shutil.copy2(self.manifest_file, backup_path / "data_manifest.json")
        shutil.copy2(self.structure_file, backup_path / "data_structure.json")
        
        # Copiar arquivos
        print("\n📥 Copiando arquivos...")
        copied = 0
        errors = []
        
        for file_info in manifest['files']:
            src = self.project_root / file_info['path']
            dst = backup_path / file_info['path']
            
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
                
                if copied % 100 == 0:
                    print(f"  Copiados: {copied}/{manifest['total_files']} arquivos...")
                    
            except Exception as e:
                errors.append(f"{file_info['path']}: {e}")
        
        print(f"\n✅ Backup concluído!")
        print(f"  ✓ Arquivos copiados: {copied}/{manifest['total_files']}")
        
        if errors:
            print(f"  ⚠️  Erros: {len(errors)}")
            for error in errors[:10]:  # Mostrar apenas os primeiros 10
                print(f"    - {error}")
        
        print(f"\n📦 Backup salvo em: {backup_path}")
        print("\n💡 Para restaurar em outro PC:")
        print(f"   1. Clone o repositório: git clone https://github.com/jmldmb/Codigos-ONS.git")
        print(f"   2. Copie esta pasta de backup para o novo PC")
        print(f"   3. Execute: python sync_data.py --restore --source \"{output_dir}\"")
    
    def restore(self, source_dir: str):
        """
        Restaura arquivos de dados a partir de um backup.
        
        Args:
            source_dir: Diretório fonte do backup
        """
        print("\n" + "="*70)
        print("🔄 INICIANDO RESTORE DE DADOS")
        print("="*70)
        
        source_path = Path(source_dir)
        manifest_path = source_path / "data_manifest.json"
        
        if not manifest_path.exists():
            print(f"❌ Erro: Manifesto não encontrado em {manifest_path}")
            return
        
        # Carregar manifesto
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print(f"\n📋 Manifesto carregado:")
        print(f"  Data: {manifest['created']}")
        print(f"  Arquivos: {manifest['total_files']}")
        print(f"  Tamanho: {manifest['total_size_gb']:.2f} GB")
        
        # Restaurar arquivos
        print("\n📥 Restaurando arquivos...")
        restored = 0
        errors = []
        
        for file_info in manifest['files']:
            src = source_path / file_info['path']
            dst = self.project_root / file_info['path']
            
            try:
                if not src.exists():
                    errors.append(f"{file_info['path']}: arquivo não encontrado no backup")
                    continue
                
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                restored += 1
                
                if restored % 100 == 0:
                    print(f"  Restaurados: {restored}/{manifest['total_files']} arquivos...")
                    
            except Exception as e:
                errors.append(f"{file_info['path']}: {e}")
        
        print(f"\n✅ Restore concluído!")
        print(f"  ✓ Arquivos restaurados: {restored}/{manifest['total_files']}")
        
        if errors:
            print(f"  ⚠️  Erros: {len(errors)}")
            for error in errors[:10]:
                print(f"    - {error}")
        
        print("\n🎉 Pronto para trabalhar!")
    
    def verify(self):
        """Verifica a estrutura do projeto e arquivos de dados."""
        print("\n" + "="*70)
        print("🔍 VERIFICANDO ESTRUTURA DO PROJETO")
        print("="*70)
        
        # Verificar código Python
        py_files = list(self.project_root.rglob("*.py"))
        print(f"\n✓ Arquivos Python: {len(py_files)}")
        
        # Verificar configurações
        config_files = list(self.project_root.rglob("*.yaml")) + list(self.project_root.rglob("*.json"))
        print(f"✓ Arquivos de configuração: {len(config_files)}")
        
        # Verificar dados
        data_files = self.get_data_files()
        print(f"\n📊 Arquivos de dados: {len(data_files)}")
        
        if len(data_files) == 0:
            print("\n⚠️  ATENÇÃO: Nenhum arquivo de dados encontrado!")
            print("💡 Execute: python sync_data.py --restore --source <caminho_backup>")
        else:
            total_size_gb = sum(f['size'] for f in data_files) / (1024 * 1024 * 1024)
            print(f"💾 Tamanho total: {total_size_gb:.2f} GB")
            
            # Verificar estrutura de pastas
            print("\n📁 Estrutura de dados:")
            data_dirs = self.structure.get('data_directories', {})
            for dir_name, dir_info in data_dirs.items():
                dir_path = self.project_root / dir_name
                if dir_path.exists():
                    print(f"  ✓ {dir_name}/")
                else:
                    print(f"  ⚠️  {dir_name}/ (não encontrado)")
        
        print("\n✅ Verificação concluída!")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='Sistema de Sincronização de Dados - Codigos ONS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  
  Fazer backup:
    python sync_data.py --backup --output "D:/Backup_Codigos_ONS"
  
  Restaurar backup:
    python sync_data.py --restore --source "D:/Backup_Codigos_ONS"
  
  Verificar estrutura:
    python sync_data.py --verify
        """
    )
    
    parser.add_argument('--backup', action='store_true', help='Fazer backup dos dados')
    parser.add_argument('--restore', action='store_true', help='Restaurar dados de um backup')
    parser.add_argument('--verify', action='store_true', help='Verificar estrutura do projeto')
    parser.add_argument('--output', type=str, help='Diretório de saída para backup')
    parser.add_argument('--source', type=str, help='Diretório fonte para restore')
    parser.add_argument('--project-root', type=str, help='Caminho raiz do projeto (padrão: diretório atual)')
    
    args = parser.parse_args()
    
    # Criar instância do sincronizador
    syncer = DataSync(project_root=args.project_root)
    
    # Executar ação
    if args.backup:
        if not args.output:
            print("❌ Erro: Especifique o diretório de saída com --output")
            sys.exit(1)
        syncer.backup(args.output)
    
    elif args.restore:
        if not args.source:
            print("❌ Erro: Especifique o diretório fonte com --source")
            sys.exit(1)
        syncer.restore(args.source)
    
    elif args.verify:
        syncer.verify()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
