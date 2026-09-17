# Carga Líquida do SIN

Medição e simulação da **carga líquida** do Sistema Interligado Nacional a partir dos dados abertos
do ONS. Funde os projetos antigos `carga_liquida` (observado) e `mini_dessem` (simulador) num pacote só.

```
carga_liquida = Hidro_R + termica_flexivel

Hidro_R          = geração das UHEs classificadas como 'R' (reservatório) no cadastro manual
termica_flexivel = val_verifordemdemeritoacimadainflex + val_verifunitcommitment
```

É a parcela da carga que o operador **decide** despachar: exclui renováveis, hidro fio d'água (FD) e a
térmica forçada (inflexibilidade, razão elétrica, garantia energética, GFOM, exportação, reserva, GSUB).
A mesma identidade contábil vale para o simulador (`carga − renováveis − inflexível − FD`), o que permite
validar o modelo contra o observado.

## Estrutura

```
carga_liquida/
├── run.py                      ponto de entrada (CLI)
├── config/config.yaml          caminhos, datasets ONS, período, definição da CL, parâmetros do modelo
├── config/projecoes.yaml       premissas mensais 2026-28 (herdadas do data.py do mini_dessem)
├── src/carga_liquida/
│   ├── config.py               leitura do config, diretórios, logging
│   ├── dados/
│   │   ├── download.py         download incremental dos datasets ONS (S3 open data)
│   │   ├── ons.py              leitores dos brutos: geração por usina, despacho térmico, CMO, balanço, ENA, COFF, cadastro
│   │   └── temperatura.py      temperatura horária "Brasil" (Meteostat, 15 estações ponderadas pela carga)
│   ├── observado/
│   │   ├── carga_liquida.py    cálculo da carga líquida histórica horária
│   │   └── analises.py         hidro FD×R, CL×CMO, gráficos diários, CL×curtailment
│   ├── modelo/
│   │   ├── premissas.py        médias mensais (histórico calculado dos dados; projeções do yaml)
│   │   ├── samplers/           carga v6 (temperatura), eólica AR(1), solar cent/dist, térmica flex e corte de rede (perfis) — treino + amostragem
│   │   ├── hidro_fd.py         regressão FD = f(R, ENA, mês, hora, tipo de dia) + calibração OLS
│   │   ├── despacho.py         balanço horário: R máximo, brentq, curtailment em cascata, térmica flexível
│   │   ├── pilha_termica.py    merit order mensal: CVU semanal (ONS) x capacidade por usina
│   │   ├── preco.py            PLD pela pilha térmica do mês
│   │   ├── simulacao.py        Monte Carlo (ano × mês × cenário × dia × hora)
│   │   └── feriados.py         feriados nacionais calculados; tipo de dia DU/FDS
│   ├── validacao/comparar.py   observado vs simulado por componente (métricas + gráficos)
│   └── cli.py
├── legacy/Scripts/             scripts originais do carga_liquida (notebook exportado + validações), sem manutenção
├── legacy/mini_dessem/         projeto mini_dessem original, sem manutenção
├── Data/                       brutos (gitignored)  — config.paths.data_dir
└── Output/                     processados, parâmetros, resultados e gráficos (gitignored)
```

## Uso

```bash
pip install -r requirements.txt

python run.py baixar                 # só o que falta: geracao_usina, termica_despacho, cmo, balanco, ena, coff_*, temperatura
python run.py processar              # Data/raw -> Output/observado/*.parquet (~30 s) + temperatura processada
python run.py analisar               # observado: hidro cmo diarios curtailment
python run.py treinar                # samplers eolica solar carga termica curtailment_rede + hidro_fd + pilhas térmicas -> Output/modelo/ (~40 s)
python run.py simular --anos 2024 2025 -n 6 --seed 42   # Monte Carlo -> Output/modelo/ (~4 s por ano)
python run.py validar                # observado vs simulado -> Output/validacao/
python run.py tudo                   # tudo acima, em ordem
```

Variáveis de ambiente `CARGA_LIQUIDA_DATA_DIR` e `CARGA_LIQUIDA_OUTPUT_DIR` sobrescrevem `config.paths.*`
(útil em worktrees). O cadastro `Data/raw/cadastros/cadastro.xlsx` (colunas `nom_usina`, `Classificação`
= `R`|`FD`) é insumo manual e **não** é baixado.

