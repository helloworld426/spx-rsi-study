"""Render a self-contained static HTML dashboard from a BacktestResult.

The output mirrors the dailychartbook study layout (header chips, summary cards,
signal map, forward-return & hit-rate bars, signal-performance paths, return
distribution, study-summary table, and the full results table). Plotly.js is
inlined so the file works fully offline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

from backtest import BacktestResult

# ---- palette (dailychartbook-ish) ----
GREEN = "#1a7f6a"
GREEN_SOFT = "#d8efe8"
GREEN_LINE = "#1a7f6a"
RED = "#c2554f"
RED_SOFT = "#f6dede"
INK = "#1d2b27"
MUTED = "#8a9a95"
BORDER = "#e7eae8"
PAGE_BG = "#f4f6f5"

# Cards on the source page skip 2M; charts/tables keep all horizons.
CARD_HORIZONS = ["1W", "2W", "1M", "3M", "6M", "9M", "12M"]

PLOT_FONT = dict(family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
                 color=INK, size=13)


def _pct(x: float, dp: int = 1, signed: bool = True) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    s = f"{x * 100:+.{dp}f}%" if signed else f"{x * 100:.{dp}f}%"
    return s


def _hit(x: float) -> str:
    """Hit rate as a whole percent, rounded half-up (matches the source site:
    62.5% -> 63%, not Python's banker's-rounding 62%)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{int(np.floor(x * 100 + 0.5))}%"


def _fig_html(fig: go.Figure, div_id: str) -> str:
    return fig.to_html(
        include_plotlyjs=False,
        full_html=False,
        div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
    )


def _base_layout(height: int) -> dict:
    return dict(
        font=PLOT_FONT,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=55, r=20, t=20, b=40),
        height=height,
        hovermode="closest",
        showlegend=False,
    )


# ---------------------------------------------------------------- figures ----
def signal_map_fig(res: BacktestResult) -> go.Figure:
    ds = res.dataset
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ds.index, y=ds["Close"], mode="lines", name="SPX",
        line=dict(color=INK, width=1.1), hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>",
    ))
    sig = res.signals
    fig.add_trace(go.Scatter(
        x=sig.index, y=sig["spx_price"], mode="markers", name="Signal",
        marker=dict(color="#e23b3b", size=9, line=dict(color="white", width=1)),
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}<extra>Signal</extra>",
    ))
    lay = _base_layout(440)
    lay.update(
        yaxis=dict(type="log", title="SPX", gridcolor="#f0f2f1", zeroline=False),
        xaxis=dict(title="Date", gridcolor="#f0f2f1",
                   range=[ds.index[0], ds.index[-1]]),
        showlegend=True,
        legend=dict(x=0.01, y=0.98, bgcolor="rgba(255,255,255,0.6)", bordercolor=BORDER, borderwidth=1),
    )
    fig.update_layout(lay)
    return fig


def forward_returns_fig(res: BacktestResult) -> go.Figure:
    H = list(res.horizons)
    sig_avg = [res.signal_stats[h]["avg"] * 100 for h in H]
    sig_med = [res.signal_stats[h]["median"] * 100 for h in H]
    base_avg = [res.baseline_stats[h]["avg"] * 100 for h in H]
    base_med = [res.baseline_stats[h]["median"] * 100 for h in H]

    fig = go.Figure()
    # Avg view (visible)
    fig.add_trace(go.Bar(x=H, y=sig_avg, marker_color=GREEN, name="Signal avg.",
                         hovertemplate="%{x}: %{y:.1f}%<extra>Signal</extra>"))
    fig.add_trace(go.Scatter(x=H, y=base_avg, mode="lines+markers", name="All-day avg.",
                             line=dict(color=INK, width=1.5), marker=dict(size=5),
                             hovertemplate="%{x}: %{y:.1f}%<extra>All-day</extra>"))
    # Median view (hidden)
    fig.add_trace(go.Bar(x=H, y=sig_med, marker_color=GREEN, name="Signal med.",
                         visible=False, hovertemplate="%{x}: %{y:.1f}%<extra>Signal</extra>"))
    fig.add_trace(go.Scatter(x=H, y=base_med, mode="lines+markers", name="All-day med.",
                             visible=False, line=dict(color=INK, width=1.5), marker=dict(size=5),
                             hovertemplate="%{x}: %{y:.1f}%<extra>All-day</extra>"))
    lay = _base_layout(300)
    lay.update(
        yaxis=dict(title="Return", ticksuffix="%", gridcolor="#f0f2f1", zeroline=True,
                   zerolinecolor="#dfe3e1"),
        xaxis=dict(gridcolor="#f0f2f1"),
        updatemenus=[_avg_med_buttons([[True, True, False, False], [False, False, True, True]])],
    )
    fig.update_layout(lay)
    return fig


