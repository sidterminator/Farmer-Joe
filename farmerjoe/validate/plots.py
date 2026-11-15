"""Validation plots (saved to outputs/<run_id>/plots/)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Validated reference palette (dataviz skill): categorical slots 1-2, light surface.
SIM_COLOR = "#2a78d6"
HIST_COLOR = "#eb6834"
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"

_LABELS = {"rain_total_in": ("Season rain total", "inches"),
           "hot_days_95": ("Hot days (tmax ≥ 95°F)", "days"),
           "gdd": ("Growing degree days (base 50, cap 86)", "°F-days")}


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _stats_text(s: np.ndarray, h: np.ndarray, unit: str) -> str:
    return (f"simulated  mean {s.mean():.2f}  sd {s.std(ddof=1):.2f}\n"
            f"historical mean {h.mean():.2f}  sd {h.std(ddof=1):.2f}  (n={len(h)} yrs)")


def plot_season_variable(ax: plt.Axes, s: np.ndarray, h: np.ndarray, var: str) -> None:
    """Simulated distribution (filled) vs historical years (outline + one tick per year)."""
    title, unit = _LABELS[var]
    _style(ax)
    if var == "hot_days_95":
        top = int(max(np.quantile(s, 0.999), h.max()))
        s = np.minimum(s, top)  # fold the far tail into the last bar
        k = np.arange(top + 1)
        ps = np.bincount(s.astype(int), minlength=top + 1) / len(s)
        ph = np.bincount(h.astype(int), minlength=top + 1) / len(h)
        ax.bar(k - 0.2, ps, width=0.38, color=SIM_COLOR, label=f"Simulated (N={len(s):,})")
        ax.bar(k + 0.2, ph, width=0.38, color=HIST_COLOR, label=f"Historical ({len(h)} Julys)")
        ax.set_ylabel("probability", color=TEXT_2, fontsize=9)
        ax.set_xticks(k[:: max(1, len(k) // 12)])
    else:
        lo, hi = min(s.min(), h.min()), np.quantile(s, 0.999)
        hi = max(hi, h.max())
        bins = np.linspace(lo, hi, 36)
        ax.hist(s, bins=bins, density=True, color=SIM_COLOR, alpha=0.55,
                edgecolor=SURFACE, linewidth=1, label=f"Simulated (N={len(s):,})")
        ax.hist(h, bins=bins[::3], density=True, histtype="step", color=HIST_COLOR,
                linewidth=2, label=f"Historical ({len(h)} Julys)")
        ymax = ax.get_ylim()[1]
        ax.vlines(h, 0, ymax * 0.06, color=HIST_COLOR, linewidth=1.5)  # one tick per year
        ax.set_xlim(left=max(0.0, lo - 0.02 * (hi - lo)) if var == "rain_total_in" else None)
        ax.set_ylabel("density", color=TEXT_2, fontsize=9)
    ax.set_title(title, loc="left", color=TEXT, fontsize=11, fontweight="semibold")
    ax.set_xlabel(unit, color=TEXT_2, fontsize=9)
    ax.text(0.98, 0.97, _stats_text(s, h, unit), transform=ax.transAxes, ha="right", va="top",
            fontsize=8, color=TEXT_2, family="monospace")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.3)  # headroom so the stats text clears the bars


def plot_season_comparison(sim: pd.DataFrame, hist: pd.DataFrame, loc: str,
                           out_path: str | Path, subtitle: str = "") -> Path:
    """Three-panel figure: rain total, hot days, GDD — simulated vs historical."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), facecolor=SURFACE)
    for ax, v in zip(axes, ("rain_total_in", "hot_days_95", "gdd")):
        plot_season_variable(ax, sim[f"{v}_{loc}"].to_numpy(float), hist[v].to_numpy(float), v)
    fig.suptitle(f"{loc}: simulated vs historical July seasons" + (f" — {subtitle}" if subtitle else ""),
                 x=0.01, ha="left", color=TEXT, fontsize=13, fontweight="semibold")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.93), ncol=2,
               frameon=False, fontsize=9, labelcolor=TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    return out_path


KIND_COLORS = {"farm–station": SIM_COLOR, "farm–region": HIST_COLOR}
_SHORT = {"rain_total_in": "Season rain", "hot_days_95": "Hot days (≥95°F)", "gdd": "GDD"}