Como biblioteca:

```python
import sys; sys.path.insert(0, "src")
from carga_liquida.observado import carga_liquida as cl, analises
df = cl.carregar_historico()                 # din_instante, FD, R, termica_flexivel, carga_liquida_historica, ano, mes, dia, hora
df_cmo = analises.carga_liquida_com_cmo()    # + val_cmo (média horária dos patamares semi-horários)

from carga_liquida.modelo import simulacao, premissas
sim = simulacao.simular(anos=[2026], num_simulacoes=20, seed=1, salvar=False)   # um registro por cenário/dia/hora
prem = premissas.montar()                    # tabela (ano, mês): carga, eólica, solar, ENA, térmica, inflexterm
```

## Dados

| Dataset (config) | Fonte | Pasta local | Uso |
|---|---|---|---|
| `geracao_usina` | ONS `geracao_usina_2_ho` (mensal, 2022-01+) | `Data/raw/geracao por usina/` | geração horária por usina → FD/R, tipos, MMGD |
| `termica_despacho` | ONS `geracao_termica_despacho_2_ho` (mensal) | `Data/raw/termoeletrica/` | componentes verificadas do despacho térmico |
| `cmo` | ONS `cmo_tm` (anual) | `Data/raw/CMO/` | CMO semi-horário (Sudeste por padrão) |
| `balanco` | ONS `balanco_energia_subsistema_ho` (anual) | `baterias/Data/balanco` (reaproveitado) | carga, térmica total, eólica, solar do SIN |
| `ena` | ONS `ena_subsistema_di` (anual) | `Data/raw/ENA/` | ENA armazenável diária (soma SIN) |
| `coff_eolica`, `coff_fotovoltaica` | ONS `restricao_coff_*_tm` (mensal) | `baterias/Data/coff_*` (reaproveitado) | curtailment (energético ENE × rede CNF/REL) e potencial renovável. Sem restrição = `''` até 2024-12 e `NaN` desde 2025-01 |
| `temperatura` | Meteostat bulk (NOAA ISD/SYNOP), 15 aeroportos | `Data/raw/temperatura/` | perfil horário da carga (sampler v6) |
| `cvu` | ONS `cvu_usitermica_se` (anual) | `Data/raw/CVU/` | CVU semanal por usina → pilha térmica |

Saídas em `Output/`:

- `observado/carga_liquida_historica.parquet` (+ `.xlsx`), `geracao_por_tipo.parquet`, `termica_componentes.parquet`
- `hidro_reservatorio/` — mensal, dia da semana, horário/heatmaps, distribuições, séries diárias, `RELATORIO_RESUMO.txt`
- `cmo/` — scatters CL×CMO (grade mensal e geral), `carga_liquida_cmo.csv`, `resumo_mensal.csv`
- `diarios/` — últimos N dias: despacho térmico empilhado por componente; geração por tipo + carga líquida
- `curtailment/` — scatters CL×curtailment por ano/mês, `carga_liquida_curtailment.csv`, `resumo_mensal.csv`
- `modelo/params/` — `eolica.json`, `solar_centralizada.json`, `solar_distribuida.json`, `carga_v6.json`, `hidro_fd.json`
- `modelo/` — `resultados_simulacao.parquet` (cenário × dia × hora), `resumo_mensal.csv`, `pilhas_termicas.csv`
- `validacao/` — `metricas.csv`, `metricas_por_ano_mes.csv`, `comparacao_horaria.csv`, gráficos (médias mensais,
  perfil horário por mês com faixa P10–P90, dispersão, decomposição do erro, erro por hora)

## Modelo

Mesma identidade nos dois lados: **observado** `R + térmica_flex` ≡ **simulado** `carga − eólica_pós − solar_pós − inflexterm − FD`.

