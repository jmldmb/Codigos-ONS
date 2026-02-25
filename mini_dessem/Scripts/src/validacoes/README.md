# Validações

Scripts de validação de componentes específicos.

## Arquivos

### `validar_sistema_completo.py`
Validação geral do sistema completo.

**Funcionalidades:**
- Testa todas as importações
- Valida dicionários de dados
- Executa mini-simulação
- Verifica curtailment em cascata

**Uso:**
```bash
python src/validacoes/validar_sistema_completo.py
```

**Validações:**
1. Importações de módulos
2. Consistência de dados
3. Simulação funcional
4. Curtailment em cascata

---

### `testar_curtailment_cascata.py`
Teste específico da lógica de curtailment em cascata.

**Funcionalidades:**
- Cenário 1: Curtailment pequeno (só prioridade 1)
- Cenário 2: Curtailment grande (atinge distribuída)
- Cenário 3: Sem curtailment

**Validações:**
- Solar distribuída preservada quando possível
- Eólica e solar centralizada cortadas primeiro
- Rateio proporcional entre P1
- Soma de curtailments correta

**Uso:**
```bash
python src/validacoes/testar_curtailment_cascata.py
```

---

### `testar_solar_centralizado_distribuido.py`
Teste da separação solar completa.

**Funcionalidades:**
- Valida médias mensais (centralizada + distribuída = total)
- Executa simulação completa
- Compara perfis horários

**Uso:**
```bash
python src/validacoes/testar_solar_centralizado_distribuido.py
```

**Validações:**
1. Soma de componentes = total
2. Simulação com separação funciona
3. Perfis são diferentes (hipótese)







