# Análise de Carga Energética - ONS

Sistema baseado no notebook estável `Carga.ipynb` para análise de dados de carga energética do ONS.

## Funcionalidades

O sistema gera **2 gráficos principais**:

1. **Comparativa Horária**: Compara a carga energética por hora entre dois períodos de datas selecionadas, incluindo médias diárias
2. **Comparação YoY**: Analisa o crescimento year-over-year entre dois anos configuráveis, com médias trimestrais

## Estrutura do Projeto

```
Carga/
├── analise_carga.py      # Script principal
├── config.yaml           # Arquivo de configuração
├── README.md            # Este arquivo
├── Data/
│   └── raw_data/        # Dados baixados do ONS
└── output/
    └── charts/          # Gráficos gerados
```

## Configuração

Edite o arquivo `config.yaml` para personalizar:

### Anos para Comparação YoY
```yaml
charts:
  yoy_growth:
    year1: 2025  # Ano atual
    year2: 2024  # Ano anterior
```

### Períodos para Comparação Horária
```yaml
charts:
  hourly_comparison:
    period1: "2024-07-15"  # Primeiro período
    period2: "2025-07-15"  # Segundo período
```

### Outras Configurações
- `moving_average_window`: Janela para média móvel (padrão: 14 dias)
- `remove_zeros`: Remove valores zero dos dados
- `dpi`: Resolução dos gráficos
- `format`: Formato dos arquivos de saída

## Como Usar

1. **Instalar dependências**:
   ```bash
   pip install pandas matplotlib requests pyyaml
   ```

2. **Configurar parâmetros**:
   - Edite o arquivo `config.yaml` conforme suas necessidades

3. **Executar análise**:
   ```bash
   python analise_carga.py
   ```

## Exemplos de Configuração

### Comparar 2025 vs 2024
```yaml
charts:
  yoy_growth:
    year1: 2025
    year2: 2024
```

### Comparar períodos específicos
```yaml
charts:
  hourly_comparison:
    period1: "2024-01-15"
    period2: "2025-01-15"
```

### Desabilitar um gráfico
```yaml
charts:
  hourly_comparison:
    enabled: false
```

## Saídas

Os gráficos são salvos na pasta `output/charts/` com nomes:
- `comparacao_horaria_YYYYMMDD_HHMMSS.png`
- `crescimento_yoy_YYYY_vs_YYYY_YYYYMMDD_HHMMSS.png`

### Características dos Gráficos

#### 1. Gráfico de Comparação Horária
- **Carga por hora**: Mostra a carga energética para cada hora do dia
- **Médias diárias**: Linhas tracejadas horizontais mostrando a média diária de cada período
- **Comparação visual**: Permite comparar facilmente os padrões de consumo entre dois períodos

#### 2. Gráfico de Crescimento YoY
- **Crescimento percentual**: Linha vermelha mostrando o crescimento year-over-year
- **Médias trimestrais**: Linhas tracejadas coloridas mostrando a média de crescimento por trimestre
- **Análise temporal**: Permite identificar tendências e sazonalidade no crescimento

## Características

- **Baseado no notebook estável**: Usa a mesma lógica do `Carga.ipynb`
- **Configurável**: Todos os parâmetros podem ser ajustados via YAML
- **Robusto**: Fallback para datas disponíveis se as configuradas não existirem
- **Flexível**: Pode habilitar/desabilitar gráficos individualmente
- **Automático**: Baixa dados automaticamente do ONS
- **Visualizações avançadas**: Inclui médias diárias e trimestrais nos gráficos

## Dependências

- `pandas`: Manipulação de dados
- `matplotlib`: Geração de gráficos
- `requests`: Download de dados
- `pyyaml`: Leitura de configuração 