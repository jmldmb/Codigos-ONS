# CVU Termicas - Projeto de Análise de Custos Variáveis Unitários

## Descrição
Projeto para captura, processamento e análise de dados de Custos Variáveis Unitários (CVU) de usinas térmicas do ONS.

## Estrutura do Projeto
```
CVU termicas/
├── data/
│   ├── raw/           # Dados brutos baixados
│   ├── processed/     # Dados processados
│   └── viz/          # Dados para visualização
├── scripts/
│   ├── data_ingest.py    # Captura de dados
│   ├── data_process.py   # Processamento
│   ├── data_viz.py       # Visualização
│   └── report_gen.py     # Geração de relatórios
├── output/
│   ├── charts/        # Gráficos gerados
│   └── reports/       # Relatórios gerados
├── logs/              # Logs de execução
├── config.yaml        # Configurações
├── requirements.txt    # Dependências
└── main.py           # Script principal
```

## Funcionalidades
1. **Captura de Dados**: Download automático dos dados CVU do ONS
2. **Processamento**: Limpeza e transformação dos dados
3. **Visualização**: Geração de gráficos e análises
4. **Automação**: Geração automática de relatórios

## Como Usar
1. Instalar dependências: `pip install -r requirements.txt`
2. Configurar `config.yaml` se necessário
3. Executar: `python main.py`

## Fontes de Dados
- URL base: https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/cvu_usitermica_se/
- Formato: Parquet
- Período: 2020-2025 