def hit_rates_fig(res: BacktestResult) -> go.Figure:
    H = list(res.horizons)
    sig_hit = [res.signal_stats[h]["hit"] * 100 for h in H]
    base_hit = [res.baseline_stats[h]["hit"] * 100 for h in H]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=H, y=sig_hit, marker_color=GREEN, name="Signal hit rate",
                         hovertemplate="%{x}: %{y:.0f}%<extra>Signal</extra>"))
    fig.add_trace(go.Scatter(x=H, y=base_hit, mode="lines+markers", name="All-day hit rate",
                             line=dict(color=INK, width=1.5), marker=dict(size=5),
                             hovertemplate="%{x}: %{y:.0f}%<extra>All-day</extra>"))
    lay = _base_layout(300)
    lay.update(
        yaxis=dict(title="Hit rate", ticksuffix="%", range=[0, 100], gridcolor="#f0f2f1"),
        xaxis=dict(gridcolor="#f0f2f1"),
    )
    fig.update_layout(lay)
    return fig


def _avg_med_buttons(vis_pairs):
    return dict(
        type="buttons", direction="right", x=1.0, xanchor="right", y=1.18, yanchor="top",
        showactive=True, bgcolor="white", bordercolor=BORDER, font=dict(size=12),
        buttons=[
            dict(label="Avg", method="update", args=[{"visible": vis_pairs[0]}]),
            dict(label="Median", method="update", args=[{"visible": vis_pairs[1]}]),
        ],
    )


def signal_performance_fig(res: BacktestResult) -> go.Figure:
    n = res.horizons[res.cfg.maxdd_horizon]
    palette = ["#5b8ff9", "#61ddaa", "#65789b", "#f6bd16", "#7262fd", "#78d3f8",
               "#9661bc", "#f6903d", "#008685", "#f08bb4"]
    fig = go.Figure()
    paths = res.forward_paths
    # individual faint paths
    mat = np.full((len(paths), n + 1), np.nan)
    for k, (dt, p) in enumerate(paths.items()):
        L = min(len(p), n + 1)
        mat[k, :L] = p[:L] * 100
        fig.add_trace(go.Scatter(
            x=list(range(L)), y=p[:L] * 100, mode="lines",
            line=dict(color=palette[k % len(palette)], width=0.8), opacity=0.45,
            name=str(dt.date()), hoverinfo="skip", showlegend=False,
        ))
    median_path = np.nanmedian(mat, axis=0)
    avg_path = np.nanmean(mat, axis=0)
    # bold median (visible) + avg (hidden)
    fig.add_trace(go.Scatter(x=list(range(n + 1)), y=median_path, mode="lines",
                             line=dict(color=INK, width=3), name="Median signal",
                             hovertemplate="day %{x}: %{y:.1f}%<extra>Median</extra>"))
    fig.add_trace(go.Scatter(x=list(range(n + 1)), y=avg_path, mode="lines", visible=False,
                             line=dict(color=INK, width=3), name="Average signal",
                             hovertemplate="day %{x}: %{y:.1f}%<extra>Average</extra>"))

    n_paths = len(paths)
    # toggle: median bold vs avg bold (the two last traces)
    vis_med = [True] * n_paths + [True, False]
    vis_avg = [True] * n_paths + [False, True]
    # month ticks
    tickvals = [0, 21, 63, 126, 189, 252]
    ticktext = ["0", "1M", "3M", "6M", "9M", "12M"]
    lay = _base_layout(430)
    lay.update(
        yaxis=dict(title="Forward return", ticksuffix="%", gridcolor="#f0f2f1",
                   zeroline=True, zerolinecolor="#dfe3e1"),
        xaxis=dict(tickvals=tickvals, ticktext=ticktext, gridcolor="#f0f2f1", range=[0, n]),
        updatemenus=[dict(
            type="buttons", direction="right", x=1.0, xanchor="right", y=1.12, yanchor="top",
            showactive=True, bgcolor="white", bordercolor=BORDER, font=dict(size=12),
            buttons=[
                dict(label="Median", method="update", args=[{"visible": vis_med}]),
                dict(label="Avg", method="update", args=[{"visible": vis_avg}]),
            ],
        )],
    )
    fig.update_layout(lay)
    return fig


