#!/usr/bin/env python
# coding: utf-8

# In[23]:


import pandas as pd
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# Helper – recorta intervalo e garante Hora como int
# ------------------------------------------------------------------
def _slice(df, start, end):
    mask = (
        (df["Data"] >= pd.to_datetime(start)) &
        (df["Data"] <= pd.to_datetime(end))
    )
    return df.loc[mask].assign(Hora=lambda d: d["Hora"].astype(int))

# ------------------------------------------------------------------
# 1.  Preço horário por submercado
# ------------------------------------------------------------------
def plot_price(df_pld, target_sub, start, end):
    d = _slice(df_pld, start, end)
    d = d[d["Submercado"] == target_sub]

    x = pd.to_datetime(d["Data"]) + pd.to_timedelta(d["Hora"], unit="h")

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(x, d["Preço"], lw=0.8)
    ax.set_title(f"{target_sub}: preço horário ({start} → {end})")
    ax.set_ylabel("R$/MWh")
    ax.grid(True, ls="--", lw=0.3)
    return fig

# ------------------------------------------------------------------
# 2.  Spread horário vs. SUDESTE
# ------------------------------------------------------------------
def plot_spread(df_pld, target_sub, start, end, ma_hours=None):
    d = _slice(df_pld, start, end)
    wide = (
        d.pivot_table(index=["Data", "Hora"], columns="Submercado", values="Preço")
          .dropna(subset=[target_sub, "SUDESTE"])
    )
    wide["Spread"] = wide[target_sub] - wide["SUDESTE"]

    x = (pd.to_datetime(wide.index.get_level_values(0)) +
         pd.to_timedelta(wide.index.get_level_values(1), unit="h"))

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(x, wide["Spread"], lw=0.8, label="Spread horário")

    if ma_hours:
        ax.plot(x,
                wide["Spread"].rolling(ma_hours, min_periods=1).mean(),
                lw=2, ls="--", label=f"Média móvel {ma_hours} h")

    ax.set_title(f"Spread {target_sub} – SUDESTE ({start} → {end})")
    ax.set_ylabel("R$/MWh")
    ax.legend(); ax.grid(True, ls="--", lw=0.3)
    return fig

# ------------------------------------------------------------------
# Helper: traça médias trimestrais
# ------------------------------------------------------------------
def _draw_quarter_lines(ax, series, start_dt, end_dt, label_base):
    q_means = series.groupby(series.index.to_period("Q")).mean()
    first = True
    for q, mean in q_means.items():
        seg_start = max(q.start_time, start_dt)
        seg_end   = min(q.end_time,   end_dt)
        if seg_start > seg_end:
            continue
        ax.hlines(mean, seg_start, seg_end, color="red", ls=":", lw=1.4,
                  label=f"{label_base}" if first else None)
        first = False

# ------------------------------------------------------------------
# 3.  Preço médio diário
# ------------------------------------------------------------------
def plot_price_daily(df_pld, target_sub, start, end, ma_days=None):
    start_dt, end_dt = pd.to_datetime(start), pd.to_datetime(end)
    d = _slice(df_pld, start_dt, end_dt)
    d = d[d["Submercado"] == target_sub]

    daily = d.groupby("Data", as_index=False)["Preço"].mean().set_index("Data")
    daily.index = pd.to_datetime(daily.index)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(daily.index, daily["Preço"], lw=1, label="Preço diário")

    if ma_days:
        ax.plot(daily.index,
                daily["Preço"].rolling(ma_days, min_periods=1).mean(),
                lw=2, ls="--", label=f"Média móvel {ma_days} d")

    _draw_quarter_lines(ax, daily["Preço"], start_dt, end_dt, "Média trim.")
    ax.set_title(f"{target_sub}: preço médio diário ({start} → {end})")
    ax.set_ylabel("R$/MWh")
    ax.legend(); ax.grid(True, ls="--", lw=0.3)
    return fig

