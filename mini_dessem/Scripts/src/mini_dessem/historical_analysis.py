"""
Análise exploratória de dados históricos a partir de Data/raw_data.

Gera estatísticas e gráficos para as variáveis de interesse e salva em
output/analise_historica/{carga,eolica,solar}.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from .config import BASE_DIR, OUTPUT_DIR


RAW_DIR = BASE_DIR / 'Data' / 'raw_data'


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def _load_all_raw_data() -> pd.DataFrame:
    """Lê todos os arquivos BALANCO_ENERGIA_SUBSISTEMA_*.xlsx (SIN)."""
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {RAW_DIR}")

    arquivos = sorted(RAW_DIR.glob('BALANCO_ENERGIA_SUBSISTEMA_*.xlsx'))
    if len(arquivos) == 0:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {RAW_DIR}")

    frames: List[pd.DataFrame] = []
    for fp in arquivos:
        try:
            df = pd.read_excel(fp, sheet_name=0)
            # Filtrar explicitamente SIN, reconhecendo variações de coluna
            id_col = None
            for cand in ['id_subsistema', 'id_subsistena', 'nom_subsistema']:
                if cand in df.columns:
                    id_col = cand
                    break
            if id_col is not None:
                df[id_col] = df[id_col].astype(str).str.upper().str.strip()
                df = df[df[id_col] == 'SIN'].copy()
            if 'din_instante' not in df.columns:
                continue
            df['din_instante'] = pd.to_datetime(df['din_instante'], errors='coerce')
            df = df.dropna(subset=['din_instante'])
            df['ano'] = df['din_instante'].dt.year
            df['mes'] = df['din_instante'].dt.month
            df['hora'] = df['din_instante'].dt.hour
            df['weekday'] = df['din_instante'].dt.weekday
            df['tipo_dia'] = np.where(df['weekday'] < 5, 'util', 'fds')

            cols_num = [
                'val_gereolica', 'val_gersolar', 'val_carga',
                'val_gertermica', 'val_gerhidraulica'
            ]
            df = _coerce_numeric(df, cols_num)
            frames.append(df)
        except Exception:
            continue

    if len(frames) == 0:
        raise RuntimeError("Falha ao carregar dados: nenhum DataFrame válido.")

    df_all = pd.concat(frames, ignore_index=True)
    df_all = df_all.sort_values('din_instante').reset_index(drop=True)
    return df_all


def _save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding='utf-8')


def _plot_save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def _acf(series: pd.Series, nlags: int = 48) -> pd.Series:
    """Autocorrelação simples (normalizada), ignorando NaNs."""
    x = pd.to_numeric(series, errors='coerce').dropna().values.astype(float)
    if len(x) == 0:
        return pd.Series([], dtype=float)
    x = x - x.mean()
    denom = np.dot(x, x)
    if denom == 0:
        return pd.Series([0.0] * (nlags + 1))
    acf_vals = []
    for lag in range(nlags + 1):
        if lag == 0:
            acf_vals.append(1.0)
        else:
            v = np.dot(x[:-lag], x[lag:]) / denom
            acf_vals.append(float(v))
    return pd.Series(acf_vals, index=range(nlags + 1))


def _monthly_summary(df: pd.DataFrame, col: str) -> pd.DataFrame:
    def p(q):
        return lambda x: np.nanpercentile(x, q)

    gb = df.groupby(['ano', 'mes'])[col]
    agg = gb.agg([
        ('mean', 'mean'), ('median', 'median'), ('std', 'std'),
        ('min', 'min'), ('p05', p(5)), ('p25', p(25)), ('p75', p(75)), ('p95', p(95)), ('max', 'max')
    ])
    agg = agg.reset_index()
    return agg


def _hour_month_heatmap(df: pd.DataFrame, col: str, title: str) -> plt.Figure:
    pivot = df.pivot_table(index='mes', columns='hora', values=col, aggfunc='mean')
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(pivot, cmap='viridis', ax=ax)
    ax.set_title(title)
    ax.set_xlabel('Hora')
    ax.set_ylabel('Mês')
    return fig


def _year_month_heatmap(df: pd.DataFrame, col: str, title: str) -> plt.Figure:
    """Heatmap com eixo Y=ano e X=mês (médias mensais)."""
    pivot = df.pivot_table(index='ano', columns='mes', values=col, aggfunc='mean')
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot, cmap='viridis', ax=ax)
    ax.set_title(title)
    ax.set_xlabel('Mês')
    ax.set_ylabel('Ano')
    return fig


def _hourly_profile(df: pd.DataFrame, col: str, titulo: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 6))
    prof = df.groupby(['tipo_dia', 'hora'])[col].mean().reset_index()
    for tipo in ['util', 'fds']:
        d = prof[prof['tipo_dia'] == tipo]
        ax.plot(d['hora'], d[col], marker='o', label=tipo)
    ax.set_title(titulo)
    ax.set_xlabel('Hora')
    ax.set_ylabel(col)
    ax.legend()
    ax.grid(alpha=0.3)
    return fig


def _distribution_plot(df: pd.DataFrame, col: str, titulo: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(df[col].dropna(), bins=60, kde=True, ax=ax)
    ax.set_title(titulo)
    ax.set_xlabel(col)
    ax.set_ylabel('Frequência')
    return fig


def _monthly_trend(df: pd.DataFrame, col: str, titulo: str) -> plt.Figure:
    s = df.set_index('din_instante')[col].resample('MS').mean()
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(s.index, s.values, linewidth=2)
    ax.set_title(titulo)
    ax.set_ylabel(f"{col} (média mensal)")
    ax.grid(alpha=0.3)
    return fig


def _acf_plot(df: pd.DataFrame, col: str, titulo: str) -> plt.Figure:
    acf_vals = _acf(df[col], nlags=48)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(acf_vals.index, acf_vals.values)
    ax.set_title(titulo)
    ax.set_xlabel('Lag (horas)')
    ax.set_ylabel('ACF')
    ax.set_xlim(0, 48)
    ax.grid(alpha=0.3)
    return fig


def _boxplot_by_month(df: pd.DataFrame, col: str, titulo: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(data=df, x='mes', y=col, ax=ax)
    ax.set_title(titulo)
    ax.set_xlabel('Mês')
    ax.set_ylabel(col)
    ax.grid(axis='y', alpha=0.3)
    return fig


def _boxplot_by_month_year(df: pd.DataFrame, col: str, titulo: str) -> plt.Figure:
    """Boxplot com separação por ano (hue)."""
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.boxplot(data=df, x='mes', y=col, hue='ano', ax=ax)
    ax.set_title(titulo)
    ax.set_xlabel('Mês')
    ax.set_ylabel(col)
    ax.grid(axis='y', alpha=0.3)
    ax.legend(title='Ano', ncol=4, fontsize=8)
    return fig


def _predictability_metrics(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Mede quão bem a média mensal prediz a série horária.

    Para cada (ano, mes), calcula:
      - mean: média horária no mês
      - std_pop: desvio padrão populacional (RMSE do preditor média)
      - cv_pop: std_pop / mean
      - mae: erro absoluto médio |x - mean|
      - smape: 2|x-mean|/(|x|+|mean|) médio (robusto a zeros)
      - p50_abs_err, p90_abs_err (e versões normalizadas por mean)
    """
    def agg_block(x: pd.Series) -> pd.Series:
        arr = pd.to_numeric(x, errors='coerce').dropna().values.astype(float)
        if arr.size == 0:
            return pd.Series({
                'count': 0, 'mean': np.nan, 'std_pop': np.nan, 'cv_pop': np.nan,
                'mae': np.nan, 'smape': np.nan,
                'p50_abs_err': np.nan, 'p90_abs_err': np.nan,
                'p50_abs_err_norm': np.nan, 'p90_abs_err_norm': np.nan
            })
        m = float(arr.mean())
        e = arr - m
        std_pop = float(np.sqrt(np.mean(e**2)))
        mae = float(np.mean(np.abs(e)))
        # sMAPE robusto a zeros
        denom = np.abs(arr) + abs(m)
        smape = float(np.mean(np.where(denom > 0, 2.0 * np.abs(e) / denom, 0.0)))
        p50 = float(np.percentile(np.abs(e), 50))
        p90 = float(np.percentile(np.abs(e), 90))
        cv = std_pop / m if m != 0 else np.nan
        return pd.Series({
            'count': arr.size,
            'mean': m,
            'std_pop': std_pop,
            'cv_pop': cv,
            'mae': mae,
            'smape': smape,
            'p50_abs_err': p50,
            'p90_abs_err': p90,
            'p50_abs_err_norm': p50 / m if m != 0 else np.nan,
            'p90_abs_err_norm': p90 / m if m != 0 else np.nan,
        })
    grp = df.groupby(['ano', 'mes'])[col].apply(agg_block)
    try:
        out = grp.unstack().reset_index()
    except Exception:
        out = grp.reset_index()
    return out


