# Orquestrador de Geração por Usina

Este projeto converte os notebooks de análise de geração por usina em uma estrutura Python modular e organizada, com um orquestrador que coordena todas as operações.

## Estrutura do Projeto

```
Geracao por usina/
├── config/
│   └── config.yaml              # Configurações centralizadas
├── utils/
│   ├── __init__.py
│   ├── config.py                # Gerenciamento de configurações
│   └── logger.py                # Sistema de logging
├── scripts/
│   ├── __init__.py
│   ├── data_downloader.py       # Download de dados do ONS
│   ├── data_processor.py        # Processamento de dados
│   └── visualization.py         # Geração de gráficos
├── Data/                        # Dados originais
│   ├── cadastro/                # Arquivos de cadastro
│   ├── geracao/                 # Dados de geração renovável
│   └── geracao_base_horaria/    # Dados de geração horária
├── output/                      # Saídas geradas
│   ├── charts/                  # Gráficos gerados
│   ├── reports/                 # Relatórios
│   └── data/                    # Dados processados
├── logs/                        # Logs do sistema
├── orchestrator.py              # Orquestrador principal
├── exemplo_uso.py               # Exemplos de uso
├── requirements.txt             # Dependências
└── README.md                    # Este arquivo
```

## Instalação

1. **Clone ou navegue para o diretório do projeto:**
   ```bash
   cd "C:/Users/joao.barbosa/Desktop/Códigos/Codigos ONS/Geracao por usina"
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure o arquivo `config/config.yaml`:**
   - Ajuste os caminhos conforme necessário
   - Configure os anos de análise
   - Ajuste as configurações de download

## Uso

### Pipeline Completo

Para executar todo o pipeline (download, processamento e gráficos):

```bash
python orchestrator.py --mode full
```

### Execução por Etapas

**Apenas download de dados:**
```bash
python orchestrator.py --mode download
```

**Apenas processamento:**
```bash
python orchestrator.py --mode process
```

**Apenas geração de gráficos:**
```bash
python orchestrator.py --mode charts
```

### Uso Programático

```python
from orchestrator import GeracaoUsinaOrchestrator

# Inicializa o orquestrador
orchestrator = GeracaoUsinaOrchestrator()

# Executa pipeline completo
orchestrator.run_full_pipeline()

# Ou executa etapas separadamente
orchestrator.download_data()
processed_data = orchestrator.process_data()
orchestrator.generate_charts(processed_data)
```

### Exemplos de Uso

Execute o arquivo de exemplos para ver diferentes formas de uso:

```bash
python exemplo_uso.py
```

## Funcionalidades

### 1. Download de Dados (`data_downloader.py`)

- **Geração Renovável:** Download de dados de eólica e fotovoltaica
- **Geração Horária:** Download de dados de geração por usina
- **Configurável:** Número de meses para baixar
- **Robusto:** Tratamento de erros e logging

### 2. Processamento de Dados (`data_processor.py`)

- **Consolidação:** Agrega arquivos parquet por tipo
- **Filtragem:** Aplica filtros de cadastro
- **Agregação:** Agrupa dados por empresa, mês, etc.
- **Certificação:** Processa dados P50/P90
- **Saída:** Gera arquivos Excel processados

### 3. Visualização (`visualization.py`)

- **Gráficos Renováveis:** Comparação com P50/P90
- **Gráficos Térmicos:** Por empresa e combustível
- **Gráficos Resumo:** Visão geral por empresa
- **Configurável:** Cores, tamanhos, formatos
- **Automático:** Gera um gráfico por empresa

### 4. Configuração (`config.py`)

- **Centralizada:** Todas as configurações em YAML
- **Flexível:** Suporte a diferentes ambientes
- **Tipada:** Validação de tipos
- **Caminhos:** Resolução automática de paths

### 5. Logging (`logger.py`)

- **Estruturado:** Logs organizados por módulo
- **Múltiplos:** Console e arquivo
- **Configurável:** Níveis e formatos
- **Rastreável:** Timestamps e contexto

## Configuração

O arquivo `config/config.yaml` permite configurar:

```yaml
paths:
  base_dir: "C:/Users/joao.barbosa/Desktop/Códigos/Codigos ONS/Geracao por usina"
  data:
    geracao: "Data/geracao"
    geracao_base_horaria: "Data/geracao_base_horaria"
    cadastro: "Data/cadastro"
  output:
    charts: "output/charts"
    reports: "output/reports"
    data: "output/data"

download:
  meses_para_baixar: 2
  verify_ssl: false

processing:
  anos_analise: [2024, 2025]
  tipos_usina: ["FOTOVOLTAICA", "EOLICA", "TÉRMICA"]

visualization:
  figsize: [12, 8]
  dpi: 300
  save_format: "png"
```

## Saídas

### Dados Processados (`output/data/`)

- `geracao_renovavel.xlsx`: Dados de geração renovável processados
- `geracao_termica.xlsx`: Dados de geração térmica processados

### Gráficos (`output/charts/`)

- `{empresa}_renovavel_vs_certificacao.png`: Gráficos por empresa
- `{empresa}_{combustivel}_geracao_termica.png`: Gráficos térmicos
- `resumo_geracao_empresas.png`: Gráfico resumo

### Logs (`logs/`)

- `geracao_usina.log`: Log detalhado de todas as operações

## Vantagens da Nova Estrutura

1. **Modularidade:** Código organizado em módulos específicos
2. **Reutilização:** Funções podem ser usadas independentemente
3. **Configuração:** Centralizada e flexível
4. **Logging:** Rastreabilidade completa
5. **Robustez:** Tratamento de erros adequado
6. **Escalabilidade:** Fácil adição de novas funcionalidades
7. **Manutenibilidade:** Código limpo e documentado
8. **Automação:** Pipeline completo automatizado

## Troubleshooting

### Problemas Comuns

1. **Erro de SSL:** Configurado para ignorar warnings de SSL
2. **Arquivos não encontrados:** Verifique os caminhos no config.yaml
3. **Memória insuficiente:** Processa arquivos em lotes
4. **Dependências:** Instale todas as dependências do requirements.txt

### Logs

Consulte os logs em `logs/geracao_usina.log` para diagnóstico de problemas.

## Contribuição

Para adicionar novas funcionalidades:

1. Crie um novo módulo em `scripts/`
2. Atualize o orquestrador se necessário
3. Adicione configurações no `config.yaml`
4. Documente no README
5. Teste com diferentes cenários

## Licença

Este projeto é para uso interno da empresa.