| Bloco | Premissa (herdada do mini_dessem) | Treino / fonte |
|---|---|---|
| Carga v6 | `carga_norm(h) = a[tipo,mês,h] + b[tipo,mês,h]·temp(h)`, Σ=24, DU vs FDS (fim de semana + feriado), ajuste de viés por hora | balanço SIN + temperatura; MAPE 3,9 %, R² 0,87 |
| Eólica | perfil médio por mês × ruído AR(1) multiplicativo `Y = μ(1+Z)`, φ≈0,95 | potencial COFF (geração + corte), 2023-10+ |
| Solar | perfil determinístico por mês; centralizada (expoente 1,5) e distribuída (1,0) | COFF FV / geração usina não-MMGD; MMGD |
| Curtailment de rede (`curtailment_rede: true`) | **premissa mensal exógena** (CNF/REL do COFF: restrições regionais de transmissão, quase todo NE, que ocorrem mesmo com o SIN precisando da energia): histórico = observado; projeção em `projecoes.yaml`. Alocado por hora pelo perfil observado (mês × hora; pica às 7–9h, ~20 % do potencial eólico vs ~6 % de madrugada), limitado ao potencial, e subtraído da eólica e da solar centralizada **antes** do despacho. O corte energético (ENE) continua endógeno | COFF 2023-10+ |
| Hidro FD | `FD = c + ghr[hora]·R − 8·(R/GW)² + 0,09·ENA + mês + hora + FDS` — a resposta ao R varia com a hora (0,91 ao meio-dia, 0,76 às 19h) e satura (marginal ≈ 0,45 em R = 20 GW, 0,2 em 35 GW); legado: ghr único 0,33 | histórico FD/R + ENA diária; MAE 1,77 GW, R² 0,91 |
| Valor da água (`termica_flexivel: valor_agua`, padrão) | **premissa = preço-base semanal por subsistema** (papel do DECOMP): histórico = mediana semanal do CMO de cada subsistema (`valor_agua_fonte: cmo`) ou CVU da pilha na térmica de mérito observada (`pilha`); projeção em `projecoes.yaml` (número ou por subsistema; ou derivado da térmica base pela pilha). Base **comprometida** da semana = usinas com CVU ≤ VA do seu subsistema, ligadas o dia inteiro | CMO / térmica observada |
| Despacho (`despachar_va`, papel do DESSEM) | hidro R fecha o balanço entre 14,5 e 42 GW; R no máximo → térmica extra por mérito; R no mínimo → base reduzida da mais cara para a mais barata **até o mínimo técnico de cada usina**, depois curtailment (eólica + solar cent. pro rata, por fim MMGD). **PLD horário = recurso marginal**: VA · CVU da extra · CVU da parcialmente reduzida · piso | — |
| Alternativas | `exogena`: térmica base mensal como premissa (MW), perfil horário observado ou flat; `residual`: legado (térmica só na saturação) | — |
| Pilha térmica | **semanal**: CVU da semana operativa × capacidade **flexível** (máx. gerado nas 52 semanas anteriores − inflexibilidade média) + subsistema, por `cod_usinaplanejamento`; nuclear fora por definição (CEG `UTN`); ~15 GW. **Mínimo técnico** por usina (`pilha_minimo_quantil`, P10): menor nível sustentado da parcela flexível quando ligada (horas com vizinhas ligadas, sem rampa; mediana das 52 semanas) — piso da redução intradiária | datasets `cvu` + `termica_despacho` |

Premissas mensais (`modelo/premissas.py`): nos anos observados tudo vem dos dados — carga (+ exportação),
eólica potencial, solar cent/dist, ENA armazenável SIN, térmica total (o `data.py` do legado era uma cópia
manual do BALANCO_ENERGIA). Para 2026-28, `config/projecoes.yaml`.

### Validação (2022-01 → 2026-09, 6 cenários; média dos cenários vs observado, hora a hora)

| componente | obs (MW) | sim (MW) | viés | MAE | MAE/média | R² |
|---|---|---|---|---|---|---|
| carga | 76.359 | 76.355 | −4 | 2.832 | 3,7 % | 0,87 |
| eólica pós-corte | 11.480 | 11.461 | −19 | 2.241 | 19,5 % | 0,66 |
| solar pós-corte | 7.002 | 6.926 | −76 | 754 | 10,8 % | 0,98 |
| hidro FD | 24.089 | 24.096 | +8 | 1.826 | 7,6 % | 0,90 |
| hidro R | 25.001 | 25.169 | +167 | 2.670 | 10,7 % | 0,74 |
| térmica flexível | 1.203 | 1.233 | +30 | 633 | 53 % | 0,55 (mensal ~0,8) |
| **carga líquida** | **26.175** | **26.367** | **+192** | **2.727** | **10,4 %** | **0,74** |
| PLD vs CMO SE (R$/MWh) | 109 | 129 | +20 | 51 | — | **0,67** |
| curtailment eól. + solar cent. (COFF, 2023-10+) | 2.951 | 2.494 | −457 | 1.723 | 58 % | 0,60 |
| — só energético (ENE) | 1.618 | 1.171 | −447 | 1.127 | 70 % | 0,53 |