def _predictability_outputs(df: pd.DataFrame, col: str, out_dir: Path, titulo_base: str) -> None:
    """Gera CSV e heatmaps de previsibilidade (CV e sMAPE) por ano x mês."""
    metrics = _predictability_metrics(df, col)
    _save_csv(metrics, out_dir / 'predictability_metrics.csv')

    # Heatmap de CV
    try:
        piv_cv = metrics.pivot_table(index='ano', columns='mes', values='cv_pop')
        fig, ax = plt.subplots(figsize=(12, 6))
        if piv_cv.size == 0 or piv_cv.notna().sum().sum() == 0:
            ax.text(0.5, 0.5, 'Sem dados para CV', ha='center', va='center')
            ax.axis('off')
        else:
            sns.heatmap(piv_cv, cmap='mako', ax=ax)
            ax.set_xlabel('Mês')
            ax.set_ylabel('Ano')
        ax.set_title(f'{titulo_base} - Heatmap CV (std/mean) Ano x Mês')
        _plot_save(fig, out_dir / 'heatmap_cv_ano_mes.png')
    except Exception:
        pass

    # Heatmap de sMAPE
    try:
        piv_sm = metrics.pivot_table(index='ano', columns='mes', values='smape')
        fig, ax = plt.subplots(figsize=(12, 6))
        if piv_sm.size == 0 or piv_sm.notna().sum().sum() == 0:
            ax.text(0.5, 0.5, 'Sem dados para sMAPE', ha='center', va='center')
            ax.axis('off')
        else:
            sns.heatmap(piv_sm, cmap='rocket', ax=ax)
            ax.set_xlabel('Mês')
            ax.set_ylabel('Ano')
        ax.set_title(f'{titulo_base} - Heatmap sMAPE Ano x Mês')
        _plot_save(fig, out_dir / 'heatmap_smape_ano_mes.png')
    except Exception:
        pass


