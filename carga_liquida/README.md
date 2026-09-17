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
│   │   ├── samplers/           carga v6 (temperatura), eólica AR(1), solar cent/dist, térmica flex (perfil) — treino + amostragem
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
python run.py treinar                # samplers eolica solar carga + hidro_fd + pilhas térmicas -> Output/modelo/ (~40 s)
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
| `coff_eolica`, `coff_fotovoltaica` | ONS `restricao_coff_*_tm` (mensal) | `baterias/Data/coff_*` (reaproveitado) | curtailment e potencial renovável |
| `temperatura` | Meteostat bulk (NOAA ISD/SYNOP), 15 aeroportos | `Data/raw/temperatura/` | perfil horário da carga (sampler v6) |
| `cvu` | ONS `cvu_usitermica_se` (anual) | `Data/raw/CVU/` | CVU semanal por usina → pilha térmica |
| `disponibilidade` | ONS `disponibilidade_usina_ho` (mensal; 2022 só csv) | `Data/raw/disponibilidade/` | disponibilidade operacional declarada por usina → capacidade na pilha |

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
| Hidro FD | `FD = c + ghr[hora]·R − 8·(R/GW)² + 0,09·ENA + mês + hora + FDS` — a resposta ao R varia com a hora (0,91 ao meio-dia, 0,76 às 19h) e satura (marginal ≈ 0,45 em R = 20 GW, 0,2 em 35 GW); legado: ghr único 0,33 | histórico FD/R + ENA diária; MAE 1,77 GW, R² 0,91 |
| Valor da água (`termica_flexivel: valor_agua`, padrão) | **premissa = preço-base por semana × patamar (DU/FDS) × subsistema** (papel do DECOMP): histórico = mediana do CMO nas horas DU e FDS de cada semana (`valor_agua_fonte: cmo`) ou CVU da pilha na térmica de mérito observada (`pilha`); projeção em `projecoes.yaml` (número, por subsistema e/ou por patamar; ou derivado da térmica base pela pilha). Base **comprometida** do dia = usinas com CVU ≤ VA do seu subsistema, ligadas o dia inteiro (no fim de semana o preço cai e usinas próximas da margem desligam: utilização 0,66 DU vs 0,50 FDS, liga/desliga e não carga parcial) | CMO / térmica observada |
| Despacho (`despachar_va`, papel do DESSEM) | hidro R fecha o balanço entre 14,5 GW e o **teto da semana**; R no teto → térmica extra por mérito; R no mínimo → base reduzida da mais cara para a mais barata, depois curtailment (eólica + solar cent. pro rata, por fim MMGD). **PLD horário = recurso marginal**: VA · CVU da extra · CVU da última reduzida · piso | — |
| Teto da hidro | fixo em 42 GW (legado). Opção `limite_modulacao` (`R_max_semana = 24,3 + 0,54·R_médio`, ≤ 42; a disponibilidade das UHEs R ~51 GW nunca limita e o pico segue a energia hídrica alocada, R² 0,5) **desativada**: aproxima a dispersão intradiária do PLD (20 → 26, obs. 29) mas nas horas erradas — teste pareado por dia: MAE intradiário do PLD 20,8 → 22,8, térmica 306 → 365, precisão dos spikes 0 | — |
| Alternativas | `exogena`: térmica base mensal como premissa (MW), perfil horário observado ou flat; `residual`: legado (térmica só na saturação) | — |
| Pilha térmica | **semanal**: CVU da semana operativa × **disponibilidade operacional declarada** (última declaração da usina, dataset `disponibilidade`, por CEG) − inflexibilidade média, + subsistema; nuclear fora por definição (CEG `UTN`); ~15 GW flexíveis | datasets `cvu` + `disponibilidade` + `termica_despacho` |

Premissas mensais (`modelo/premissas.py`): nos anos observados tudo vem dos dados — carga (+ exportação),
eólica potencial, solar cent/dist, ENA armazenável SIN, térmica total (o `data.py` do legado era uma cópia
manual do BALANCO_ENERGIA). Para 2026-28, `config/projecoes.yaml`.

### Validação (2022-01 → 2025-12, 6 cenários; média dos cenários vs observado, hora a hora)

| componente | obs (MW) | sim (MW) | viés | MAE | MAE/média | R² |
|---|---|---|---|---|---|---|
| carga | 75.598 | 75.598 | +1 | 2.832 | 3,7 % | 0,87 |
| eólica pós-corte | 11.388 | 11.905 | +517 | 2.333 | 20,5 % | 0,61 |
| solar pós-corte | 6.198 | 6.260 | +62 | 702 | 11,3 % | 0,98 |
| hidro FD | 23.627 | 23.749 | +122 | 1.777 | 7,5 % | 0,90 |
| hidro R | 25.131 | 25.477 | +346 | 2.707 | 10,8 % | 0,74 |
| térmica flexível | 1.043 | 874 | −169 | 640 | 61 % | 0,46 (mensal ~0,8) |
| **carga líquida** | **26.176** | **25.660** | **−516** | **2.825** | **10,8 %** | **0,73** |
| PLD vs CMO SE (R$/MWh) | 91 | 116 | +25 | 51 | — | **0,70** |

