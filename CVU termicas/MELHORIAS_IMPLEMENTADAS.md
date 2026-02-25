# Melhorias Implementadas no Sistema CVU Termicas

## Resumo das Melhorias

Este documento descreve as melhorias implementadas na funcionalidade de match dos nomes entre os arquivos CVU e Capacidade Geração no projeto CVU Termicas, incluindo a integração de dados de inflexibilidade.

## 1. Arquivo de Equivalência de Nomes

### O que foi implementado:
- **Arquivo de mapeamento**: Criado arquivo `equivalencia de nomes.xlsx` em `data/raw/`
- **Estrutura**: 68 mapeamentos entre nomes CVU e nomes Capacidade
- **Colunas**: 
  - `nom_usina_cvu`: Nome da usina na base CVU
  - `nom_usina_capacidade`: Nome correspondente na base Capacidade

### Benefícios:
- Permite mapeamento manual de casos específicos onde os nomes não coincidem
- Aumenta significativamente a taxa de correspondência
- Mantém auditabilidade dos casos sem equivalência

## 2. Filtro de Tipo de Usina

### O que foi implementado:
- **Filtro automático**: Apenas usinas com `nom_tipousina` = 'TÉRMICA' ou 'NUCLEAR'
- **Aplicação**: Filtro aplicado na função `load_capacity_data()`
- **Resultado**: Redução de 5309 para 1464 registros (apenas térmica/nuclear)

### Benefícios:
- Foca apenas nas usinas relevantes para análise CVU
- Elimina ruído de usinas eólicas, fotovoltaicas e hidroelétricas
- Melhora performance e precisão da análise

## 3. Sistema de Mapeamento Inteligente

### O que foi implementado:
- **Função `apply_equivalencia_mapping()`**: Aplica mapeamento de equivalência
- **Lógica**: Usa nome mapeado quando disponível, senão usa nome original
- **Rastreamento**: Identifica quais correspondências usaram mapeamento

### Benefícios:
- Aumenta taxa de correspondência de forma controlada
- Mantém rastreabilidade dos mapeamentos aplicados
- Permite auditoria dos casos sem equivalência

## 4. Relatórios de Auditoria Melhorados

### O que foi implementado:
- **Relatórios detalhados**: Incluem informações sobre mapeamentos aplicados
- **Arquivos gerados**:
  - `audit_report_YYYY_MM_weekN_matches.csv`: Correspondências encontradas
  - `audit_report_YYYY_MM_weekN_cvu_only.csv`: Usinas apenas na base CVU
  - `audit_report_YYYY_MM_weekN_capacity_only.csv`: Usinas apenas na base Capacidade
  - `audit_report_YYYY_MM_weekN_summary.txt`: Resumo completo

### Benefícios:
- Auditabilidade completa do processo
- Identificação de casos que precisam de atenção
- Base para melhorias futuras no mapeamento

## 5. Resultados dos Testes

### Taxa de Correspondência:
- **Antes**: ~70-80% (estimativa)
- **Depois**: 98.8% (teste com dados 2025/01/semana 1)

### Estatísticas do Teste:
- **Correspondências encontradas**: 85
- **Usinas apenas na base CVU**: 1
- **Usinas apenas na base Capacidade**: 163
- **Mapeamentos aplicados**: 64

## 6. Arquivos Modificados

### Scripts Atualizados:
- `scripts/merit_order.py`: Versão completamente atualizada
- `scripts/merit_order_improved.py`: Versão alternativa (mantida para referência)

### Novos Arquivos:
- `data/raw/equivalencia de nomes.xlsx`: Arquivo de mapeamento
- `teste_merit_order.py`: Script de teste da funcionalidade
- `teste_final.py`: Script de teste final
- `examinar_equivalencia.py`: Script para examinar dados
- `examinar_capacidade.py`: Script para examinar dados
- `examinar_cvu.py`: Script para examinar dados

## 7. Integração de Dados de Inflexibilidade

