# Codigos ONS

Sistema de análises do setor elétrico brasileiro desenvolvido para análises operacionais e estratégicas do sistema elétrico nacional.

## 📋 Descrição

Este repositório contém um conjunto integrado de ferramentas e análises para o setor elétrico brasileiro, incluindo:

- **Captura ENA**: Coleta e análise de Energia Natural Afluente
- **Análise de Carga**: Processamento e visualização de dados de carga do sistema
- **Carga Líquida**: Análises de carga líquida considerando geração distribuída
- **Curtailment**: Análises de cortes de geração renovável
- **CVU Térmicas**: Cálculo e análise de Custo Variável Unitário de usinas térmicas
- **Mini DESSEM**: Análises baseadas no modelo de despacho DESSEM
- **Preços de Energia**: Análises de preços spot e contratos
- **Vertimento Turbinável**: Análises de vertimento em usinas hidrelétricas
- **Orquestrador Central**: Sistema de coordenação de análises

## 🚀 Início Rápido

### 1. Clone o Repositório

```bash
git clone https://github.com/jmldmb/Codigos-ONS.git
cd Codigos-ONS
```

### 2. Configure o Ambiente Python

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências (se houver requirements.txt em cada módulo)
pip install -r requirements.txt
```

### 3. Restaurar Dados

⚠️ **IMPORTANTE**: Este repositório contém apenas o código. Os arquivos de dados não estão versionados no Git devido ao tamanho.

Para restaurar os dados:

```bash
# Se você tem um backup
python sync_data.py --restore --source "caminho/para/backup"

# Para verificar a estrutura
python sync_data.py --verify
```

## 📁 Estrutura do Projeto

```
Codigos-ONS/
├── Captura ENA/              # Análises de ENA
│   ├── src/                  # Código fonte
│   ├── config/               # Configurações
│   ├── Data/                 # Dados (não versionado)
│   └── README.md
│
├── Carga/                    # Análises de carga
│   ├── analise_carga.py
│   ├── config.yaml
│   └── Data/                 # Dados (não versionado)
│
├── carga_liquida/            # Carga líquida
│   ├── Scripts/
│   └── Data/                 # Dados (não versionado)
│
├── Curtailment/              # Análises de curtailment
│   ├── Scripts/
│   └── Dados/                # Dados (não versionado)
│
├── CVU termicas/             # CVU de térmicas
│   ├── main.py
│   ├── scripts/
│   └── data/                 # Dados (não versionado)
│
├── mini_dessem/              # Análises DESSEM
│   ├── Scripts/
│   └── data/                 # Dados (não versionado)
│
├── Precos de Energia BR/     # Análises de preços
│   ├── Scripts/
│   └── Data/                 # Dados (não versionado)
│
├── orquestrador_central/     # Orquestrador
│   └── Scripts/
│
└── sync_data.py              # Script de sincronização
```

## 🔧 Módulos Principais

### Captura ENA
Coleta e processamento de dados de Energia Natural Afluente do ONS.

**Principais funcionalidades:**
- Download automático de dados do ONS
- Processamento e limpeza de dados
- Geração de gráficos e relatórios

### Análise de Carga
Processamento de dados de carga do sistema elétrico.

**Principais funcionalidades:**
- Análise de séries temporais de carga
- Identificação de padrões e tendências
- Previsões de carga

### Curtailment
Análises de cortes de geração renovável (eólica e solar).

**Principais funcionalidades:**
- Identificação de eventos de curtailment
- Análise de impacto financeiro
- Correlação com CMO

### CVU Térmicas
Cálculo e análise de Custo Variável Unitário de usinas térmicas.

**Principais funcionalidades:**
- Cálculo de CVU por usina
- Análise de mérito de despacho
- Visualizações de ordem de mérito

### Mini DESSEM
Análises baseadas no modelo de despacho de curto prazo.

**Principais funcionalidades:**
- Processamento de resultados DESSEM
- Análise de despacho horário
- Geração de relatórios operacionais

## 📊 Sincronização de Dados

Este projeto utiliza um sistema de sincronização de dados para facilitar o trabalho em múltiplos computadores.

### Fazer Backup

```bash
python sync_data.py --backup --output "D:/Backup_Codigos_ONS"
```

Isso irá:
- ✅ Escanear todos os arquivos de dados
- ✅ Criar um manifesto com checksums MD5
- ✅ Copiar todos os dados para o diretório de backup
- ✅ Gerar relatório detalhado

### Restaurar Backup

```bash
python sync_data.py --restore --source "D:/Backup_Codigos_ONS"
```

Isso irá:
- ✅ Ler o manifesto de backup
- ✅ Criar estrutura de pastas necessária
- ✅ Copiar arquivos para os locais corretos
- ✅ Verificar integridade dos dados

### Verificar Estrutura

```bash
python sync_data.py --verify
```

Isso irá:
- ✅ Verificar código Python
- ✅ Verificar arquivos de configuração
- ✅ Verificar presença de dados
- ✅ Reportar problemas encontrados

## 🔐 Dados e Segurança

- **Dados sensíveis**: Não versione credenciais ou dados confidenciais
- **Arquivos grandes**: Dados brutos estão no `.gitignore`
- **Backup**: Use o `sync_data.py` ou Google Drive para sincronização
- **Configurações locais**: Use arquivos `*_local.yaml` (ignorados pelo Git)

## 📦 Dependências

Cada módulo pode ter suas próprias dependências. Verifique os arquivos `requirements.txt` em cada pasta.

Dependências comuns:
- pandas
- numpy
- matplotlib
- seaborn
- pyyaml
- requests

## 🤝 Contribuindo

Este é um projeto interno. Para contribuir:

1. Crie uma branch para sua feature
2. Faça commit das mudanças
3. Push para a branch
4. Abra um Pull Request

## 📝 Convenções de Código

- **Python**: Siga PEP 8
- **Docstrings**: Use formato Google/NumPy
- **Commits**: Mensagens claras e descritivas
- **Configurações**: Use YAML para configs

## 🐛 Problemas Conhecidos

- Alguns arquivos de dados são muito grandes (>100 MB)
- Requer conexão com APIs internas para alguns módulos
- Alguns scripts dependem de estrutura de pastas específica

## 📞 Contato

Para dúvidas ou sugestões, entre em contato com a equipe de desenvolvimento.

## 📄 Licença

Projeto interno - Todos os direitos reservados.

## 🔄 Histórico de Versões

### v1.0.0 (2026-02-24)
- ✨ Versão inicial no GitHub
- ✨ Sistema de sincronização de dados implementado
- ✨ Documentação completa
- ✨ Estrutura modular organizada

---

**Desenvolvido com ❤️ para análises do setor elétrico brasileiro**
