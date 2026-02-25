# Análise de Correlação: Curtailment Energético vs CMO

Este projeto analisa a correlação entre o **curtailment energético** (em termos percentuais) e o **Custo Marginal de Operação (CMO)** para cada hora disponível nas amostras.

## Objetivo

Gerar gráficos de correlação entre:
- **Curtailment energético**: Medido em termos percentuais a nível Brasil
- **CMO**: Custo Marginal de Operação do subsistema Sudeste

## Estrutura do Projeto

```
correlacao_curtailment_cmo/
├── correlacao_curtailment_cmo.py    # Script principal de análise
├── requirements.txt                 # Dependências Python
├── README.md                        # Este arquivo
├── data/                           # Dados processados (gerados automaticamente)
├── output/                         # Gráficos e análises (gerados automaticamente)
└── correlacao_analise.log          # Log de execução (gerado automaticamente)
```

## Pré-requisitos

### Dados Necessários

O sistema utiliza dados dos seguintes diretórios existentes:

1. **Dados de Curtailment**:
   - Local: `../Codigos ONS/Curtailment/Dados/raw_data/`
   - Arquivos: `RESTRICAO_COFF_EOLICA_*.csv` e `RESTRICAO_COFF_FOTOVOLTAICA_*.csv`

2. **Dados de CMO**:
   - Local: `../Codigos ONS/carga_liquida/Data/raw/CMO/` ou `../Codigos ONS/Curtailment/Dados/raw_data/`
   - Arquivos: `CMO_SEMIHORARIO_*.csv`

### Dependências Python

```bash
pip install -r requirements.txt
```

## Como Usar

### Execução Automática

```bash
python correlacao_curtailment_cmo.py
```

### Execução Passo a Passo (via código)

```python
from correlacao_curtailment_cmo import CorrelacaoAnalisador

# Inicializar analisador
analisador = CorrelacaoAnalisador()

# Executar análise completa
resultado = analisador.executar_analise_completa()

# Acessar resultados
print(f"Correlação: {resultado['analise']['correlacao_pearson']:.4f}")
print(f"Gráfico: {resultado['grafico_path']}")
```

## Funcionalidades

### 1. Carregamento de Dados

- **Dados de Curtailment**: Carrega dados brutos de curtailment e calcula percentuais a nível Brasil
- **Dados de CMO**: Carrega dados de CMO do subsistema Sudeste
- **Período de Análise**: Últimos 30 dias automaticamente

### 2. Processamento

- Conversão de unidades (MW para MWh)
- Agregação por hora
- Cálculo de percentuais de curtailment
- Combinação de datasets por timestamp

### 3. Análise Estatística

- Coeficiente de correlação de Pearson
- Estatísticas descritivas (média, desvio padrão)
- Interpretação da força da correlação

### 4. Visualizações

O sistema gera automaticamente 4 tipos de gráficos:

1. **Scatter Plot Principal**: Curtailment (%) vs CMO (R$/MWh)
2. **Distribuição de CMO**: Faixas de valores de CMO
3. **Séries Temporais**: Evolução temporal de ambas as variáveis
4. **Correlação por Hora**: Coeficiente de correlação para cada hora do dia

## Saídas Geradas

### Arquivos de Saída

- **Gráfico principal**: `output/correlacao_curtailment_cmo_YYYYMMDD_HHMMSS.png`
- **Análise estatística**: `output/analise_estatistica_YYYYMMDD_HHMMSS.txt`
- **Log de execução**: `correlacao_analise.log`

### Exemplo de Saída Estatística

```
ANÁLISE DE CORRELAÇÃO: CURTAILMENT vs CMO
==================================================

Período analisado: 2024-09-15 00:00:00 até 2024-10-14 23:00:00
Tamanho da amostra: 720 observações

ESTATÍSTICAS DESCRITIVAS:
------------------------------
Curtailment médio: 2.45%
CMO médio: R$ 145.67/MWh
Desvio padrão Curtailment: 1.23%
Desvio padrão CMO: R$ 89.45/MWh

CORRELAÇÃO:
-----------
Coeficiente de Pearson: 0.6789
Força da correlação: Moderada
```

## Características Técnicas

### Tratamento de Dados

- **Período**: Últimos 30 dias automaticamente
- **Frequência**: Dados horários (agregados)
- **Filtros**: Apenas dados válidos e positivos
- **Subsistemas**: CMO do Sudeste, Curtailment Brasil

### Cálculo de Curtailment Percentual

```python
pct_curtailment = (curtailment_mwh / geracao_referencia_mwh) * 100
```

### Correlação de Pearson

```python
correlacao = df['pct_curtailment'].corr(df['val_cmo'])
```

## Interpretação dos Resultados

### Coeficiente de Correlação

- **|r| > 0.7**: Correlação Forte
- **0.3 < |r| ≤ 0.7**: Correlação Moderada
- **|r| ≤ 0.3**: Correlação Fraca

### Padrões Esperados

- **Correlação positiva**: Quando o CMO aumenta, espera-se aumento no curtailment
- **Variação por horário**: Pode haver padrões diferentes em diferentes horas do dia
- **Sazonalidade**: Padrões podem variar por mês/estação

## Logs e Debugging

O sistema gera logs detalhados em `correlacao_analise.log` com informações sobre:

- Arquivos de dados encontrados/carregados
- Número de registros processados
- Avisos e erros durante o processamento
- Estatísticas finais

## Troubleshooting

### Problemas Comuns

1. **Dados não encontrados**:
   - Verificar se os diretórios de dados existem
   - Confirmar se há arquivos recentes nos diretórios

2. **Erro de permissão**:
   - Verificar permissões de leitura dos arquivos de dados

3. **Memória insuficiente**:
   - Para grandes volumes de dados, considere reduzir o período de análise

4. **Dependências**:
   - Instalar todas as dependências: `pip install -r requirements.txt`

## Extensões Possíveis

- Análise por subsistema específico
- Análise sazonal (mensal/trimestral)
- Modelos de previsão baseados na correlação
- Dashboards interativos com Streamlit/Plotly
- Análise de outras variáveis correlacionadas

## Contribuição

Para modificar ou estender o sistema:

1. Mantenha a estrutura de classes existente
2. Adicione logs informativos para debugging
3. Teste com dados reais antes de deploy
4. Documente mudanças no README

## Licença

Este projeto utiliza dados públicos do ONS (Operador Nacional do Sistema Elétrico) e segue as diretrizes de uso estabelecidas.
