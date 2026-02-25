# Teste de Envio WhatsApp

Este projeto contém um código de teste para envio de mensagens e imagens via WhatsApp, preparado para posterior integração com envio de relatórios.

## 📁 Arquivos Criados

- `teste_whatsapp.py` - Script principal de teste
- `configurar_whatsapp.py` - Script de configuração e instalação
- `requirements_whatsapp.txt` - Lista de dependências
- `README_WHATSAPP.md` - Este arquivo de instruções

## 🚀 Como Usar

### 1. Configuração Inicial

Execute o script de configuração:

```bash
python configurar_whatsapp.py
```

Este script irá:
- Verificar se as dependências estão instaladas
- Instalar automaticamente as dependências necessárias
- Guiar você através da configuração

### 2. Preparação do WhatsApp Web

1. Abra o WhatsApp Web no navegador: https://web.whatsapp.com
2. Faça login escaneando o QR Code com seu celular
3. **IMPORTANTE**: Mantenha a aba do WhatsApp Web aberta durante os testes
4. Não minimize o navegador durante a execução

### 3. Executar o Teste

```bash
python teste_whatsapp.py
```

O script irá:
- Solicitar o número de telefone para teste
- Enviar uma mensagem de teste
- Tentar enviar uma imagem (se existir)
- Mostrar o status de cada operação

## 📋 Funcionalidades

### Envio de Mensagens
```python
enviar_mensagem_teste(numero, mensagem)
```

### Envio de Imagens
```python
enviar_imagem_teste(numero, caminho_imagem, legenda)
```

## 🔧 Configuração Avançada

### Número de Telefone
- Formato: `+5511999999999` (código do país + DDD + número)
- Exemplo: `+5511999999999` para Brasil

### Imagem de Teste
- Crie um arquivo chamado `teste_imagem.png` no mesmo diretório
- Ou modifique o caminho no código: `caminho_imagem_teste = "sua_imagem.png"`

## ⚠️ Importante

1. **Não mova o mouse** durante o envio automático
2. **Mantenha o navegador aberto** e focado na aba do WhatsApp
3. **Aguarde** o tempo de espera configurado (15 segundos)
4. **Verifique** se o WhatsApp Web está logado antes de executar

## 🐛 Solução de Problemas

### Erro: "pywhatkit não encontrado"
```bash
pip install pywhatkit==5.4.3
```

### Erro: "Navegador não encontrado"
- Certifique-se de que o Chrome está instalado
- Ou instale o Chrome: https://www.google.com/chrome/

### Erro: "QR Code não escaneado"
- Abra o WhatsApp Web manualmente
- Faça login com o QR Code
- Mantenha a aba aberta

### Mensagem não enviada
- Verifique se o número está no formato correto
- Certifique-se de que o WhatsApp Web está logado
- Não minimize o navegador durante o envio

## 🔄 Integração com Relatórios

Para integrar com envio de relatórios, use as funções:

```python
# Enviar relatório como mensagem
enviar_mensagem_teste(numero, conteudo_relatorio)

# Enviar imagem do relatório
enviar_imagem_teste(numero, "relatorio.png", "Relatório Mensal")
```

### Alternativa recomendada: WAHA (WhatsApp HTTP API)

Para não depender de automação de navegador, você pode rodar o WAHA localmente e usar o cliente em `waha_client.py`:

1) Instale Node.js 22+ e Yarn, depois clone o WAHA:

```powershell
git clone https://github.com/devlikeapro/waha.git
cd waha
yarn install --frozen-lockfile
yarn gows:proto
yarn dev | cat
```

O WAHA sobe em `http://localhost:3000`.

2) Conecte a sessão `default` no Swagger em `http://localhost:3000`:
- POST `/api/sessions` com body `{ "name": "default" }`
- GET `/api/screenshot` para exibir o QR e escanear

3) No seu Python, envie assim:

```python
from waha_client import send_text, send_image

destino = "5521971482431"  # sem '+'
send_text(destino, "Relatório diário — gráficos a seguir.")
send_image(destino, r"C:\\relatorios\\grafico.png", caption="Gráfico: grafico.png")
```

Ou use o utilitário:

```powershell
python enviar_relatorios_waha.py --destino 5521971482431 --contexto "Relatório — gráficos a seguir." --arquivos C:\\relatorios\\g1.png C:\\relatorios\\g2.png
```

## 📞 Suporte

Se encontrar problemas:
1. Verifique se todas as dependências estão instaladas
2. Confirme se o WhatsApp Web está logado
3. Teste com um número válido
4. Verifique a conexão com a internet

## 📝 Logs

O script gera logs detalhados mostrando:
- Status de cada operação
- Tempo de execução
- Erros encontrados
- Resumo final dos testes

---

**Desenvolvido para integração futura com sistema de relatórios ONS** 