def distribution_fig(res: BacktestResult) -> go.Figure:
    H = list(res.horizons)
    fig = go.Figure()
    for h in H:
        vals = res.signals[h].dropna().to_numpy() * 100
        fig.add_trace(go.Box(
            y=vals, name=h, boxpoints="all", jitter=0.5, pointpos=0,
            marker=dict(color="#e23b3b", size=5, opacity=0.7),
            line=dict(color=GREEN), fillcolor=GREEN_SOFT, whiskerwidth=0.4,
            hovertemplate=h + ": %{y:.1f}%<extra></extra>",
        ))
    lay = _base_layout(440)
    lay.update(
        yaxis=dict(title="Forward return", ticksuffix="%", gridcolor="#f0f2f1",
                   zeroline=True, zerolinecolor="#dfe3e1"),
        xaxis=dict(gridcolor="#f0f2f1"),
    )
    fig.update_layout(lay)
    return fig


# ----------------------------------------------------------------- html -----
def _chip(label: str) -> str:
    return f'<span class="chip">{label}</span>'


def _stat_card(label, value, sub, value_class="") -> str:
    return f"""<div class="card stat">
      <div class="card-label">{label}</div>
      <div class="stat-value {value_class}">{value}</div>
      <div class="card-sub">{sub}</div>
    </div>"""


def _metric_card(label, avg_txt, med_txt, sub_avg, sub_med, pos: bool) -> str:
    cls = "pos" if pos else "neg"
    return f"""<div class="card metric" data-avg="{avg_txt}" data-med="{med_txt}"
        data-sub-avg="{sub_avg}" data-sub-med="{sub_med}">
      <div class="card-label">{label}</div>
      <div class="pill {cls} metric-value">{avg_txt}</div>
      <div class="card-sub metric-sub">{sub_avg}</div>
    </div>"""


def _ai_summary(res: BacktestResult) -> str:
    cfg = res.cfg
    s = res.signal_stats
    b = res.baseline_stats
    n_total = len(res.signals)
    n_done = s["12M"]["n"]
    start = res.dataset.index[0].date()
    end = res.dataset.index[-1].date()
    one_m_sig = _pct(s["1M"]["avg"])
    one_m_base = _pct(b["1M"]["avg"])
    edge = "weaker" if s["1M"]["avg"] < b["1M"]["avg"] else "stronger"
    return (
        f"This {cfg.asset} backtest found {n_total} signals from {start} through {end}, "
        f"with {n_done} completed 12-month forward windows. The setup's 1-month average "
        f"forward return was {one_m_sig} versus {one_m_base} for all days, making the "
        f"short-term read {edge} than the all-day baseline. At 12 months, average signal "
        f"return was {_pct(s['12M']['avg'])} versus {_pct(b['12M']['avg'])} baseline, while "
        f"the median signal return was {_pct(s['12M']['median'])}. Average 12-month max "
        f"drawdown after signals was {_pct(s['_maxdd']['avg'])}, so the sample points to "
        f"meaningful path risk even when the 12-month endpoint is positive."
    )