def _run_single_dimension(df: pd.DataFrame, col: str, out_dir: Path, titulo_base: str) -> None:
    _ensure_dir(out_dir)

    # 1) Sumário mensal
    monthly = _monthly_summary(df, col)
    _save_csv(monthly, out_dir / 'monthly_summary.csv')

    # 2) Perfis horário por tipo de dia
    fig = _hourly_profile(df, col, f'{titulo_base} - Perfil horário (util vs fds)')
    _plot_save(fig, out_dir / 'perfil_horario_util_fds.png')

    # 3) Heatmap Hora x Mês (média)
    fig = _hour_month_heatmap(df, col, f'{titulo_base} - Heatmap Hora x Mês (média)')
    _plot_save(fig, out_dir / 'heatmap_hora_mes.png')
    # 3a) Heatmap Ano x Mês (média mensal)
    fig = _year_month_heatmap(df, col, f'{titulo_base} - Heatmap Ano x Mês (média)')
    _plot_save(fig, out_dir / 'heatmap_ano_mes.png')
    # 3b) Heatmaps por ano (um arquivo por ano)
    try:
        years = sorted(df['ano'].dropna().unique())
        for y in years:
            d = df[df['ano'] == y]
            if len(d) == 0:
                continue
            pivot = d.pivot_table(index='mes', columns='hora', values=col, aggfunc='mean')
            fig_y, ax = plt.subplots(figsize=(12, 6))
            sns.heatmap(pivot, cmap='viridis', ax=ax)
            ax.set_title(f"{titulo_base} - Heatmap Hora x Mês (Ano {int(y)})")
            ax.set_xlabel('Hora')
            ax.set_ylabel('Mês')
            _plot_save(fig_y, out_dir / f'heatmap_hora_mes_ano_{int(y)}.png')
    except Exception:
        pass

    # 4) Boxplot por mês
    fig = _boxplot_by_month(df, col, f'{titulo_base} - Boxplot por mês')
    _plot_save(fig, out_dir / 'boxplot_por_mes.png')
    # 4b) Boxplot por mês com separação por ano
    try:
        fig = _boxplot_by_month_year(df, col, f'{titulo_base} - Boxplot por mês (por ano)')
        _plot_save(fig, out_dir / 'boxplot_por_mes_por_ano.png')
    except Exception:
        pass

    # 5) Distribuição (hist + kde)
    fig = _distribution_plot(df, col, f'{titulo_base} - Distribuição (hist+kde)')
    _plot_save(fig, out_dir / 'distribuicao_hist_kde.png')
    # 5b) Distribuição por ano (KDE sobreposta)
    try:
        fig_d, ax = plt.subplots(figsize=(14, 7))
        years = sorted(df['ano'].dropna().unique())
        if df[col].notna().any():
            x_min = float(np.nanpercentile(df[col], 1))
            x_max = float(np.nanpercentile(df[col], 99))
        else:
            x_min, x_max = 0.0, 1.0
        for y in years:
            s = df.loc[df['ano'] == y, col].dropna()
            if len(s) == 0:
                continue
            sns.kdeplot(s, ax=ax, label=str(int(y)), linewidth=2)
        ax.set_title(f'{titulo_base} - Distribuição por ano (KDE)')
        ax.set_xlabel(col)
        ax.set_ylabel('Densidade (KDE)')
        ax.set_xlim(x_min, x_max)
        ax.grid(alpha=0.3)
        ax.legend(title='Ano', ncol=4, fontsize=8)
        _plot_save(fig_d, out_dir / 'distribuicao_kde_por_ano.png')
    except Exception:
        pass

    # 6) Tendência mensal (média mensal)
    fig = _monthly_trend(df, col, f'{titulo_base} - Tendência mensal (média)')
    _plot_save(fig, out_dir / 'tendencia_mensal.png')

    # 7) Autocorrelação até 48 lags
    fig = _acf_plot(df, col, f'{titulo_base} - ACF (até 48 lags)')
    _plot_save(fig, out_dir / 'acf_48lags.png')

    # 7b) Previsibilidade a partir da média mensal
    _predictability_outputs(df, col, out_dir, titulo_base)

    # 8) Evolução por ano: linhas por ano (médias mensais)
    try:
        pivot_year = df.set_index('din_instante')[col].resample('MS').mean().to_frame('valor')
        pivot_year['ano'] = pivot_year.index.year
        pivot_year['mes'] = pivot_year.index.month
        fig_y, ax = plt.subplots(figsize=(14, 6))
        for ano, g in pivot_year.groupby('ano'):
            ax.plot(g['mes'], g['valor'], marker='o', label=str(int(ano)))
        ax.set_title(f'{titulo_base} - Evolução mensal por ano')
        ax.set_xlabel('Mês')
        ax.set_ylabel(f'{col} (média mensal)')
        ax.set_xticks(range(1, 13))
        ax.grid(alpha=0.3)
        ax.legend(ncol=4, fontsize=8)
        _plot_save(fig_y, out_dir / 'evolucao_mensal_por_ano.png')
    except Exception:
        pass

    # 9) Perfis horários por ano (útil e FDS separados)
    try:
        prof = df.groupby(['ano', 'tipo_dia', 'hora'])[col].mean().reset_index()
        for tipo in ['util', 'fds']:
            fig_t, ax = plt.subplots(figsize=(14, 6))
            sub = prof[prof['tipo_dia'] == tipo]
            for ano, g in sub.groupby('ano'):
                ax.plot(g['hora'], g[col], marker='o', label=str(int(ano)))
            ax.set_title(f'{titulo_base} - Perfil horário por ano ({tipo})')
            ax.set_xlabel('Hora')
            ax.set_ylabel(col)
            ax.set_xticks(range(0, 24))
            ax.grid(alpha=0.3)
            ax.legend(ncol=4, fontsize=8)
            fname = f'perfil_horario_por_ano_{tipo}.png'
            _plot_save(fig_t, out_dir / fname)
    except Exception:
        pass

    # 10) Heatmap Ano x Hora
    try:
        pivot_ah = df.pivot_table(index='ano', columns='hora', values=col, aggfunc='mean')
        fig_h, ax = plt.subplots(figsize=(14, 6))
        sns.heatmap(pivot_ah, cmap='magma', ax=ax)
        ax.set_title(f'{titulo_base} - Heatmap Ano x Hora (média)')
        ax.set_xlabel('Hora')
        ax.set_ylabel('Ano')
        _plot_save(fig_h, out_dir / 'heatmap_ano_hora.png')
    except Exception:
        pass

    # 11) Relatório de qualidade de dados (por ano/mês)
    try:
        def p(q):
            return lambda x: np.nanpercentile(x, q)

        base = df[['ano', 'mes', col]].copy()
        dq = base.groupby(['ano', 'mes'])[col].agg([
            ('count', 'count'), ('mean', 'mean'), ('median', 'median'), ('std', 'std'),
            ('min', 'min'), ('p01', p(1)), ('p99', p(99)), ('max', 'max')
        ]).reset_index()

        # Desvios robustos vs mediana global
        med_global = np.nanmedian(base[col])
        mad_global = np.nanmedian(np.abs(base[col] - med_global))
        if mad_global == 0:
            dq['robust_z'] = 0.0
        else:
            dq['robust_z'] = (dq['median'] - med_global) / (1.4826 * mad_global)

        # Flags de possíveis anomalias
        dq['flag_outlier_mediana'] = dq['robust_z'].abs() > 5
        dq['flag_amplitude_excessiva'] = (dq['p99'] - dq['p01']) > (dq['median'].abs() * 1.5 + 1)

        _save_csv(dq, out_dir / 'data_quality_report.csv')
    except Exception:
        pass