Histórico das duas últimas mudanças (mesma janela): (1) antes do corte de rede como premissa, e com o bug do `''` no
COFF que inflava o potencial 2023-10→2024-12 em ~0,5 GW: eólica +685, carga líquida −457, hidro R −312 — o viés da
carga líquida era quase todo o corte de rede. (2) Antes do mínimo técnico (base reduzida até zero na sobra): térmica
R² 0,46 / intradiário MAE 366, carga líquida R² 0,73 / MAE 2.780, ENE 967. **Teste pareado por dia** (mesma semente)
do mínimo técnico: térmica intradiária MAE 366 → 208, melhor em 98 % dos dias (p 10⁻⁸⁷); carga líquida intradiária
1.886 → 1.806, 90 % dos dias; ENE diário melhor em 60 %; PLD intradiário 26,0 → 26,4 (pior em 54 % dos dias, p 3·10⁻⁴)
e nível diário da térmica 544 → 597 (pior em 58 %) — nas horas com ENE observado > 1 GW o modelo mantém 1,9 GW
de térmica (obs 1,7; antes 1,0). Aceito: a forma horária da térmica e da carga líquida melhora muito; o PLD fica
neutro; o que piora é pequeno e explicado (Sergipe/GNA com mínimo ≈ 95 % da capacidade flexível).

Por que o mínimo técnico e não "reduzir até zero" (2025-26, horas com corte energético > 1 GW = 25 % das horas):
a inflexibilidade fica onde está (4,8 GW), a ordem de mérito cai de 1,95 para 1,09 GW e o **unit commitment sobe de
0,24 para 0,68 GW** — a usina comprometida pelo DECOMP não desliga no vale solar, é reduzida ao mínimo e re-rotulada.
Das usinas comprometidas no dia, 23 % desligam de fato, 40 % ficam abaixo de 40 % da capacidade e 34 % acima de 80 %.
Quem fica ligada é ciclo combinado grande e carvão (Sergipe 1,6 GW a 86 %, Pecém, Itaqui, Parnaíba V, Maranhão 4/5);
quem desliga são motores e ciclos abertos pequenos (Prosperidade, Poraque, Jaraqui) e algumas baratas (Marlim Azul,
Pampa Sul, Aparecida). Correlação entre usinas desligar × CVU = −0,38: o ONS desliga quem *consegue* ciclar, não quem
é cara. O piso P10 por usina (estimado sem usar as horas de sobra, causal) fecha 2/3 do erro: térmica flexível das
comprometidas nas horas de sobra obs 1,9 GW (2025) / 1,5 (2026) vs Σ mínimos 1,6 / 1,2 vs zero.

Regimes simulados: hidro marginal 83 %, curtailment 12 %, base reduzida 1 %, extra 3 % (observado: ±50 % do patamar semanal em 78 % das horas; abaixo 16 %, concentradas 8–14h com R ≈ 15,6 GW; acima 6 %, 16–22h com R p90 38,5 GW). **Componente intradiária** (`validacao/metricas_intradiarias.csv`, desvios da média diária): PLD corr 0,52 / R² 0,26 / MAE 26; hidro R corr 0,93 / R² 0,82; térmica corr 0,35 / MAE 209 (R² −0,6: ainda pior que flat, mas era −4,4); spikes horários (> 1,5× a mediana da semana operativa, mesma definição nos dois lados; obs 3,3 % das horas, sim 0,7 %): precisão 0,14, recall 0,03 — o modelo não acerta *quando* o degrau ocorre. Qualquer mudança de estrutura horária deve ser julgada por estas métricas em teste pareado por dia, não pelo desvio-padrão.

