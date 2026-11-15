"""Farmer Joe weather model CLI.

Examples:
    .venv/bin/python run.py --farm champaign_corn
    .venv/bin/python run.py --lat 38.8 --lon -97.6 --crop wheat --n 10000 --seed 42
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from farmerjoe import MODEL_VERSION
from farmerjoe.config import VALID_MODES, Config, load_config
from farmerjoe.fetch.history import fetch_index_history, fetch_openmeteo_season, fetch_station_history
from farmerjoe.fetch.station_meta import load_station_meta
from farmerjoe.model import climatology as clim
from farmerjoe.model.dependence import fit_dependence, simulate_joint, solve_rain_year_corr
from farmerjoe.outputs import schema
from farmerjoe.outputs.aggregate import season_totals
from farmerjoe.outputs.contracts import payoff_matrix
from farmerjoe.outputs.fake import HONEST_LIMITS, make_fake_outputs
from farmerjoe.outputs.hedge import hedge_diagnostics
from farmerjoe.outputs.write import write_run
from farmerjoe.regions import index_locations
from farmerjoe.stations import haversine_km, resolve_market_stations, select_stations
from farmerjoe.validate.backtest import compare_season, correlation_check
from farmerjoe.validate.plots import plot_correlation_check, plot_season_comparison, plot_trend_holdout

PHASE = 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulate farm, settlement-station and production-region weather.")
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument("--farm", help="named reference farm from config (e.g. salina_wheat)")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--crop", choices=["corn", "soybeans", "wheat"])
    p.add_argument("--year", type=int, help="season year (default: next season not yet started)")
    p.add_argument("--start", help="window start YYYY-MM-DD (overrides crop calendar)")
    p.add_argument("--end", help="window end YYYY-MM-DD")
    p.add_argument("--stations", help="'auto' or comma-separated market-station codes")
    p.add_argument("--k-stations", type=int, dest="k_stations")
    p.add_argument("--n", type=int, dest="n_scenarios")
    p.add_argument("--seed", type=int)
    p.add_argument("--mode", choices=VALID_MODES)
    p.add_argument("--issue-date", dest="issue_date", help="replay forecast issued on YYYY-MM-DD")
    p.add_argument("--trend", action=argparse.BooleanOptionalAction, default=None,
                   help="separate linear tmax/tmin trends (default from config)")
    p.add_argument("--out-dir", dest="output_dir", help="parent folder for run outputs")
    p.add_argument("--run-id", dest="run_id", help="override the generated run id")
    p.add_argument("--refit", action="store_true", help="refit params even if cached in data/params")
    p.add_argument("--skip-validation", action="store_true", help="skip history checks and plots")
    p.add_argument("--prewarm", action="store_true",
                   help="download data and build cached runs for the demo farms in config.yaml")
    p.add_argument("--run", help="--mode hedge: weather run folder (default outputs/latest_run.txt)")
    p.add_argument("--budget", type=float, dest="budget_usd")
    p.add_argument("--risk-weight", type=float, dest="risk_weight")
    p.add_argument("--acres", type=float)
    return p.parse_args(argv)


def make_run_id(cfg: Config) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    who = cfg.farm_name or f"{cfg.lat:.2f}_{cfg.lon:.2f}"
    return f"{cfg.mode}_{who}_{cfg.crop}_{cfg.start:%Y%m}-{cfg.end:%Y%m}_seed{cfg.seed}_{stamp}"


# ----------------------------------------------------------------------------- data
def gather(cfg: Config) -> dict:
    """Select + verify stations, define index locations, load all histories (cached)."""
    raw = cfg.data_dir / "raw"
    explicit = None if cfg.stations == "auto" else cfg.stations
    with warnings.catch_warnings(record=True) as warned:
        warnings.simplefilter("always")
        codes = select_stations(cfg.lat, cfg.lon, cfg.market_stations, cfg.k_stations, explicit, cfg.max_station_km)
    st_meta, inv = load_station_meta(raw)
    resolved = resolve_market_stations(cfg.market_stations, st_meta, inv, cfg.all_years,
                                       cfg.data_dir / "params" / "stations_resolved.json", codes=codes)
    months = (cfg.start.month, cfg.end.month)
    obs: dict[str, pd.DataFrame] = {}
    farm = fetch_openmeteo_season(cfg.lat, cfg.lon, cfg.all_years, months, raw)
    obs["farm"] = farm
    for c, s in resolved.items():
        s.distance_km = round(float(haversine_km(cfg.lat, cfg.lon, s.lat, s.lon)), 1)
        obs[c] = fetch_station_history(s.ghcn_id, dt.date(cfg.all_years[0], 1, 1),
                                       dt.date(cfg.all_years[1], 12, 31), raw)
    idx = index_locations(cfg.regions, cfg.lat, cfg.lon)
    for r in idx:
        obs[r["code"]] = fetch_index_history(r["points"], cfg.all_years, months, raw)
    return {"stations": resolved, "index": idx, "obs": obs, "timezone": farm.attrs.get("timezone", ""),
            "warnings": [str(w.message) for w in warned]}


def build_dependence(cfg: Config, data: dict, params: dict, rng: np.random.Generator) -> dict:
    dep = fit_dependence(data["obs"], params, cfg.start, cfg.end, cfg.fit_years)
    hist = {l: clim.historical_season_totals(o, cfg.start, cfg.end, cfg.fit_years).set_index("year")["rain_total_in"]
            for l, o in data["obs"].items()}
    return solve_rain_year_corr(params, dep, hist, len(cfg.dates), rng)


def source_key(cfg: Config, loc: str, data: dict) -> str:
    if loc == "farm":
        return f"farm_{cfg.lat:.3f}_{cfg.lon:.3f}"
    if loc in data["stations"]:
        return data["stations"][loc].ghcn_id
    return f"{cfg.crop}_{loc}"


def get_params(cfg: Config, data: dict, trend: bool, rng: np.random.Generator, refit: bool) -> dict:
    """Per-location climatology params, cached in data/params keyed by the full fit spec."""
    c = cfg.climatology
    out = {}
    for loc, o in data["obs"].items():
        key = source_key(cfg, loc, data)
        spec = {"source": key, "fit_years": list(cfg.fit_years),
                "window_md": [cfg.start.strftime("%m-%d"), cfg.end.strftime("%m-%d")],
                "buffer_days": int(c.get("buffer_days", 0)), "interannual": bool(c.get("interannual", True)),
                "trend": bool(trend), "model_version": MODEL_VERSION, "phase": PHASE}
        path = cfg.data_dir / "params" / f"clim_{key}_{cfg.start:%m%d}-{cfg.end:%m%d}_trend{int(trend)}.json"
        if path.exists() and not refit:
            p = clim.load_params(path)
            if p.get("spec") == spec:
                out[loc] = p
                continue
        p = clim.fit_location(o, cfg.start, cfg.end, cfg.fit_years, rng, spec["buffer_days"],
                              trend=trend, interannual=spec["interannual"])
        p["spec"] = spec
        clim.save_params(p, path)
        out[loc] = p
    return out


# ----------------------------------------------------------------------- validation
def trend_holdout(cfg: Config, data: dict, rng_fit: np.random.Generator, rng: np.random.Generator,
                  refit: bool, n: int = 4000) -> pd.DataFrame:
    """Fit on 1995-2019 with the trend off and on; simulate each holdout year (2020-24) and
    compare season GDD / hot days with what was observed. bias = mean(sim − obs) over years."""
    d = len(cfg.dates)
    rows = []
    for trend in (False, True):
        params = get_params(cfg, data, trend, rng_fit, refit)
        dep = build_dependence(cfg, data, params, rng_fit)
        locs = dep["locations"]
        errs = {(l, v): [] for l in locs for v in ("gdd", "hot_days_95")}
        for y in range(cfg.holdout_years[0], cfg.holdout_years[1] + 1):
            a = simulate_joint(params, dep, n, d, y, rng)
            s = season_totals(a["tmax_f"], a["tmin_f"], a["precip_in"], locs)
            for l in locs:
                h = clim.historical_season_totals(data["obs"][l], cfg.start.replace(year=y),
                                                  cfg.end.replace(year=y), (y, y))
                if h.empty:
                    continue
                for v in ("gdd", "hot_days_95"):
                    errs[(l, v)].append(float(s[f"{v}_{l}"].mean()) - float(h[v].iloc[0]))
        for (l, v), e in errs.items():
            if e:
                rows.append(dict(location=l, variable=v, trend="on" if trend else "off",
                                 bias=float(np.mean(e)), mae=float(np.mean(np.abs(e))), n_years=len(e),
                                 beta_tmax_f_per_decade=(params[l]["trend"] or {}).get("tmax_f", {}).get("beta_f_per_decade"),
                                 beta_tmin_f_per_decade=(params[l]["trend"] or {}).get("tmin_f", {}).get("beta_f_per_decade")))
    return pd.DataFrame(rows)


def validate(cfg: Config, data: dict, season: pd.DataFrame, locs: list[str], out_dir: Path,
             rng_fit: np.random.Generator, rng: np.random.Generator, refit: bool) -> dict:
    plots = out_dir / "plots"
    plots.mkdir(exist_ok=True)
    hist = {l: clim.historical_season_totals(data["obs"][l], cfg.start, cfg.end, cfg.fit_years) for l in locs}

    marg = []
    for l in locs:
        c = compare_season(season, hist[l], l, rng)
        for r in c.itertuples():
            marg.append(dict(location=l, variable=r.variable, stat=r.stat, sim=r.sim, hist=r.hist,
                             rel_err=r.rel_err, within_tol=r.within_tol, within_ci=r.within_ci))
    marg = pd.DataFrame(marg)
    marg.to_csv(plots / "marginal_check_fit_years.csv", index=False)

    pairs = [("farm", c, "farm–station") for c in data["stations"]] + \
            [("farm", r["code"], "farm–region") for r in data["index"]]
    corr = correlation_check(season, hist, pairs, ("rain_total_in", "hot_days_95", "gdd"), rng)
    corr.to_csv(plots / "correlation_check.csv", index=False)
    who = cfg.farm_name or f"({cfg.lat}, {cfg.lon})"
    plot_correlation_check(corr[corr.variable.isin(["rain_total_in", "hot_days_95"])],
                           plots / "correlation_check.png",
                           f"{who}, {cfg.crop} {cfg.start:%b}–{cfg.end:%b}: farm correlations, "
                           f"simulated vs historical ({cfg.fit_years[0]}–{cfg.fit_years[1]})")
    plot_season_comparison(season, hist["farm"], "farm", plots / "season_sim_vs_hist_farm.png",
                           f"{who}, fit years {cfg.fit_years[0]}–{cfg.fit_years[1]}")

    th = trend_holdout(cfg, data, rng_fit, rng, refit)
    th.to_csv(plots / "trend_holdout.csv", index=False)
    plot_trend_holdout(th, plots / "trend_holdout.png",
                       f"{who}: trend switch on the {cfg.holdout_years[0]}–{cfg.holdout_years[1]} holdout")
    return {"marginal": marg, "corr": corr, "trend": th, "plots": plots}


# ------------------------------------------------------------------------------ run
def run_joint(cfg: Config, out_dir: Path, run_id: str, rng: np.random.Generator, refit: bool,
              skip_validation: bool) -> dict:
    """Phase 2: farm + stations + index locations simulated jointly from climatology."""
    rng_fit, rng_sim, rng_val, rng_hedge = rng.spawn(4)   # independent streams from the one rng
    data = gather(cfg)
    trend = bool(cfg.climatology.get("trend", False))
    params = get_params(cfg, data, trend, rng_fit, refit)
    dep = build_dependence(cfg, data, params, rng_fit)
    locs = dep["locations"]
    t0 = time.perf_counter()
    arrays = simulate_joint(params, dep, cfg.n_scenarios, len(cfg.dates), cfg.year, rng_sim)
    sim_s = time.perf_counter() - t0

    station_info = []
    for c, s in data["stations"].items():
        h = clim.historical_season_totals(data["obs"][c], cfg.start, cfg.end, cfg.fit_years)
        info = s.as_meta()
        info.update(record_years=int(len(h)), short_record=bool(len(h) < 20))
        station_info.append(info)
    if trend:
        trend_meta = {"enabled": True, **{l: params[l]["trend"] for l in locs}}
        if cfg.year - cfg.fit_years[1] > 10:
            warnings.warn(f"trend extrapolated {cfg.year - cfg.fit_years[1]} years past the last fit year")
    else:
        trend_meta = {"enabled": False}

    meta = {
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "forecast_issue_time": None, "N": cfg.n_scenarios, "seed": cfg.seed,
        "window": {"start": cfg.start.isoformat(), "end": cfg.end.isoformat()},
        "farm": {"lat": cfg.lat, "lon": cfg.lon, "name": cfg.farm_name},
        "crop": cfg.crop, "season_window_source": cfg.season_window_source, "farm_timezone": data["timezone"],
        "stations": list(data["stations"]), "station_info": station_info,
        "index_locations": data["index"], "trend": trend_meta,
        "model_version": MODEL_VERSION, "mode": "climatology", "phase": PHASE, "calibration_scores": None,
        "fit_years": list(cfg.fit_years), "holdout_years": list(cfg.holdout_years),
        "dependence": dep, "station_selection_warnings": data["warnings"],
        "honest_limits": HONEST_LIMITS,
        "notes": "Climatology only (no forecast). Market stations are unverified against Kalshi "
                 "listings unless station_info.verified_market is true.",
    }
    markets = {c: s.markets for c, s in data["stations"].items()}

    def hedge_meta(daily, season, contracts):
        pay = payoff_matrix(contracts, daily, season)
        return {"hedge_diagnostics": hedge_diagnostics(season, contracts, pay, station_info, rng_hedge)}

    season, contracts = write_run(out_dir, arrays, cfg.dates, locs, markets, [], cfg.contracts, meta, hedge_meta)
    res = {"data": data, "params": params, "locs": locs, "season": season, "sim_seconds": sim_s,
           "station_info": station_info}
    if not skip_validation:
        v = validate(cfg, data, season, locs, out_dir, rng_fit, rng_val, refit)
        res.update(v)
        m = json.loads((out_dir / schema.META_FILE).read_text())
        m["validation"] = {
            "correlation_check": v["corr"].round(4).replace({np.nan: None}).to_dict("records"),
            "trend_holdout": v["trend"].round(4).replace({np.nan: None}).to_dict("records"),
            "marginal_within_ci_share": float(v["marginal"].within_ci.mean()),
        }
        schema.write_meta(m, out_dir / schema.META_FILE)
    return res


# -------------------------------------------------------------------------- summary
def print_summary(out_dir: Path, cfg: Config, res: dict | None) -> None:
    season = pd.read_parquet(out_dir / schema.SEASON_FILE)
    contracts = pd.read_csv(out_dir / schema.CONTRACTS_FILE)
    meta = json.loads((out_dir / schema.META_FILE).read_text())
    pd.set_option("display.width", 160)
    print(f"\nRun {meta['run_id']}  (mode={cfg.mode}, N={cfg.n_scenarios}, seed={cfg.seed})")
    print(f"Farm {cfg.farm_name or ''} ({cfg.lat}, {cfg.lon}), crop {cfg.crop}, window {cfg.start} .. {cfg.end} "
          f"[{cfg.season_window_source}], tz {meta.get('farm_timezone', '')}")
    if meta.get("fake_data"):
        print("*** FAKE DATA — schema/integration only, not a forecast ***")
    if meta.get("station_info"):
        print("\nSettlement stations (nearest market stations):")
        for s in meta["station_info"]:
            print(f"  {s['code']:4s} {s['ghcn_id']}  {s['name'][:44]:44s} {s['distance_km']:7.1f} km  "
                  f"seasons={s['record_years']}{' SHORT' if s['short_record'] else ''}  "
                  f"markets={','.join(s['markets'])}  verified_market={s['verified_market']}")
        for w in meta.get("station_selection_warnings", []):
            print(f"  WARNING: {w}")
    if meta.get("index_locations"):
        print("\nProduction-region index locations:")
        for r in meta["index_locations"]:
            print(f"  {r['code']:8s} centroid {r['centroid']}  {r['distance_km']:7.1f} km from farm  ({len(r['points'])} points)")

    rows = []
    for loc in meta.get("locations", []):
        for v in schema.SEASON_VARS:
            q = np.percentile(season[f"{v}_{loc}"], [5, 25, 50, 75, 95])
            rows.append([loc, v, *np.round(q, 1)])
    print("\nSeason variable percentiles:")
    print(pd.DataFrame(rows, columns=["location", "variable", "p5", "p25", "p50", "p75", "p95"]).to_string(index=False))

    print(f"\nContracts: {len(contracts)}; closest to 50/50:")
    top = contracts.assign(dist=(contracts["p_model"] - 0.5).abs()).nsmallest(5, "dist")
    print(top[["contract_id", "p_model", "p_se"]].round(4).to_string(index=False))

    hd = meta.get("hedge_diagnostics", {})
    if hd:
        print("\nHedge diagnostics (farm season variable vs contract payoffs, out-of-sample R²):")
        for v in ("rain_total_in", "hot_days_95", "gdd"):
            d = hd.get(v, {})
            if "max_hedge_effectiveness" in d:
                print(f"  {v:14s} max HE {d['max_hedge_effectiveness']}  by station {d['by_station']}  "
                      f"corr {d['corr_with_station']}")
            else:
                print(f"  {v:14s} {d.get('note', '')}")
    print(f"\nOutputs: {out_dir.resolve()}")


def print_validation(res: dict) -> None:
    corr = res["corr"]
    print("\n=== Phase 2 acceptance: farm correlations, simulated vs historical (fit years) ===")
    show = corr[corr.variable.isin(["rain_total_in", "hot_days_95"])].copy()
    print(show[["pair", "kind", "variable", "n_years", "hist_corr", "ci_lo", "ci_hi", "sim_corr", "diff",
                "within_tol", "within_ci"]].round(3).to_string(index=False))
    defined = show[show.hist_corr.notna()]
    print(f"within ±0.1: {int(defined.within_tol.sum())}/{len(defined)}   "
          f"inside historical 90% range: {int(defined.within_ci.sum())}/{len(defined)}   "
          f"undefined (no events): {int(show.hist_corr.isna().sum())}")
    m = res["marginal"]
    print("\nMarginal checks per location (fit years): sim inside historical 90% range "
          f"for {int(m.within_ci.sum())}/{len(m)} stats; within 10% for {int(m.within_tol.sum())}/{len(m)}")
    bad = m[~m.within_ci]
    if len(bad):
        print(bad.round(3).to_string(index=False))
    th = res["trend"]
    print("\n=== Trend switch on the holdout (bias = simulated − observed, mean over holdout years) ===")
    piv = th.pivot_table(index=["location", "variable"], columns="trend", values=["bias", "mae"]).round(2)
    print(piv.to_string())
    agg = th.groupby(["variable", "trend"])["mae"].mean().unstack().round(2)
    print("\nMean absolute holdout error across locations:")
    print(agg.to_string())
    print(f"Plots: {res['plots'].resolve()}")


def prewarm(config_path: str | None = None) -> int:
    """Build (or confirm) the cached web runs for the demo farms, so the demo never waits."""
    import yaml
    from farmerjoe.config import DEFAULT_CONFIG_PATH
    from farmerjoe.webcache import snap, weather_run
    farms = yaml.safe_load(Path(config_path or DEFAULT_CONFIG_PATH).read_text()).get("demo_farms", [])
    for f in farms:
        t = time.perf_counter()
        out_dir, _ = weather_run(f["lat"], f["lon"], f["crop"])
        print(f"{f['name']:16s} {f['crop']:9s} grid {snap(f['lat'], f['lon'])}  ready in "
              f"{time.perf_counter() - t:6.1f}s  -> {out_dir.name}", flush=True)
    return 0


def run_hedge_cli(args: argparse.Namespace) -> int:
    """--mode hedge: hedge model v1 on the latest (or given) weather run."""
    from farmerjoe.hedge.pipeline import run_hedge
    run_dir = Path(args.run) if args.run else Path(Path("outputs/latest_run.txt").read_text().strip())
    ov = {"budget_usd": args.budget_usd, "risk_weight": args.risk_weight, "acres": args.acres}
    res = run_hedge(run_dir, ov, seed=args.seed)
    r, ev = res["rec"], res["eval"]
    b, a = ev["before"], ev["after"]
    print(f"Hedge model v1 on {run_dir}  (placeholders; contracts hypothetical)")
    print(f"Decision: {r['decision'].upper()} — {r['reason']}")
    print(f"Natural hedge: {res['nh']['natural_hedge_pct']:.1%} of revenue swing removed")
    print(f"Eval half: mean ${b['mean']:,.0f} → ${a['mean']:,.0f}; 5th pct ${b['p5']:,.0f} → ${a['p5']:,.0f}; "
          f"CVaR5 ${b['cvar5']:,.0f} → ${a['cvar5']:,.0f}; cost ${ev['cost']:,.0f}")
    if len(res["legs"]):
        pd.set_option("display.width", 200)
        print(res["legs"][["contract_id", "side", "contracts", "dollars", "fair_value", "ask", "max_entry_price",
                           "limit_price"]].round(3).to_string(index=False))
    print(f"Outputs: {res['dir'].resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.prewarm:
        return prewarm(args.config)
    skip = {"config", "run_id", "refit", "skip_validation", "run", "budget_usd", "risk_weight", "acres", "prewarm"}
    if args.mode == "hedge":
        return run_hedge_cli(args)
    overrides = {k: v for k, v in vars(args).items() if k not in skip}
    cfg = load_config(args.config, overrides)
    rng = np.random.default_rng(cfg.seed)  # the ONLY rng; children are spawned from it
    run_id = args.run_id or make_run_id(cfg)
    out_dir = cfg.output_dir / run_id

    t0 = time.perf_counter()
    res = None
    if cfg.mode == "fake":
        explicit = None if cfg.stations == "auto" else cfg.stations
        codes = select_stations(cfg.lat, cfg.lon, cfg.market_stations, cfg.k_stations, explicit, cfg.max_station_km)
        make_fake_outputs(cfg.n_scenarios, cfg.seed, out_dir, start=cfg.start, end=cfg.end, stations=codes,
                          farm=(cfg.lat, cfg.lon), forecast_horizon_days=cfg.forecast_horizon_days,
                          contract_grid=cfg.contracts, index_codes=list(cfg.regions), run_id=run_id, rng=rng)
    elif cfg.mode == "climatology":
        res = run_joint(cfg, out_dir, run_id, rng, args.refit, args.skip_validation)
    else:
        print(f"--mode {cfg.mode} is not built yet (forecast arrives in Phases 3-4).", file=sys.stderr)
        return 2
    elapsed = time.perf_counter() - t0

    info = schema.validate_run_dir(out_dir)
    (cfg.output_dir / "latest_run.txt").write_text(str(out_dir) + "\n")   # read by --mode hedge
    sim_note = f" (simulation {res['sim_seconds']:.1f}s)" if res else ""
    print(f"Wrote and validated {len(schema.ALL_FILES)} files in {elapsed:.1f}s{sim_note}: "
          f"N={info['N']}, rows={info['daily_rows']:,}, locations={info['locations']}, contracts={info['contracts']}")
    print_summary(out_dir, cfg, res)
    if res is not None and "corr" in res:
        print_validation(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
