# ORQUESTRADOR CENTRAL

Sistema de agendamento para execução automática dos orquestradores.

## 📁 Estrutura

```
orquestrador_central/
├── scheduler.py              # Agendador principal
├── config_scheduler.yaml     # Configurações de agendamento
├── instalar_dependencias.py  # Instalador de dependências
├── iniciar_servidor.py       # Iniciador do servidor web
├── teste_rapido.py          # Teste rápido do sistema
├── requirements_scheduler.txt # Dependências
├── README.md                # Este arquivo
├── runners/                 # Runners específicos
│   ├── curtailment_runner.py
│   └── precos_energia_runner.py
└── logs/                   # Logs do sistema
```

## 🚀 Instalação

1. **Instalar dependências:**
   ```bash
   python instalar_dependencias.py
   ```

2. **Configurar agendamentos:**
   Edite o arquivo `config_scheduler.yaml` conforme necessário.

## 📋 Uso

### 🖥️ Interface Web (Recomendado)
```bash
# Iniciar servidor web
python iniciar_servidor.py
```
- Abre automaticamente o navegador em `http://localhost:8080`
- Interface visual para controlar o orquestrador
- Botões para iniciar/parar e execução manual

### ⚡ Execução Manual
```bash
# Executar projeto específico
python scheduler.py --projeto curtailment
python scheduler.py --projeto precos_energia
```

### 🔄 Iniciar Agendador
```bash
# Iniciar agendador (execução contínua)
python scheduler.py --agendador
```

### 🧪 Teste Rápido
```bash
# Testar o sistema rapidamente
python teste_rapido.py
```

## ⚙️ Configuração

Edite `config_scheduler.yaml` para ajustar:

- **Agendamentos**: Tipos (teste, diário, semanal, mensal)
- **Horários**: Quando executar cada projeto
- **Intervalos de teste**: Para verificar funcionamento

### Tipos de Agendamento:

1. **teste**: Executa a cada X minutos (para testes)
2. **diario**: Executa diariamente em horário específico
3. **semanal**: Executa semanalmente em dia e horário específicos
4. **mensal**: Executa mensalmente em dia e horário específicos

## 📊 Logs

Os logs são salvos em `logs/scheduler.log` com informações detalhadas sobre:

- Execuções dos projetos
- Erros e sucessos
- Configurações de agendamento

## 🔧 Automação no Windows

Para executar automaticamente na inicialização do Windows:

```batch
schtasks /create /tn "Orquestrador Central" /tr "python C:\path\to\iniciar_servidor.py" /sc onstart /ru System
```

## 📅 Agendamentos Configurados

### Curtailment
- **Teste**: A cada 3 minutos (para verificar funcionamento)
- **Diário**: 08:00 - Relatório diário
- **Semanal**: Segunda-feira 09:00 - Relatório semanal

### Preços de Energia BR
- **Teste**: A cada 5 minutos (para verificar funcionamento)
- **Diário**: 07:30 - Atualização diária
- **Mensal**: Dia 5 às 10:00 - Relatório mensal

## 🛠️ Troubleshooting

### Problemas Comuns

1. **Erro de dependência**: Execute `python instalar_dependencias.py`
2. **Erro de caminho**: Verifique se os projetos existem nos caminhos corretos
3. **Erro de permissão**: Execute como administrador se necessário
4. **Porta ocupada**: Mude a porta 8080 se necessário

### Logs Detalhados

Verifique `logs/scheduler.log` para informações detalhadas sobre erros e execuções.

## 🎯 Como Testar

1. **Teste Rápido:**
   ```bash
   python teste_rapido.py
   ```

2. **Interface Web:**
   ```bash
   python iniciar_servidor.py
   ```

3. **Execução Manual:**
   ```bash
   python scheduler.py --projeto curtailment
   ```

## 📈 Monitoramento

- **Interface Web**: Visual em tempo real
- **Logs**: Arquivo `logs/scheduler.log`
- **Testes**: Gatilhos a cada 3-5 minutos para verificar funcionamento

## 🔧 Problemas Conhecidos e Soluções

### 1. Terminal "Travando"
- **Problema**: O terminal pode parecer "travado" quando o scheduler está rodando
- **Solução**: Use a interface web em `http://localhost:8080` para controle
- **Explicação**: O scheduler roda em loop contínuo, o que pode parecer que travou

### 2. Erro de Agendamento Mensal
- **Problema**: `AttributeError: 'Job' object has no attribute 'month'`
- **Solução**: ✅ Corrigido na versão atual
- **Explicação**: A biblioteca `schedule` não suporta `.month.day()` diretamente

### 3. Erro de Execução Manual
- **Problema**: Execução manual retorna erro vazio
- **Solução**: ✅ Corrigido - removidos TODOS os emojis de todos os arquivos
- **Explicação**: Emojis causavam `UnicodeEncodeError` no Windows. Script automatizado removeu emojis de executar.py, data_ingest.py e outros arquivos.

### 4. Caminho Incorreto do Projeto
- **Problema**: Runner não encontrava o projeto "Precos de Energia BR"
- **Solução**: ✅ Corrigido - ajustado nome do diretório (P maiúsculo)
- **Explicação**: Diferença entre nome configurado e nome real do diretório 