Comparação dos modos (mesma simulação 2022-25): `valor_agua` com `fonte: pilha` (sem usar o CMO) → PLD R² 0,51, térmica R² 0,76; `exogena` → térmica R² 0,82, carga líquida viés −317, PLD R² 0,51; `residual` (legado) → térmica ≈ 0, carga líquida viés −716, PLD R² ≈ 0. O ganho de R² 0,70 vem do nível do patamar ser premissa; o modelo entrega a modulação.

Por que a base é comprometida o dia inteiro: o "unit commitment" do ONS (27 % da térmica flexível) tem pico às 8–13h e mínimo às 18–20h, com correlação intradiária **negativa** com a carga líquida — são as mesmas unidades da ordem de mérito, rotuladas como UC no vale solar (o preço não as chamaria) e como mérito à noite; a soma é quase flat no dia (CV 0,16). Por que o VA é por subsistema: em mar/2025 o CMO SE/S foi ~350 e N/NE ~10; 1,3 GW de térmicas do N/NE com CVU 111–295 não rodaram. Pilha semanal + VA por subsistema + base comprometida levaram a térmica de R² 0,30 para 0,49 (mensal 0,68 → 0,81) sem nenhum fator de ajuste. `min_hidro_reservatorio` 14,5 GW do legado se sustenta (12 ou 10,5 GW pioram R, carga líquida e curtailment).

Por que a térmica flexível é premissa e não decisão do modelo: o despacho herdado só chamava térmica quando a
hidro batia no limite (térmica ≈ 0 em 99,7 % das horas vs 48 % observado), e nenhuma variável disponível a
prevê — o valor da água implícito (CVU marginal despachado) correlaciona só 0,5 com o CMO, e `flex ~ EAR + ENA + mês`
dá R² 0,5 (mudança de regime em 2025-26). Já `CMO ~ térmica_flex` dá R² 0,82 mensal. Ver `Output/modelo/valor_agua_implicito.parquet`.

Limitações restantes: o curtailment energético simulado fica ~30 % abaixo do observado — o terço do erro de térmica
que o mínimo técnico não fecha (usinas que nem ao mínimo vão: inflexibilidade real maior que a declarada, não está em dado
público) e a eólica amostrada, que não reproduz os dias de vento extremo (média dos cenários regride à média do mês);
o corte de rede é premissa, não previsão; o PLD tem piso 61 (CMO observado chega a 0) e subestima picos (out/2024: 360 vs 516).

## Premissas embutidas (herdadas do código original)

- Período a partir de 2022-01-01; geração do **SIN** inteiro (inclui MMGD), CMO do **Sudeste**.
- Térmica flexível = só ordem de mérito acima da inflexibilidade + unit commitment.
- Horas sem registro no despacho térmico recebem térmica flexível = 0.
- Eixos fixos nos scatters: carga líquida 10–50 GW, CMO 0–2000 R$/MWh.

## Diferenças em relação ao legado

- **Aliases de usinas renomeadas pelo ONS** (`config.cadastro.aliases`): `Corumbá I → Corumbá` (nov/2024) e
  `Sobradinho → UHE Sobradinho` (out/2025). O legado deixava esses reservatórios silenciosamente fora de R.
  UHEs ainda sem classificação são listadas no log a cada `processar`.
- CMO horário = média dos dois patamares semi-horários (o legado casava só o patamar `:00`).
- Curtailment vem dos datasets `RESTRICAO_COFF_*` (desde 2023-10), com o método validado no módulo
  `baterias/` (37,2 TWh em 2025), separado em energético (ENE) e de rede (CNF/REL). Até 2024-12 o ONS marca
  "sem restrição" com `''` (não `NaN`); tratar `''` como restrição inflava o potencial em ~0,5 GW médios.
- Fora isso, `processar` reproduz o parquet antigo exatamente (2022-01 → 2025-09; out/2025 difere porque
  o ONS revisou o bruto após a última execução do legado).
- **Temperatura**: a fonte original (`temperatura_processada.parquet`) não existia mais; substituída por
  Meteostat (estações WMO de aeroportos, pesos ≈ carga). Climatologia ~1 °C acima da hardcoded; o v6 foi retreinado.