def _summary_table(res: BacktestResult) -> str:
    H = list(res.horizons)
    s, b, z = res.signal_stats, res.baseline_stats, res.zscores
    head = "".join(f"<th>{h}</th>" for h in H)
    rows = []

    def row(label, vals, strong=False, fmt=lambda v: v):
        cls = ' class="strong"' if strong else ""
        cells = "".join(f"<td>{fmt(v)}</td>" for v in vals)
        return f"<tr{cls}><td class='rowlab'>{label}</td>{cells}</tr>"

    rows.append(row("Median Signal Return", [_pct(s[h]["median"]) for h in H], strong=True))
    rows.append(row("Median All-Dataset Return", [_pct(b[h]["median"]) for h in H]))
    rows.append(row("Average Signal Return", [_pct(s[h]["avg"]) for h in H], strong=True))
    rows.append(row("Average All-Dataset Return", [_pct(b[h]["avg"]) for h in H]))
    rows.append(row("Signal Hit Rate", [s[h]["hit"] for h in H], strong=True, fmt=_hit))
    rows.append(row("All-Dataset Hit Rate", [b[h]["hit"] for h in H], fmt=_hit))
    rows.append(row("Signal Z-Score", [z[h] for h in H], strong=True,
                    fmt=lambda v: f"{v:.2f}"))
    return f"""<table class="summary-table">
      <thead><tr><th class='rowlab'>METRIC</th>{head}</tr></thead>
      <tbody>{''.join(rows)}</tbody></table>"""


