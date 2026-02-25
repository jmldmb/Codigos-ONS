# Configuração do Filtro de Visualização

## Como Configurar o Número de Meses para Trás

O filtro de visualização agora é configurável através do arquivo `config/config.yaml`.

### Configuração Atual
```yaml
visualization:
  filter:
    months_back: 1  # Número de meses para trás (ajustável)
```

### Exemplos de Configuração

#### Para mostrar apenas o mês atual:
```yaml
visualization:
  filter:
    months_back: 1
```

#### Para mostrar 2 meses para trás:
```yaml
visualization:
  filter:
    months_back: 2
```

#### Para mostrar 3 meses para trás:
```yaml
visualization:
  filter:
    months_back: 3
```

### Como Funciona

1. **Data de Início**: Calculada como N meses para trás do mês atual
2. **Data de Fim**: 
   - Se há dados PMO disponíveis: usa a data máxima dos dados PMO
   - Se não há dados PMO: usa o último dia do mês atual

### Exemplo Prático

**Configuração**: `months_back: 1`
**Execução em agosto de 2024**:
- **Data início**: 1º de agosto de 2024
- **Data fim**: 
  - Com dados PMO até 31/08/2024: 31 de agosto de 2024
  - Sem dados PMO: 31 de agosto de 2024

**Configuração**: `months_back: 2`
**Execução em agosto de 2024**:
- **Data início**: 1º de julho de 2024
- **Data fim**: 
  - Com dados PMO até 31/08/2024: 31 de agosto de 2024
  - Sem dados PMO: 31 de agosto de 2024

### Aplicação

O filtro é aplicado automaticamente aos gráficos:
- `hairy_chart.png`
- `comparison_chart.png`

Quando você executa o script `main.py` com as opções:
- `--create-viz`
- `--full-pipeline`