# ------------------------------------------------------------------
# 4.  Spread diário vs. SUDESTE
# ------------------------------------------------------------------
def plot_spread_daily(df_pld, target_sub, start, end, ma_days=None):
    start_dt, end_dt = pd.to_datetime(start), pd.to_datetime(end)
    d = _slice(df_pld, start_dt, end_dt)

    daily_means = (
        d.groupby(["Data", "Submercado"])["Preço"].mean().unstack()
          .dropna(subset=[target_sub, "SUDESTE"])
    )
    daily_means["Spread"] = daily_means[target_sub] - daily_means["SUDESTE"]
    daily_means.index = pd.to_datetime(daily_means.index)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(daily_means.index, daily_means["Spread"], lw=1, label="Spread diário")

    if ma_days:
        ax.plot(daily_means.index,
                daily_means["Spread"].rolling(ma_days, min_periods=1).mean(),
                lw=2, ls="--", label=f"Média móvel {ma_days} d")

    _draw_quarter_lines(ax, daily_means["Spread"], start_dt, end_dt, "Média trim.")
    ax.set_title(f"Spread {target_sub} – SUDESTE (média diária {start} → {end})")
    ax.set_ylabel("R$/MWh")
    ax.legend(); ax.grid(True, ls="--", lw=0.3)
    return fig


def plot_spread_armazenamento_diario(
    df_pld, 
    target_sub, 
    start, 
    end, 
    storage_hours_high=(18, 21), 
    storage_hours_low=(9, 12), 
    spread_ma_days=30
):
    """
    Plota apenas o spread de armazenamento diário (apenas valores positivos, negativos são considerados zero),
    sua média móvel e as médias trimestrais do spread.
    O spread de armazenamento é a diferença entre a média do preço nas horas
    storage_hours_high e a média do preço nas horas storage_hours_low.
    """
    # Filtrar apenas o submercado alvo ANTES de calcular o spread e a média móvel
    d_sub = df_pld[df_pld["Submercado"] == target_sub].copy()

    # Calcular spread de armazenamento diário em TODO o período disponível para o submercado
    d_high = d_sub[(d_sub["Hora"] >= storage_hours_high[0]) & (d_sub["Hora"] <= storage_hours_high[1])]
    d_low = d_sub[(d_sub["Hora"] >= storage_hours_low[0]) & (d_sub["Hora"] <= storage_hours_low[1])]

    mean_high = d_high.groupby("Data")["Preço"].mean()
    mean_low = d_low.groupby("Data")["Preço"].mean()
    storage_spread = mean_high - mean_low
    storage_spread = storage_spread.clip(lower=0)  # Só pode ser positivo, negativo vira zero
    storage_spread.name = "Spread Armazenamento"

    # Calcular média móvel do spread ANTES de filtrar o intervalo de datas
    storage_spread_ma = storage_spread.rolling(spread_ma_days, min_periods=1).mean()

    # Filtrar o spread e sua média móvel para o período de interesse
    mask_spread = (storage_spread.index >= pd.to_datetime(start)) & (storage_spread.index <= pd.to_datetime(end))
    storage_spread_plot = storage_spread.loc[mask_spread]
    storage_spread_ma_plot = storage_spread_ma.loc[mask_spread]

    # Plotar apenas o spread e sua média móvel
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(storage_spread_plot.index, storage_spread_plot, color="tab:orange", lw=1.2, label="Spread armazenamento diário")
    ax.plot(storage_spread_ma_plot.index, storage_spread_ma_plot, color="tab:red", lw=2, ls="--", label=f"Média móvel {spread_ma_days}d do spread")

    # Calcular e plotar médias trimestrais do spread de armazenamento
    # Agrupar por trimestre e calcular a média
    q_means = storage_spread_plot.groupby(storage_spread_plot.index.to_period("Q")).mean()
    for q, mean in q_means.items():
        seg_start = max(q.start_time, storage_spread_plot.index.min())
        seg_end = min(q.end_time, storage_spread_plot.index.max())
        if seg_start > seg_end:
            continue
        ax.hlines(mean, seg_start, seg_end, color="blue", ls=":", lw=1.4, label="Média trimestral" if q == q_means.index[0] else None)

    ax.set_title(f"{target_sub}: spread armazenamento ({start} → {end})")
    ax.set_ylabel("R$/MWh")
    ax.grid(True, ls="--", lw=0.3)

    # Legenda
    ax.legend(loc="upper left")

    return fig# In[ ]:





# %%