def plot_correlation_check(df: pd.DataFrame, out_path: str | Path, title: str) -> Path:
    """Simulated vs historical farm–X correlation, one panel per variable. Horizontal bars:
    90% bootstrap range of the historical value; shaded band: |sim − hist| ≤ 0.1."""
    variables = list(dict.fromkeys(df["variable"]))
    fig, axes = plt.subplots(1, len(variables), figsize=(6.2 * len(variables), 5.6), facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    for ax, v in zip(axes, variables):
        _style(ax)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        d = df[(df.variable == v) & df.hist_corr.notna()]
        ax.fill_between([-1, 1], [-1.1, 0.9], [-0.9, 1.1], color=GRID, alpha=0.6, linewidth=0,
                        label="within ±0.1")
        ax.plot([-1, 1], [-1, 1], color=TEXT_2, linewidth=1, linestyle=(0, (4, 3)))
        for kind, color in KIND_COLORS.items():
            k = d[d.kind == kind]
            if k.empty:
                continue
            ax.errorbar(k.hist_corr, k.sim_corr, xerr=[k.hist_corr - k.ci_lo, k.ci_hi - k.hist_corr],
                        fmt="o", ms=8, color=color, ecolor=color, elinewidth=1.2, capsize=0,
                        markeredgecolor=SURFACE, markeredgewidth=1.5, label=kind)
            for r in k.itertuples():
                ax.annotate(r.pair.split("–")[1], (r.hist_corr, r.sim_corr), xytext=(6, -10),
                            textcoords="offset points", fontsize=8, color=TEXT_2)
        lo = min(-0.1, float(np.nanmin(d[["ci_lo", "sim_corr"]].to_numpy())) - 0.05) if len(d) else -0.1
        ax.set_xlim(lo, 1.0)
        ax.set_ylim(lo, 1.0)
        ax.set_aspect("equal")
        ax.set_xlabel("historical correlation (fit years)", color=TEXT_2, fontsize=9)
        ax.set_ylabel("simulated correlation", color=TEXT_2, fontsize=9)
        ax.set_title(_SHORT.get(v, v), loc="left", color=TEXT, fontsize=11, fontweight="semibold")
        missing = df[(df.variable == v) & df.hist_corr.isna()]
        if len(missing):
            ax.text(0.02, 0.98, "not defined (no events): " + ", ".join(p.split("–")[1] for p in missing.pair),
                    transform=ax.transAxes, va="top", fontsize=8, color=TEXT_2)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper left", bbox_to_anchor=(0.01, 0.93), ncol=3, frameon=False, fontsize=9,
               labelcolor=TEXT)
    fig.suptitle(title, x=0.01, ha="left", color=TEXT, fontsize=13, fontweight="semibold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    return out_path


def plot_trend_holdout(df: pd.DataFrame, out_path: str | Path, title: str) -> Path:
    """Holdout bias (simulated mean − observed, averaged over holdout years) per location,
    trend off vs on, for GDD and hot days."""
    variables = ["gdd", "hot_days_95"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), facecolor=SURFACE)
    for ax, v in zip(axes, variables):
        _style(ax)
        d = df[df.variable == v]
        locs = list(dict.fromkeys(d.location))
        x = np.arange(len(locs))
        for off, (setting, color) in zip((-0.2, 0.2), (("off", SIM_COLOR), ("on", HIST_COLOR))):
            vals = [d[(d.location == l) & (d.trend == setting)].bias.iloc[0] for l in locs]
            ax.bar(x + off, vals, width=0.38, color=color, label=f"trend {setting}")
        ax.axhline(0, color=TEXT_2, linewidth=1)
        ax.set_xticks(x)
        ax.set_xticklabels(locs, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("bias: simulated − observed" + (" (°F-days)" if v == "gdd" else " (days)"),
                      color=TEXT_2, fontsize=9)
        ax.set_title(_SHORT[v] + " — holdout bias", loc="left", color=TEXT, fontsize=11, fontweight="semibold")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper left", bbox_to_anchor=(0.01, 0.93), ncol=2, frameon=False, fontsize=9,
               labelcolor=TEXT)
    fig.suptitle(title, x=0.01, ha="left", color=TEXT, fontsize=13, fontweight="semibold")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    return out_path


def plot_revenue_before_after(before: np.ndarray, after: np.ndarray, out_path: str | Path, title: str) -> Path:
    """One chart: unhedged vs hedged revenue distributions, 5th percentiles marked."""
    fig, ax = plt.subplots(figsize=(11, 4.8), facecolor=SURFACE)
    _style(ax)
    lo, hi = np.percentile(np.concatenate([before, after]), [0.2, 99.8])
    bins = np.linspace(lo, hi, 60)
    ax.hist(before, bins=bins, color=SIM_COLOR, alpha=0.5, edgecolor=SURFACE, linewidth=0.8, label="unhedged")
    ax.hist(after, bins=bins, histtype="step", color=HIST_COLOR, linewidth=2, label="hedged")
    ytop = ax.get_ylim()[1]
    for x, c, name, ha, y in ((np.percentile(before, 5), SIM_COLOR, "unhedged", "right", 0.97),
                              (np.percentile(after, 5), HIST_COLOR, "hedged", "left", 0.80)):
        ax.axvline(x, color=c, linewidth=1.5, linestyle=(0, (4, 3)))
        pad = " " if ha == "left" else ""
        ax.text(x, ytop * y, f"{pad}5th pct {name}{' ' if ha == 'right' else ''}\n{pad}${x:,.0f}{' ' if ha == 'right' else ''}",
                color=TEXT_2, fontsize=8, va="top", ha=ha)
    ax.set_xlabel("season revenue (USD)", color=TEXT_2, fontsize=9)
    ax.set_ylabel("scenarios", color=TEXT_2, fontsize=9)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k"))
    ax.set_title(title, loc="left", color=TEXT, fontsize=11, fontweight="semibold")
    ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=TEXT)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    return out_path