- **`inflexterm`** (config.modelo): padrão `termica_forcada` (= térmica total − flexível observada); o legado
  usava a térmica total (`termica_total`), que dá viés −1,6 GW na carga líquida em vez de −0,7 GW.
- **Carga + exportação** (`carga_inclui_intercambio`): a carga do balanço exclui a exportação, mas a
  geração observada não; somar fecha a identidade contábil (~0,2–1 GW).
- **Hidro FD** recalibrada por OLS em 2022-25 (MAE 1,7 GW vs 1,85 GW dos parâmetros do legado nos mesmos dados).
- **Cascata de curtailment**: quando eólica + solar centralizada = 0, o legado não cortava nada; aqui a distribuída é cortada.
- **Corte de rede como premissa** (`curtailment_rede`): o legado (e o despacho) só produz corte energético; o de rede
  (CNF/REL, 2 GW médios em 2025) entra como premissa mensal com perfil horário observado, no padrão da térmica flexível.
- **Mínimo técnico na sobra** (`pilha_minimo_quantil`): a base comprometida reduz até o piso de cada usina, não até zero;
  a ordem continua da mais cara para a mais barata (na realidade o ONS desliga quem consegue ciclar, mas o total é o que
  fecha o balanço). `0` volta ao comportamento antigo.
- **Despacho por valor da água** (`termica_flexivel: valor_agua`, estrutura DECOMP → DESSEM) com preço horário pelo recurso
  marginal, VA semanal por subsistema e base comprometida; `exogena` (térmica base mensal) e `residual` (legado) continuam
  como opções. **Testado e descartado (sem ganho nas métricas ou reprovado no teste intradiário):** fator de despacho; proxy
  de disponibilidade por geração recente (k < 52 semanas); disponibilidade operacional declarada do ONS como capacidade
  (`disponibilidade_usina_ho`: métricas iguais — o sub-despacho residual é restrição de combustível, invisível nela);
  preço-base por patamar DU/FDS (métricas iguais); comprometimento pela média ou P75 do CMO (a mediana é a estatística
  certa); R mínimo abaixo de 14,5 GW; teto fixo de 38–40 GW; teto por modulação semanal `24,3 + 0,54·R_médio` (aproxima a
  dispersão intradiária do PLD mas nas horas erradas: MAE intradiário 20,8 → 22,8, térmica 306 → 365, spikes precisão 0). **Pilha só com capacidade flexível**
  (`pld_offset_mw: 0`; o legado somava 3.500 MW, que compensava a nuclear na base da pilha).
- `data.py` (dicionários manuais) → `premissas.py` (dados) + `projecoes.yaml`; feriados calculados em vez de tabela 2023-25.

- **Pilha térmica** montada dos dados ONS (`cvu_usitermica_se` + despacho térmico) em vez das planilhas manuais
  do módulo CVU térmicas (equivalência de nomes, indisponibilidade, exceções); ficam de fora ~0,8 GW sem CVU
  (Norte Fluminense, despacho contratual). Um xlsx em `config.modelo.pilha_termica_xlsx` ainda pode substituir.

## Pendências

- Fontes das projeções 2026-28 em `projecoes.yaml` (herdadas sem documentação).
- 5 UHEs pequenas sem classificação R/FD no cadastro (~50 MW): Alto Jatapu, Conj. Barreiras, Eng. Dreher,
  Eng. Kotzian, Juruena.
- Premissa de preço-base / térmica flexível 2026-28 em `projecoes.yaml` (hoje: placeholder = térmica observada de 2025).
- Calibrar `limite_hidro_reservatorio` (teto efetivo da hidro) pelo regime de degrau observado (~38–40 GW?).
- **Sub-despacho térmico de ~200 MW (~20 %)**: usinas disponíveis (dataset `disponibilidade_usina_ho`) e no dinheiro que o ONS
  não despacha — Santa Cruz e Baixada Fluminense (gás Petrobras, SE), Maranhão III e Parnaíba V (gás Parnaíba), Itaqui e
  Pampa Sul (carvão): restrição de suprimento de combustível, invisível nos dados públicos. Só entra como premissa por usina.
- Regime de degrau em 3,7 % das horas vs 6 % observado: parte dos spikes ocorre com R ≈ 34 GW, por rampa/unit
  commitment do DESSEM, abaixo de qualquer teto de energia — não modelado.
