# Orquestrador Central ONS - Atualização 2025

## 📋 Resumo das Mudanças

Este documento detalha as atualizações implementadas no sistema de orquestração central conforme solicitação:

### ✅ Mudanças Implementadas

1. **Remoção de Gatilhos Automáticos**
   - Todos os agendamentos automáticos foram desabilitados
   - Sistema agora funciona **apenas em modo manual**
   - Interface web atualizada com aviso sobre o modo manual

2. **Integração de Novos Orquestradores**
   - ✅ **Geração por Usina**: `../Geracao por usina/orchestrator.py`
   - ✅ **Análise de Carga**: `../Carga/analise_carga.py`
   - ✅ **CVU Térmicas**: `../CVU termicas/main.py`

3. **Melhoria da Estrutura**
   - Sistema modular com suporte a diferentes tipos de scripts
   - Interface web modernizada e responsiva
   - Configuração centralizada no arquivo YAML

## 🔧 Arquitetura Atualizada

### Tipos de Scripts Suportados

1. **Legacy** (`script_type: "legacy"`)
   - Scripts antigos usando runners específicos
   - Exemplos: Curtailment, Preços de Energia

2. **Orchestrator** (`script_type: "orchestrator"`)
   - Scripts com múltiplos modos de execução
   - Exemplo: Geração por Usina (full, download, process, charts)

3. **Pipeline** (`script_type: "pipeline"`)
   - Pipelines complexos com diferentes modos
   - Exemplo: CVU Térmicas (full, update, viz, report, merit)

4. **Direct** (`script_type: "direct"`)
   - Scripts diretos sem argumentos especiais
   - Exemplo: Análise de Carga

### Configuração (config_scheduler.yaml)

```yaml
projetos:
  - nome: "geracao_usina"
    descricao: "Geração por Usina - ONS"
    script_path: "../Geracao por usina/orchestrator.py"
    script_type: "orchestrator"
    modes:
      - "full"
      - "download"
      - "process"
      - "charts"
```

## 🖥️ Interface Web Atualizada

### Funcionalidades

- **Design Moderno**: Interface responsiva com grid layout
- **Controle de Servidor**: Iniciar/parar o orquestrador
- **Execução Manual**: Botões específicos para cada projeto e modo
- **Logs em Tempo Real**: Acompanhamento das execuções
- **Status Visual**: Indicadores claros do estado do sistema

### URL de Acesso
```
http://localhost:8080
```

## 🚀 Como Usar

### 1. Iniciar o Sistema
```bash
cd "Codigos ONS/orquestrador_central"
python iniciar_servidor.py
```

### 2. Acessar Interface Web
- Navegador abrirá automaticamente em `http://localhost:8080`
- Use os botões para executar projetos manualmente

### 3. Projetos Disponíveis

#### Geração por Usina
- **Full**: Pipeline completo
- **Download**: Apenas download de dados
- **Process**: Apenas processamento
- **Charts**: Apenas geração de gráficos

#### CVU Térmicas
- **Full**: Pipeline completo
- **Update**: Atualização de dados (2025)
- **Viz**: Apenas visualizações
- **Report**: Apenas relatório
- **Merit**: Curva de mérito

#### Análise de Carga
- **Execução Direta**: Análise completa de carga energética

#### Sistemas Legados
- **Curtailment**: Sistema de curtailment
- **Preços de Energia**: Sistema de preços BR

## 🔧 Configurações Técnicas

### Timeout
- **Padrão**: 3600 segundos (1 hora)
- **Configurável**: via `config_scheduler.yaml`

### Logs
- **Localização**: `logs/scheduler.log`
- **Níveis**: INFO, ERROR
- **Saída**: Arquivo + Console

### Tratamento de Erros
- Timeout automático para execuções longas
- Logs detalhados de erros
- Feedback visual na interface web

## 📁 Estrutura de Arquivos

```
orquestrador_central/
├── iniciar_servidor.py          # Script de inicialização
├── scheduler.py                 # Orquestrador principal
├── config_scheduler.yaml        # Configuração dos projetos
├── runners/                     # Runners para sistemas legados
│   ├── curtailment_runner.py
│   └── precos_energia_runner.py
├── logs/                        # Logs do sistema
│   └── scheduler.log
└── README_ATUALIZACAO.md        # Esta documentação
```

## ⚠️ Observações Importantes

1. **Agendamentos Desabilitados**: Conforme solicitado, todos os agendamentos automáticos foram removidos
2. **Lógica Preservada**: As lógicas individuais dos scripts não foram alteradas
3. **Compatibilidade**: Sistema mantém compatibilidade com runners antigos
4. **Escalabilidade**: Fácil adição de novos projetos via configuração YAML

## 🔄 Próximos Passos Sugeridos

1. **Teste dos Projetos**: Executar cada projeto manualmente para verificar funcionamento
2. **Monitoramento**: Acompanhar logs para identificar possíveis ajustes
3. **Documentação de Projetos**: Cada projeto pode ter sua documentação específica
4. **Backup**: Configurar backup automático dos resultados

---

**Data da Atualização**: Janeiro 2025
**Autor**: Sistema de Orquestração Central ONS