def gerar_analise_historica(output_base: Path | None = None) -> Dict[str, Path]:
    """Executa análises para carga, eólica e solar e salva saídas.

    Retorna dicionário com os diretórios de saída por dimensão.
    """
    df_all = _load_all_raw_data()

    out_root = Path(output_base) if output_base is not None else OUTPUT_DIR / 'analise_historica'
    _ensure_dir(out_root)

    out_dirs = {
        'carga': out_root / 'carga',
        'eolica': out_root / 'eolica',
        'solar': out_root / 'solar',
    }
    for p in out_dirs.values():
        _ensure_dir(p)

    # Subconjuntos limpos
    base_cols = ['din_instante', 'ano', 'mes', 'hora', 'tipo_dia']

    # Carga
    if 'val_carga' in df_all.columns:
        df_carga = df_all[base_cols + ['val_carga']].dropna(subset=['val_carga'])
        _run_single_dimension(df_carga, 'val_carga', out_dirs['carga'], 'Carga (SIN)')

    # Eólica
    if 'val_gereolica' in df_all.columns:
        df_eolica = df_all[base_cols + ['val_gereolica']].dropna(subset=['val_gereolica'])
        _run_single_dimension(df_eolica, 'val_gereolica', out_dirs['eolica'], 'Geração Eólica (SIN)')

    # Solar
    if 'val_gersolar' in df_all.columns:
        df_solar = df_all[base_cols + ['val_gersolar']].dropna(subset=['val_gersolar'])
        _run_single_dimension(df_solar, 'val_gersolar', out_dirs['solar'], 'Geração Solar (SIN)')

    # Salvar amostra de dados consolidados para referência
    sample_path = out_root / 'amostra_dados_consolidados.csv'
    _save_csv(df_all.head(1000), sample_path)

    return out_dirs


