# Projeto Captura ENA

Sistema de captura e processamento de dados ENA (Energia Natural Afluente) do ONS (Operador Nacional do Sistema Elétrico).

## 📋 Descrição

Este projeto converte a lógica do notebook original em uma estrutura Python modular e organizada, seguindo padrões de projeto de dados. O sistema permite:

- Download automático de dados ENA diários do ONS
- Processamento de arquivos ENA PDP (projeções diárias)
- Processamento de dados PMO (Programa Mensal de Operação)
- Criação de visualizações (gráficos "hairy chart")
- Geração de relatórios e exportação de dados

## 🏗️ Estrutura do Projeto

```
Captura ENA/
├── config/
│   └── config.yaml              # Configurações do projeto
├── src/
│   ├── data/                    # Módulos de processamento de dados
│   │   ├── ena_processor.py     # Processamento ENA PDP
│   │   ├── pmo_processor.py     # Processamento PMO
│   │   ├── ena_diario_processor.py  # Processamento ENA diário
│   │   └── downloader.py        # Download de dados
│   ├── visualization/           # Módulos de visualização
│   │   └── plotter.py           # Criação de gráficos
│   ├── utils/                   # Utilitários
│   │   ├── config.py            # Gerenciamento de configurações
│   │   └── logger.py            # Sistema de logging
│   └── orchestrator.py          # Orquestrador principal
├── Data/                        # Dados do projeto
│   ├── Dados Brutos/            # Dados originais
│   ├── Dados Processados/       # Dados processados
│   ├── Outputs/                 # Arquivos de saída
│   └── reports/                 # Relatórios gerados
├── logs/                        # Arquivos de log
├── main.py                      # Script principal
├── example_usage.py             # Exemplos de uso
├── requirements.txt             # Dependências
└── README.md                    # Este arquivo
```

## 🚀 Instalação

1. **Clone o repositório:**
```bash
git clone <url-do-repositorio>
cd "Captura ENA"
```

2. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

3. **Configure os diretórios de dados:**
   - Coloque os arquivos ENA PDP na pasta `Data/Dados Brutos/arquivos_ENA_PDP_ONS/`
   - Coloque o arquivo PMO mensal na mesma pasta

## 📖 Uso

### Pipeline Completo

Para executar todo o processamento:

```bash
python main.py
```

ou

```bash
python main.py --full-pipeline
```

### Operações Específicas

**Download de dados ENA diários:**
```bash
python main.py --download-ena
```

**Processamento de dados PMO:**
```bash
python main.py --process-pmo
```

**Criação de visualizações:**
```bash
python main.py --create-viz
```

**Salvar dados processados:**
```bash
python main.py --save-data
```

**Especificar pasta de arquivos ENA:**
```bash
python main.py --ena-folder "caminho/para/arquivos"
```

**Especificar ano para processamento:**
```bash
python main.py --year 2024
```

### Uso Programático

```python
from src.orchestrator import ENAOrchestrator

# Inicializar orquestrador
orchestrator = ENAOrchestrator()

# Executar pipeline completo
results = orchestrator.run_full_pipeline()

# Ou executar operações específicas
orchestrator.download_ena_data()
orchestrator.process_ena_pdp_files()
orchestrator.create_visualizations()
```

## ⚙️ Configuração

As configurações do projeto estão no arquivo `config/config.yaml`:

```yaml
# Configurações de diretórios
paths:
  raw_data: "Data/Dados Brutos"
  processed_data: "Data/Dados Processados"
  outputs: "Data/Outputs"
  logs: "logs"
  reports: "reports"

# Configurações de processamento
processing:
  sheet_6_index: 5  # Aba 6 (SUDESTE)
  sheet_7_index: 6  # Aba 7 (SUL, NORDESTE, NORTE)
  
# Configurações de visualização
visualization:
  figure_size: [12, 8]
  colors:
    line_color: "blue"
    last_line_color: "red"
    pmo_color: "green"
```

## 📊 Funcionalidades

### 1. Download de Dados
- Download automático de dados ENA diários do site do ONS
- Suporte a múltiplos anos
- Tratamento de erros de conexão

### 2. Processamento ENA PDP
- Leitura de arquivos Excel com projeções diárias
- Extração de dados das abas 6 (SUDESTE) e 7 (SUL, NORDESTE, NORTE)
- Suporte a diferentes formatos de arquivo (novo e antigo)
- Cálculo automático de MLT (Média de Longo Termo)

### 3. Processamento PMO
- Leitura de arquivos PMO mensal
- Agrupamento e processamento de dados
- Integração com projeções diárias

### 4. Visualizações
- Gráfico "hairy chart" com projeções
- Gráfico comparativo entre dados reais e projeções
- Personalização de cores e estilos
- Exportação em alta resolução

### 5. Exportação de Dados
- Salvamento em formato Excel
- Dados consolidados e agrupados
- Relatórios estruturados

## 🔧 Módulos Principais

### ENAProcessor
Processa arquivos ENA PDP, extraindo dados das abas específicas e calculando métricas.

### PMOProcessor
Gerencia o processamento de dados PMO, incluindo leitura e agrupamento.

### ENADownloader
Responsável pelo download automático de dados ENA diários do site do ONS.

### ENAPlotter
Cria visualizações personalizadas dos dados processados.

### ENAOrchestrator
Orquestra todo o pipeline de processamento, coordenando os diferentes módulos.

## 📝 Logs

O sistema gera logs detalhados em:
- Console (tempo real)
- Arquivo `logs/captura_ena.log`

Níveis de log configuráveis:
- INFO: Informações gerais
- WARNING: Avisos
- ERROR: Erros

## 🐛 Tratamento de Erros

O sistema inclui tratamento robusto de erros:
- Validação de arquivos de entrada
- Tratamento de conexões de rede
- Verificação de integridade de dados
- Logs detalhados de erros

## 📈 Exemplos de Saída

### Gráficos Gerados
- `hairy_chart.png`: Projeções de ENA como percentual MLT
- `comparison_chart.png`: Comparação entre dados reais e projeções

### Arquivos de Dados
- `final_combined_data.xlsx`: Dados ENA PDP consolidados
- `grouped_data.xlsx`: Dados agrupados por data
- `pmo_data.xlsx`: Dados PMO processados
- `ena_diario_data.xlsx`: Dados ENA diários

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👥 Autores

- Desenvolvido com base no notebook original de captura ENA
- Convertido para estrutura modular Python

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs em `logs/captura_ena.log`
2. Consulte a documentação dos módulos
3. Execute `python example_usage.py` para exemplos
4. Abra uma issue no repositório

## 🔄 Atualizações

### Versão 1.0.0
- Conversão do notebook para estrutura Python modular
- Implementação de orquestrador
- Sistema de configuração YAML
- Logging estruturado
- Visualizações personalizadas
- Download automático de dados