def _results_table(res: BacktestResult) -> str:
    H = list(res.horizons)
    head = "".join(f"<th>{h}</th>" for h in H) + "<th>12M MAXDD</th>"
    body = []
    for dt, r in res.signals.iterrows():
        cells = [f"<td class='rowlab'>{dt.date()}</td>",
                 f"<td>{r['spx_price']:.2f}</td>"]
        for h in H:
            v = r[h]
            if pd.isna(v):
                cells.append("<td></td>")
            else:
                cls = "cpos" if v >= 0 else "cneg"
                cells.append(f"<td class='{cls}'>{_pct(v)}</td>")
        dd = r["maxdd"]
        cells.append("<td class='cneg'>" + (_pct(dd) if not pd.isna(dd) else "") + "</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    # footer aggregates
    s, b, z = res.signal_stats, res.baseline_stats, res.zscores

    def foot(label, vals, fmt):
        return ("<tr class='foot'><td class='rowlab'>" + label + "</td>" +
                "".join(f"<td>{fmt(v)}</td>" for v in vals) + "</tr>")

    pf = lambda v: _pct(v) if not (isinstance(v, float) and np.isnan(v)) else ""
    foot_rows = [
        foot("Average Signal Return", [b_ for b_ in [s[h]["avg"] for h in H]] + [s["_maxdd"]["avg"]], pf),
        foot("Median Signal Return", [s[h]["median"] for h in H] + [s["_maxdd"]["median"]], pf),
        ("<tr class='foot'><td class='rowlab'>Signal Hit Rate</td>" +
         "".join(f"<td>{_hit(s[h]['hit'])}</td>" for h in H) + "<td></td></tr>"),
        ("<tr class='foot'><td class='rowlab'>Signal Z-Score</td>" +
         "".join(f"<td>{z[h]:.2f}</td>" for h in H) + "<td></td></tr>"),
        foot("Average All-Dataset Return", [b[h]["avg"] for h in H] + [b["_maxdd"]["avg"]], pf),
        foot("Median All-Dataset Return", [b[h]["median"] for h in H] + [b["_maxdd"]["median"]], pf),
        ("<tr class='foot'><td class='rowlab'>All-Dataset Hit Rate</td>" +
         "".join(f"<td>{_hit(b[h]['hit'])}</td>" for h in H) + "<td></td></tr>"),
    ]
    return f"""<table class="results-table">
      <thead><tr><th class='rowlab'>SIGNAL DATE</th><th>SPX PRICE</th>{head}</tr></thead>
      <tbody>{''.join(body)}{''.join(foot_rows)}</tbody></table>"""


def _section(anchor, kicker, title, body, extra_head="") -> str:
    return f"""<section id="{anchor}" class="card panel">
      <div class="panel-head">
        <div><div class="kicker">{kicker}</div><h2>{title}</h2></div>
        <div>{extra_head}</div>
      </div>
      {body}
    </section>"""


def build_html(res: BacktestResult) -> str:
    cfg = res.cfg
    s, b = res.signal_stats, res.baseline_stats
    n_total = len(res.signals)
    n_done = s["12M"]["n"]
    # Windows strftime lacks %-d, so build the date range manually.
    d0, d1 = res.dataset.index[0], res.dataset.index[-1]
    rng = f"{d0.day} {d0.strftime('%b %Y')} - {d1.day} {d1.strftime('%b %Y')}"

    # header chips
    chips = "".join(_chip(c) for c in [
        f"Asset: {cfg.asset}", f"n={n_total}", f"Trigger: {cfg.trigger_label}", rng])

    # top stat cards
    trigger_txt = (
        f"Triggers when {cfg.asset}'s {cfg.rsi_period}-day RSI crosses from above "
        f"{cfg.overbought:.0f} to below {cfg.cross_below:.0f} in {cfg.lookback} trading days "
        f"or less. Specifically: on the signal day RSI closes &lt; {cfg.cross_below:.0f} "
        f"(having closed &gt;= {cfg.cross_below:.0f} the prior day), AND RSI was &gt; "
        f"{cfg.overbought:.0f} on at least one of the prior {cfg.lookback} trading days.")
    top_cards = (
        '<div class="stack">'
        + _stat_card("Signal count", f"{n_total}", f"{n_done} completed 12M windows")
        + _stat_card("Avg. max drawdown", _pct(s["_maxdd"]["avg"]),
                     f"n={s['_maxdd']['n']}; all-day avg. {_pct(b['_maxdd']['avg'])}",
                     value_class="pill neg")
        + "</div>"
        + f"""<div class="card stat"><div class="card-label">Trigger criteria</div>
              <div class="card-text">{trigger_txt}</div></div>"""
        + f"""<div class="card stat"><div class="card-label">AI Summary</div>
              <div class="card-text">{_ai_summary(res)}</div></div>"""
    )

    # forward-return metric cards
    fr_cards = "".join(
        _metric_card(
            f"{h} avg. return", _pct(s[h]["avg"]), _pct(s[h]["median"]),
            f"n={s[h]['n']}; all-day avg. {_pct(b[h]['avg'])}",
            f"n={s[h]['n']}; all-day med. {_pct(b[h]['median'])}",
            pos=s[h]["avg"] >= 0)
        for h in CARD_HORIZONS)
    hit_cards = "".join(
        _stat_card(f"{h} hit rate", _hit(s[h]["hit"]),
                   f"n={s[h]['n']}; all-day hit {_hit(b[h]['hit'])}")
        for h in CARD_HORIZONS)

    # summary highlight cards
    z = res.zscores
    best_z_h = max(res.horizons, key=lambda h: abs(z[h]))
    best_edge_h = max(res.horizons, key=lambda h: s[h]["median"] - b[h]["median"])
    peak_hit_h = max(res.horizons, key=lambda h: s[h]["hit"])
    hi_cards = "".join([
        _hi_card("Completed windows", f"{n_done} of {n_total}", "12-month forward sample"),
        _hi_card("Strongest Z-score", f"{best_z_h} {z[best_z_h]:.2f}", "|Z| >= 2 is emphasized"),
        _hi_card("Best median edge", f"{best_edge_h} {_pct(s[best_edge_h]['median']-b[best_edge_h]['median'])}",
                 "signal median minus all-day median"),
        _hi_card("Peak signal hit", f"{peak_hit_h} {s[peak_hit_h]['hit']*100:.0f}%",
                 f"all-day hit {b[peak_hit_h]['hit']*100:.0f}%"),
    ])

    # figures
    sigmap = _fig_html(signal_map_fig(res), "fig-signalmap")
    frfig = _fig_html(forward_returns_fig(res), "fig-forward")
    hitfig = _fig_html(hit_rates_fig(res), "fig-hit")
    perffig = _fig_html(signal_performance_fig(res), "fig-perf")
    distfig = _fig_html(distribution_fig(res), "fig-dist")

    toc = "".join(
        f'<a href="#{a}">{t}</a>' for a, t in [
            ("overview", "Overview"), ("signal-map", "Signal Map"),
            ("forward-returns", "Forward Returns"), ("hit-rates", "Hit Rates"),
            ("signal-performance", "Signal Performance"), ("distribution", "Distribution"),
            ("study-summary", "Study Summary"), ("results-table", "Results Table")])

    avg_med_toggle = (
        '<div class="toggle" data-toggle="cards">'
        '<button class="t-on" data-mode="avg">Avg</button>'
        '<button data-mode="med">Median</button></div>')

    body = f"""
    <header class="topbar">
      <div class="topbar-inner">
        <span class="back">Back to studies</span>
        <div class="chips">{chips}</div>
      </div>
    </header>

    <main class="wrap">
      <div class="title-block" id="overview">
        <div class="kicker">Backtest Visualizer</div>
        <h1>{cfg.title}</h1>
      </div>

      <div class="grid top-grid">{top_cards}</div>

      {_section("forward-returns-cards", "Forward Returns", "Average returns vs all-day baseline",
                f'<div class="grid cards-7">{fr_cards}</div>'
                f'<div class="grid cards-7">{hit_cards}</div>',
                extra_head=avg_med_toggle)}

      {_section("signal-map", "Signal Map", "SPX with signal triggers", sigmap)}

      <div class="grid two">
        {_section("forward-returns", "Forward Returns", "Average signal vs baseline", frfig)}
        {_section("hit-rates", "Hit Rates", "Signal hit rate vs baseline", hitfig)}
      </div>

      {_section("signal-performance", "Signal Performance", "Forward path after each trigger", perffig)}

      {_section("distribution", "Distribution", "Return distribution by horizon", distfig)}

      {_section("study-summary", "Study Summary", "Signal summary vs all-dataset baseline",
                f'<div class="grid hi-cards">{hi_cards}</div>{_summary_table(res)}')}

      {_section("results-table", "Results Table", "Backtest results",
                f'<div class="table-scroll">{_results_table(res)}</div>')}

      <footer class="disclaimer">
        Past performance is not indicative of future results. Backtested results are
        hypothetical, assumption-dependent, and may not reflect trading costs, taxes,
        slippage, liquidity, or execution constraints. Reproduction of
        <em>studies.dailychartbook.com</em> for educational purposes.
      </footer>
    </main>

    <nav class="toc"><div class="toc-title">Study Contents</div>{toc}</nav>
    """

    return _HTML_SHELL.format(
        title=cfg.title, plotlyjs=get_plotlyjs(), css=_CSS, body=body, js=_JS)


def _hi_card(label, value, sub) -> str:
    return f"""<div class="hi-card"><div class="hi-label">{label}</div>
      <div class="hi-value">{value}</div><div class="hi-sub">{sub}</div></div>"""


# ----------------------------------------------------------- css / shell ----
_CSS = """
:root{--green:#1a7f6a;--ink:#1d2b27;--muted:#8a9a95;--border:#e7eae8;--bg:#f4f6f5;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:14px;}
a{color:inherit;text-decoration:none;}
.topbar{background:var(--bg);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:20;}
.topbar-inner{max-width:1180px;margin:0 auto;padding:10px 24px;display:flex;
  align-items:center;justify-content:space-between;gap:16px;}
.back{border:1px solid var(--border);background:white;border-radius:999px;padding:5px 14px;
  font-size:12px;color:var(--green);font-weight:600;}
.chips{display:flex;gap:8px;flex-wrap:wrap;}
.chip{background:white;border:1px solid var(--border);border-radius:999px;padding:5px 12px;
  font-size:12px;color:var(--ink);}
.wrap{max-width:1180px;margin:0 auto;padding:24px 24px 80px;}
.title-block{padding:14px 0 22px;}
.kicker{color:var(--green);font-size:11px;font-weight:700;letter-spacing:.09em;
  text-transform:uppercase;margin-bottom:6px;}
h1{font-size:40px;line-height:1.1;margin:2px 0 0;font-weight:800;}
h2{font-size:19px;margin:2px 0 0;font-weight:700;}
.card{background:white;border:1px solid var(--border);border-radius:14px;padding:18px;}
.panel{margin:18px 0;}
.panel-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;gap:12px;}
.grid{display:grid;gap:14px;}
.top-grid{grid-template-columns:1.05fr 1.5fr 1.7fr;margin-bottom:6px;align-items:start;}
.stack{display:flex;flex-direction:column;gap:14px;}
.two{grid-template-columns:1fr 1fr;}
.cards-7{grid-template-columns:repeat(7,1fr);margin-bottom:14px;}
.hi-cards{grid-template-columns:repeat(4,1fr);margin-bottom:16px;}
.card-label{font-size:11px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);}
.card-sub{font-size:11px;color:var(--muted);margin-top:8px;}
.card-text{font-size:13px;line-height:1.5;margin-top:8px;color:#33433e;}
.stat-value{font-size:30px;font-weight:800;margin-top:8px;}
.stat.wide{padding:18px;}
.metric .card-label{margin-bottom:10px;}
.pill{display:inline-block;border-radius:8px;padding:5px 12px;font-weight:800;font-size:22px;}
.pill.pos{background:#d8efe8;color:#15795f;}
.pill.neg{background:#f6dede;color:#b9433d;}
.stat-value.pill{font-size:26px;}
.toggle{display:inline-flex;border:1px solid var(--border);border-radius:999px;overflow:hidden;background:white;}
.toggle button{border:0;background:white;padding:6px 16px;font-size:12px;cursor:pointer;color:var(--muted);font-weight:600;}
.toggle button.t-on{background:var(--green);color:white;}
.summary-table,.results-table{width:100%;border-collapse:collapse;font-size:12.5px;}
.summary-table th,.results-table th{background:var(--green);color:white;font-weight:600;
  padding:9px 8px;text-align:right;}
.summary-table th.rowlab,.results-table th.rowlab{text-align:left;}
.summary-table td,.results-table td{padding:8px;text-align:right;border-bottom:1px solid #eef1f0;}
.summary-table td.rowlab,.results-table td.rowlab{text-align:left;font-weight:500;}
.summary-table tr.strong td{font-weight:700;}
.summary-table tr.strong td,.summary-table tr.strong{background:#eef8f4;}
.results-table td.cpos{background:#e4f4ee;color:#15795f;}
.results-table td.cneg{background:#fbe7e7;color:#b9433d;}
.results-table tr.foot td{font-weight:700;border-top:2px solid var(--border);background:#fafbfb;}
.table-scroll{max-height:560px;overflow:auto;}
.hi-card{border-left:3px solid var(--green);padding:2px 0 2px 14px;}
.hi-label{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);}
.hi-value{font-size:24px;font-weight:800;margin:4px 0 2px;}
.hi-sub{font-size:11px;color:var(--muted);}
.disclaimer{font-size:11px;color:var(--muted);line-height:1.6;margin-top:30px;
  border-top:1px solid var(--border);padding-top:16px;}
.toc{position:fixed;top:90px;right:24px;width:165px;font-size:13px;display:none;}
.toc-title{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--green);margin-bottom:8px;}
.toc a{display:block;padding:4px 0;color:#55655f;}
.toc a:hover{color:var(--green);}
@media(min-width:1500px){.toc{display:block;}}
@media(max-width:900px){.cards-7,.hi-cards{grid-template-columns:repeat(2,1fr);}
  .top-grid,.two{grid-template-columns:1fr;}h1{font-size:30px;}}
"""

_JS = """
document.querySelectorAll('.toggle[data-toggle=cards] button').forEach(function(btn){
  btn.addEventListener('click', function(){
    var mode = btn.getAttribute('data-mode');
    document.querySelectorAll('.toggle[data-toggle=cards] button').forEach(function(b){b.classList.remove('t-on');});
    btn.classList.add('t-on');
    document.querySelectorAll('.card.metric').forEach(function(c){
      var v = c.querySelector('.metric-value'); var s = c.querySelector('.metric-sub');
      if(mode==='avg'){v.textContent=c.dataset.avg; s.textContent=c.dataset.subAvg;}
      else{v.textContent=c.dataset.med; s.textContent=c.dataset.subMed;}
    });
  });
});
"""

_HTML_SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script>{plotlyjs}</script>
<style>{css}</style>
</head><body>
{body}
<script>{js}</script>
</body></html>"""
