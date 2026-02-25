# Guia Rápido - CVU Termicas

## 🚀 Início Rápido

### 1. Instalação
```bash
# Instalar dependências
python install.py

# Ou manualmente
pip install -r requirements.txt
```

### 2. Execução Básica
```bash
# Pipeline completo (recomendado para primeira execução)
python main.py

# Apenas atualização de dados de 2025
python main.py --mode update

# Apenas visualizações
python main.py --mode viz

# Apenas relatório
python main.py --mode report
```

## 📁 Estrutura do Projeto

```
CVU termicas/
├── 📄 main.py              # Script principal
├── 📄 config.yaml          # Configurações
├── 📄 requirements.txt     # Dependências
├── 📄 install.py          # Instalador
├── 📄 exemplo_uso.py      # Exemplos de uso
├── 📁 scripts/            # Scripts modulares
│   ├── data_ingest.py     # Captura de dados
│   ├── data_process.py    # Processamento
│   ├── data_viz.py        # Visualização
│   └── report_gen.py      # Relatórios
├── 📁 data/               # Dados
│   ├── raw/              # Dados brutos baixados
│   ├── processed/        # Dados processados
│   └── viz/             # Dados para visualização
├── 📁 output/            # Saídas
│   ├── charts/          # Gráficos gerados
│   └── reports/         # Relatórios HTML
└── 📁 logs/             # Logs de execução
```

## 🔧 Funcionalidades

### Captura de Dados
- **Download histórico**: 2020-2024 (apenas uma vez)
- **Download atual**: 2025 (atualiza a cada execução)
- **Verificação**: Valida integridade dos arquivos
- **Resumo**: Estatísticas dos dados baixados

### Processamento
- **Limpeza**: Remove duplicatas e valores inválidos
- **Features**: Adiciona colunas derivadas (ano, mês, etc.)
- **Resumos**: Cria tabelas agregadas por ano, usina, mês
- **Validação**: Verifica qualidade dos dados

### Visualização
- **Timeline**: Evolução temporal do CVU
- **Boxplot**: Distribuição por ano
- **Top usinas**: Ranking das usinas com maior CVU
- **Padrão mensal**: Sazonalidade dos dados
- **Dashboard interativo**: HTML com Plotly

### Relatórios
- **HTML responsivo**: Relatório completo e moderno
- **Gráficos integrados**: Visualizações no relatório
- **Tabelas resumo**: Dados tabulados
- **Estatísticas**: Métricas principais

## 📊 Dados de Entrada

**Fonte**: ONS - Operador Nacional do Sistema Elétrico
**URL**: https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/cvu_usitermica_se/
**Formato**: Parquet
**Período**: 2020-2025
**Estrutura esperada**:
- `data`: Data da observação
- `usina`: Nome da usina
- `cvu`: Custo Variável Unitário (R$/MWh)

## 🎯 Casos de Uso

### Primeira Execução
```bash
python main.py
```
- Baixa todos os dados históricos
- Processa e limpa os dados
- Gera visualizações
- Cria relatório completo

### Atualização Diária
```bash
python main.py --mode update
```
- Baixa apenas dados de 2025
- Reprocessa dados atualizados
- Mantém histórico anterior

### Análise Rápida
```bash
python main.py --mode viz
```
- Gera apenas visualizações
- Útil para análise exploratória

### Relatório Sob Demanda
```bash
python main.py --mode report
```
- Gera relatório com dados existentes
- Não baixa novos dados

## 📈 Saídas Geradas

### Gráficos (PNG)
- `cvu_timeline.png`: Evolução temporal
- `cvu_by_year.png`: Distribuição por ano
- `top_usinas_cvu.png`: Ranking de usinas
- `monthly_pattern.png`: Padrão mensal

### Dashboard Interativo (HTML)
- `dashboard_interativo.html`: Dashboard completo

### Relatórios (HTML)
- `relatorio_cvu_YYYYMMDD_HHMM.html`: Relatório completo

### Dados Processados (Parquet)
- `cvu_complete.parquet`: Dados completos
- `summary_yearly.parquet`: Resumo anual
- `summary_usina.parquet`: Resumo por usina
- `summary_monthly.parquet`: Resumo mensal

## 🔍 Monitoramento

### Logs
- `logs/cvu_termicas.log`: Log principal
- `logs/scheduler.log`: Log do agendador (se usado)

### Verificação de Status
```bash
# Verificar dados baixados
python scripts/data_ingest.py

# Verificar processamento
python scripts/data_process.py

# Verificar visualizações
python scripts/data_viz.py
```

## ⚙️ Configuração

### config.yaml
```yaml
data:
  base_url: "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/cvu_usitermica_se/"
  filename_pattern: "CVU_USINA_TERMICA_{year}.parquet"
  years: [2020, 2021, 2022, 2023, 2024, 2025]

paths:
  raw_data: "data/raw"
  processed_data: "data/processed"
  viz_data: "data/viz"
  output_charts: "output/charts"
  output_reports: "output/reports"
  logs: "logs"
```

## 🚨 Troubleshooting

### Erro de Download
- Verificar conexão com internet
- Verificar se URLs estão acessíveis
- Verificar espaço em disco

### Erro de Processamento
- Verificar se dados foram baixados
- Verificar estrutura dos dados
- Verificar logs para detalhes

### Erro de Visualização
- Verificar se dados foram processados
- Verificar dependências (matplotlib, plotly)
- Verificar permissões de escrita

## 📞 Suporte

Para problemas ou dúvidas:
1. Verificar logs em `logs/cvu_termicas.log`
2. Executar `python exemplo_uso.py` para testes
3. Verificar se todas as dependências estão instaladas
4. Verificar se a estrutura de diretórios está correta 