### O que foi implementado:
- **Arquivo de inflexibilidade**: `inflexibilidade.xlsx` em `data/raw/`
- **Estrutura**: Formato wide com 37 usinas e 12 colunas (meses 1-12)
- **Integração**: Dados aplicados automaticamente na curva de mérito
- **Cálculo**: Potência flexível = Potência total - Inflexibilidade
- **Verificação**: Check de consistência (inflexibilidade < potência total)

### Benefícios:
- Curva de mérito mais realista considerando inflexibilidade operacional
- Redução significativa da potência disponível para despacho
- Identificação automática de inconsistências nos dados
- Relatórios detalhados com informações de inflexibilidade

### Resultados do Teste:
- **Total de usinas**: 477 registros
- **Usinas com inflexibilidade > 0**: 48
- **Potência total original**: 29,031.02 MW
- **Potência flexível**: 27,330.75 MW
- **Redução total**: 1,700.26 MW (5.9%)
- **Inconsistências encontradas**: 1 (KARKEY 013)

## 8. Como Usar

### Execução Básica:
```python
from scripts.merit_order import MeritOrderGenerator

generator = MeritOrderGenerator()
result = generator.generate_merit_order(2025, 1, 1)
```

### Verificação de Funcionalidade:
```bash
python teste_final.py
```

### Arquivos Gerados:
- `merit_order_curve_YYYY_MM_weekN.png`: Curva de mérito com inflexibilidade
- `merit_order_table_YYYY_MM_weekN.csv`: Tabela com dados de inflexibilidade
- Relatórios de auditoria com informações detalhadas

## 9. Próximos Passos

### Melhorias Futuras:
1. **Expansão do mapeamento**: Adicionar mais casos ao arquivo de equivalência
2. **Automatização**: Implementar sugestões automáticas de mapeamento
3. **Validação**: Adicionar validação de qualidade dos mapeamentos
4. **Interface**: Criar interface para gerenciar mapeamentos
5. **Expansão de inflexibilidade**: Incluir mais usinas nos dados de inflexibilidade
6. **Análise sazonal**: Implementar análise de sazonalidade da inflexibilidade

### Manutenção:
1. **Atualização periódica**: Revisar e atualizar arquivo de equivalência
2. **Monitoramento**: Acompanhar taxa de correspondência ao longo do tempo
3. **Documentação**: Manter documentação atualizada
4. **Validação de inflexibilidade**: Verificar consistência dos dados de inflexibilidade

## 10. Considerações Técnicas

### Dependências:
- `pandas`: Manipulação de dados
- `pyarrow`: Leitura de arquivos parquet
- `openpyxl`: Leitura de arquivos Excel
- `matplotlib`: Geração de gráficos
- `seaborn`: Estilização de gráficos

### Performance:
- **Filtro de tipo**: Reduz significativamente o volume de dados processados
- **Mapeamento eficiente**: Usa dicionário para lookup rápido
- **Logging**: Permite acompanhamento do processo

### Robustez:
- **Tratamento de erros**: Verificações de existência de arquivos
- **Fallback**: Usa nome original quando mapeamento não existe
- **Logging detalhado**: Facilita debugging

## 11. Conclusão

As melhorias implementadas resultaram em:
- **Aumento significativo** na taxa de correspondência (98.8%)
- **Melhor auditabilidade** do processo de match
- **Foco nas usinas relevantes** (térmica/nuclear)
- **Flexibilidade** para ajustes manuais via arquivo de equivalência
- **Manutenção** dos arquivos de auditoria para casos sem equivalência
- **Integração de inflexibilidade** para curva de mérito mais realista
- **Redução de 5.9%** na potência disponível para despacho
- **Identificação automática** de inconsistências nos dados

O sistema agora está mais robusto, preciso e auditável, permitindo análises mais confiáveis da curva de mérito das usinas térmicas brasileiras, considerando tanto o mapeamento de nomes quanto as restrições operacionais de inflexibilidade. 