# Otimizações de Performance

Este documento descreve as otimizações implementadas para resolver problemas de performance com grandes datasets.

## Problema Original

O erro encontrado foi:
```
ValueError: This sheet is too large! Your sheet size is: 6223104, 12 Max sheet size is: 1048576, 16384
```

Isso ocorreu porque o DataFrame de geração térmica tinha **6.223.104 células**, excedendo os limites do Excel.

## Soluções Implementadas

### 1. Verificação Inteligente de Tamanho

O método `save_processed_data()` agora verifica automaticamente o tamanho do DataFrame:

- **Datasets pequenos** (< 1M linhas): Salva como Excel
- **Datasets grandes** (> 1M linhas): 
  - Salva como CSV (mais eficiente)
  - Cria amostra Excel para visualização
  - Gera arquivo de estatísticas

### 2. Otimização do Processamento Térmico

- **Filtro por ano**: Processa apenas anos de análise (2024, 2025)
- **Agregação eficiente**: Calcula média, soma e contagem em uma operação
- **Colunas otimizadas**: Inclui estatísticas úteis (média, total, número de registros)

### 3. Datasets Resumidos

Cria automaticamente datasets resumidos para análise:

- `resumo_renovavel_mensal.xlsx`: Resumo mensal por empresa
- `resumo_renovavel_anual.xlsx`: Resumo anual por empresa  
- `resumo_termica_mensal.xlsx`: Resumo mensal por empresa e combustível
- `resumo_termica_anual.xlsx`: Resumo anual por empresa e combustível

### 4. Otimizações de Memória

- **Tipos categóricos**: Converte strings para `category` quando apropriado
- **Downcasting numérico**: Reduz precisão de números quando possível
- **Processamento em chunks**: Para datasets muito grandes

## Arquivos de Saída

### Para Datasets Grandes

1. **`geracao_termica.csv`**: Dataset completo em formato CSV
2. **`geracao_termica_sample.xlsx`**: Amostra de 10k linhas para visualização
3. **`geracao_termica_stats.txt`**: Estatísticas detalhadas do dataset

### Datasets Resumidos

- **`resumo_renovavel_mensal.xlsx`**: Dados mensais por empresa
- **`resumo_termica_mensal.xlsx`**: Dados mensais por empresa e combustível

## Como Usar

### Execução Normal

```bash
python orchestrator.py --mode full
```

O sistema automaticamente:
- Detecta datasets grandes
- Aplica otimizações
- Cria datasets resumidos
- Gera gráficos usando dados otimizados

### Teste de Performance

```bash
python test_performance.py
```

Este script testa:
- Tempo de processamento
- Uso de memória
- Otimizações de tipos de dados
- Salvamento de datasets grandes

## Configurações

### Limites Configuráveis

No arquivo `config/performance_config.yaml`:

```yaml
file_limits:
  excel:
    max_rows: 1000000  # Limite do Excel
    sample_size: 10000  # Tamanho da amostra
```

### Filtros de Processamento

```yaml
processing:
  filters:
    min_geracao_value: 0.1  # Valor mínimo
    max_missing_percentage: 50  # Máximo de dados faltantes
```

## Benefícios

1. **Compatibilidade**: Funciona com datasets de qualquer tamanho
2. **Performance**: Processamento mais rápido e uso eficiente de memória
3. **Flexibilidade**: Múltiplos formatos de saída
4. **Análise**: Datasets resumidos para análise eficiente
5. **Visualização**: Gráficos otimizados para grandes volumes

## Monitoramento

O sistema registra automaticamente:
- Tempo de processamento
- Uso de memória
- Tamanho dos datasets
- Otimizações aplicadas

## Próximos Passos

1. **Processamento paralelo**: Para datasets muito grandes
2. **Cache inteligente**: Para evitar reprocessamento
3. **Compressão**: Para reduzir tamanho de arquivos
4. **Streaming**: Para datasets extremamente grandes

## Troubleshooting

### Erro de Memória

Se ainda houver problemas de memória:
1. Reduza `meses_para_baixar` no config.yaml
2. Filtre por menos anos de análise
3. Use processamento em chunks

### Erro de Disco

Se houver problemas de espaço em disco:
1. Use compressão CSV
2. Salve apenas datasets resumidos
3. Configure limpeza automática de arquivos temporários
