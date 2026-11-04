"""Scenarios for the old-age dependency ratio (OADR = people 65+ per 100 people aged 15-64), 2025-2075.

All scenarios use Statistics Canada's M1 assumptions for fertility, mortality, emigration and the
non-permanent resident share (see validate.py), and differ only in permanent immigration:

  none      no new permanent immigrants
  plan      380,000 a year to 2028 (2026-2028 Immigration Levels Plan), then 0.9% of population a year
  high      1.2% of population a year (about the 2023-24 level)
  required  the inflow each year that holds the OADR at its 2025 level (UN "replacement migration" method)

Plus one measurement scenario on the plan path: the retirement threshold rises from 65 to 70 between
2025 and 2045 (three months a year), and the ratio is measured against that threshold.
"""
import contextlib, io
import numpy as np
import pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import validate as v          # reuses the validated model, assumptions and calibrated NPR start share
from projection import summarize, oadr_from_counts, BASE_YEAR

m, tfr, npr = v.m, v.tfr_m1, v.npr_path(v.s0)
popsum = lambda P: P["M"].sum() + P["F"].sum()

def plan(y, P, probe):
    return 380_000 if y < 2028 else 0.009 * popsum(P)

def high(y, P, probe):
    return 0.012 * popsum(P)

def none(y, P, probe):
    return 0.0

TARGET = oadr_from_counts(m.P0)
def required(y, P, probe):
    """Smallest inflow that keeps next year's OADR at or below the 2025 level (bisection)."""
    if oadr_from_counts(probe(0.0)) <= TARGET:
        return 0.0
    lo, hi = 0.0, 1e6
    while oadr_from_counts(probe(hi)) > TARGET:
        hi *= 2
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if oadr_from_counts(probe(mid)) > TARGET else (lo, mid)
    return hi

runs = {}
for name, f in [("none", none), ("plan", plan), ("high", high), ("required", required)]:
    pops, imms, flows = m.run(tfr, f, npr_share=npr)
    s = summarize(pops)
    s["immigrants"] = pd.Series(imms).reindex(s.index)          # flow during year -> year+1
    s["imm_rate_%"] = s.immigrants / s["pop"] * 100
    runs[name] = (pops, s)

retire = lambda y: min(70.0, 65 + 5 * max(0, y - BASE_YEAR) / 20)
runs["plan_retire70"] = (runs["plan"][0], summarize(runs["plan"][0], retire_age=retire))

oadr = pd.DataFrame({k: s["oadr"] for k, (_, s) in runs.items()})
oadr.round(3).to_csv("oadr_scenarios.csv")
req = runs["required"][1][["pop", "immigrants", "imm_rate_%", "oadr"]]
req.round(3).to_csv("required_inflow.csv")

# Share of the 2075 population aged 65+ that exists because of post-2025 permanent immigration
# (immigrants plus their descendants): difference between the plan and no-immigration runs.
old = {k: runs[k][1].loc[2075, "old"] for k in ("plan", "none", "high")}
attrib = (old["plan"] - old["none"]) / old["plan"] * 100

YRS = [2025, 2030, 2035, 2040, 2050, 2060, 2070, 2075]
print(f"OADR 2025 target: {TARGET:.2f}\n")
print("OADR by scenario"); print(oadr.loc[YRS].round(1).to_string())
print("\nPopulation (millions)")
print(pd.DataFrame({k: s["pop"] / 1e6 for k, (_, s) in runs.items() if k != "plan_retire70"}).loc[YRS].round(1).to_string())
print("\nRequired inflow to hold OADR at 2025 level")
r = req.copy(); r["immigrants_k"] = r.immigrants / 1e3
print(r.loc[[2025, 2026, 2027, 2028, 2030, 2035, 2040, 2045, 2050, 2060, 2070, 2074], ["immigrants_k", "imm_rate_%"]].round(2).to_string())
print(f"\nCumulative required 2025-2074: {req.immigrants.sum()/1e6:.1f}M vs plan {runs['plan'][1].immigrants.sum()/1e6:.1f}M")
print(f"Population 2075 under required path: {req.loc[2075,'pop']/1e6:.1f}M")
print(f"Share of 2075 65+ population attributable to post-2025 immigration (plan): {attrib:.1f}%")
for k in ("plan", "high"):
    print(f"  {k}: 65+ in 2075 = {runs[k][1].loc[2075,'old']/1e6:.2f}M vs none {old['none']/1e6:.2f}M; "
          f"working-age = {runs[k][1].loc[2075,'working']/1e6:.2f}M vs none {runs['none'][1].loc[2075,'working']/1e6:.2f}M")