Regimes simulados: hidro marginal 90 %, curtailment 7,5 %, base reduzida 1,6 %, extra 0,5 % (observado: ±50 % do patamar semanal em 78 % das horas; abaixo 16 %, concentradas 8–14h com R ≈ 15,6 GW; acima 6 %, 16–22h com R p90 38,5 GW). **Componente intradiária** (`validacao/metricas_intradiarias.csv`, desvios da média diária): PLD corr 0,49 / R² 0,20 / MAE 21; hidro R corr 0,93 / R² 0,82; térmica R² < 0 (a forma horária da térmica simulada é pior que flat); spikes horários (CMO > 1,5× mediana semanal, 2,9 % das horas): precisão e recall 0 — o modelo não acerta *quando* o degrau ocorre. Qualquer mudança de estrutura horária deve ser julgada por estas métricas em teste pareado por dia, não pelo desvio-padrão.

Comparação dos modos (mesma simulação 2022-25): `valor_agua` com `fonte: pilha` (sem usar o CMO) → PLD R² 0,51, térmica R² 0,76; `exogena` → térmica R² 0,82, carga líquida viés −317, PLD R² 0,51; `residual` (legado) → térmica ≈ 0, carga líquida viés −716, PLD R² ≈ 0. O ganho de R² 0,70 vem do nível do patamar ser premissa; o modelo entrega a modulação.

Por que a base é comprometida o dia inteiro: o "unit commitment" do ONS (27 % da térmica flexível) tem pico às 8–13h e mínimo às 18–20h, com correlação intradiária **negativa** com a carga líquida — são as mesmas unidades da ordem de mérito, rotuladas como UC no vale solar (o preço não as chamaria) e como mérito à noite; a soma é quase flat no dia (CV 0,16). Por que o VA é por subsistema: em mar/2025 o CMO SE/S foi ~350 e N/NE ~10; 1,3 GW de térmicas do N/NE com CVU 111–295 não rodaram. Pilha semanal + VA por subsistema + base comprometida levaram a térmica de R² 0,30 para 0,49 (mensal 0,68 → 0,81) sem nenhum fator de ajuste. `min_hidro_reservatorio` 14,5 GW do legado se sustenta (12 ou 10,5 GW pioram R, carga líquida e curtailment).

Por que a térmica flexível é premissa e não decisão do modelo: o despacho herdado só chamava térmica quando a
hidro batia no limite (térmica ≈ 0 em 99,7 % das horas vs 48 % observado), e nenhuma variável disponível a
prevê — o valor da água implícito (CVU marginal despachado) correlaciona só 0,5 com o CMO, e `flex ~ EAR + ENA + mês`
dá R² 0,5 (mudança de regime em 2025-26). Já `CMO ~ térmica_flex` dá R² 0,82 mensal. Ver `Output/modelo/valor_agua_implicito.parquet`.

Limitações restantes: o curtailment simulado (~0,8 GW) é só o energético — o de rede (CNF/REL, a maior parte
hoje) não é modelado, e a eólica pós-corte fica +0,5 GW acima da observada; o PLD tem piso 61 (CMO observado chega a 0)
e subestima picos (out/2024: 360 vs 516).

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
  `baterias/` (37,2 TWh em 2025).
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
- **Despacho por valor da água** (`termica_flexivel: valor_agua`, estrutura DECOMP → DESSEM) com preço horário pelo recurso
  marginal, patamar DU/FDS, VA por subsistema, base comprometida por dia e disponibilidade declarada; `exogena` (térmica base mensal) e `residual` (legado) continuam como opções. Testado e descartado:
  fator de despacho, proxy de disponibilidade por geração recente, comprometimento pela média ou P75 do CMO (a mediana é
  a estatística certa), R mínimo abaixo de 14,5 GW, teto fixo de 38–40 GW e teto por modulação semanal (reprovado no teste intradiário). **Pilha só com capacidade flexível**
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
- **Sub-despacho térmico de ~170 MW (16 %)**: usinas disponíveis e no dinheiro que o ONS não despacha — Santa Cruz e Baixada
  Fluminense (gás Petrobras, SE), Maranhão III e Parnaíba V (gás Parnaíba), Itaqui e Pampa Sul (carvão): restrição de
  suprimento de combustível, invisível nos datasets de CVU e disponibilidade. Só entra como premissa por usina (MW máx.).
- Regime de degrau em 3,7 % das horas vs 6 % observado: parte dos spikes ocorre com R ≈ 34 GW, por rampa/unit
  commitment do DESSEM, abaixo de qualquer teto de energia — não modelado.
