# 🚀 Guia de Configuração - Codigos ONS

Este guia irá ajudá-lo a configurar o projeto "Codigos ONS" em um novo computador.

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Git
- 4.6 GB de espaço em disco (para dados)
- Conexão com internet (para clone inicial)

## 🔧 Configuração Passo a Passo

### Passo 1: Instalar Python

Se ainda não tem Python instalado:

**Windows:**
```bash
# Baixe de: https://www.python.org/downloads/
# Durante instalação, marque "Add Python to PATH"
```

**Linux/Mac:**
```bash
# Geralmente já vem instalado
python3 --version
```

### Passo 2: Instalar Git

**Windows:**
```bash
# Baixe de: https://git-scm.com/download/win
```

**Linux:**
```bash
sudo apt-get install git
```

**Mac:**
```bash
brew install git
```

### Passo 3: Clonar o Repositório

```bash
# Navegue até onde quer clonar o projeto
cd C:\Users\seu_usuario\Desktop\Codigos

# Clone o repositório
git clone https://github.com/jmldmb/Codigos-ONS.git

# Entre na pasta
cd Codigos-ONS
```

### Passo 4: Criar Ambiente Virtual

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### Passo 5: Instalar Dependências

```bash
# Se houver requirements.txt global
pip install -r requirements.txt

# Ou instalar por módulo
cd "Captura ENA"
pip install -r requirements.txt
cd ..

cd "Carga"
pip install -r requirements.txt
cd ..

# Repita para outros módulos conforme necessário
```

### Passo 6: Restaurar Dados

Você tem **3 opções** para obter os dados:

#### Opção A: Restaurar de Backup Local 🔄

Se você fez backup no computador antigo:

```bash
# No computador ANTIGO (antes de sair):
python sync_data.py --backup --output "D:/Backup_Codigos_ONS"

# Copie a pasta "Backup_Codigos_ONS" para o novo PC
# (via pen drive, HD externo, rede, etc.)

# No computador NOVO:
python sync_data.py --restore --source "D:/Backup_Codigos_ONS"
```

#### Opção B: Google Drive 📁

```bash
# 1. No computador antigo, faça backup
python sync_data.py --backup --output "C:/Users/seu_usuario/Google Drive/Backup_Codigos_ONS"

# 2. Aguarde sincronização do Google Drive

# 3. No computador novo, após instalar Google Drive Desktop
python sync_data.py --restore --source "C:/Users/seu_usuario/Google Drive/Backup_Codigos_ONS"
```

#### Opção C: Download Manual das Fontes 🌐

Se preferir baixar dados diretamente das fontes:

1. **ONS (Energia Natural Afluente)**
   - Site: https://www.ons.org.br/
   - Navegue até: Dados > Energia Natural Afluente
   - Salve em: `Captura ENA/Data/`

2. **Carga do Sistema**
   - Site: https://www.ons.org.br/
   - Navegue até: Dados > Carga
   - Salve em: `Carga/Data/`

3. **Outros dados**
   - Consulte documentação específica de cada módulo

### Passo 7: Verificar Instalação

```bash
# Verificar estrutura do projeto
python sync_data.py --verify
```

Você deve ver:
```
✓ Arquivos Python: XXX
✓ Arquivos de configuração: XXX
📊 Arquivos de dados: XXX
💾 Tamanho total: X.XX GB
```

### Passo 8: Testar Módulos

Teste cada módulo individualmente:

```bash
# Testar Captura ENA
cd "Captura ENA"
python main.py
cd ..

# Testar Análise de Carga
cd "Carga"
python analise_carga.py
cd ..

# Continue para outros módulos...
```

## 🔍 Verificação de Problemas

### Problema: "Módulo não encontrado"

```bash
# Certifique-se de que o ambiente virtual está ativado
# Windows:
venv\Scripts\activate

# Instale a dependência faltante
pip install nome_do_modulo
```

### Problema: "Arquivo de dados não encontrado"

```bash
# Verifique se os dados foram restaurados
python sync_data.py --verify

# Se necessário, restaure novamente
python sync_data.py --restore --source "caminho/para/backup"
```

### Problema: "Erro de permissão"

```bash
# Windows: Execute como Administrador
# Linux/Mac: Use sudo se necessário
sudo python script.py
```

## 📊 Estrutura de Dados Esperada

Após restaurar os dados, você deve ter:

```
Codigos-ONS/
├── Captura ENA/
│   └── Data/                 ← 169 arquivos (~45 MB)
├── Carga/
│   └── Data/                 ← 28 arquivos (~120 MB)
├── carga_liquida/
│   └── Data/
│       ├── raw/              ← 101 arquivos
│       └── processed/        ← 2 arquivos
├── Curtailment/
│   └── Dados/                ← 79 arquivos
├── CVU termicas/
│   └── data/                 ← 16 arquivos
├── mini_dessem/
│   └── data/                 ← Muitos arquivos (~1.2 GB)
└── [outros módulos...]
```

## 🔐 Configurações Locais

Alguns módulos podem precisar de configurações específicas:

```bash
# Copie o template de configuração
cp config.yaml config_local.yaml

# Edite com suas configurações
notepad config_local.yaml  # Windows
nano config_local.yaml     # Linux/Mac
```

**Nota:** Arquivos `*_local.yaml` não são versionados no Git.

## 🌐 Conexões Externas

Alguns módulos podem precisar de:

- **APIs do ONS**: Credenciais para acesso a dados
- **Bloomberg**: Para módulos de preços (se aplicável)
- **Banco de dados interno**: Configurar conexão

Consulte a documentação específica de cada módulo.

## 📝 Próximos Passos

1. ✅ Configurar Git com suas credenciais
   ```bash
   git config --global user.name "Seu Nome"
   git config --global user.email "seu.email@exemplo.com"
   ```

2. ✅ Criar branch para seu trabalho
   ```bash
   git checkout -b feature/sua-feature
   ```

3. ✅ Começar a trabalhar!

## 🆘 Precisa de Ajuda?

- **Documentação**: Consulte README.md de cada módulo
- **Verificação**: Execute `python sync_data.py --verify`
- **Logs**: Verifique arquivos `.log` nas pastas `logs/`

## 📞 Suporte

Para problemas ou dúvidas:
- Verifique os logs de erro
- Consulte a documentação específica do módulo
- Entre em contato com a equipe de desenvolvimento

---

**Boa sorte com suas análises! 🚀**
