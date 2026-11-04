"""Combined policy: immigration phased to 0.5% of population, age-restricted, plus a tripled child benefit
paid for out of seniors' spending (2% of GDP moved dollar for dollar).

Immigration: current plan (380,000) through 2028, then the rate falls linearly from 0.9% of population in
2028 to 0.5% in 2038 and stays there.
Age restriction: no permanent immigrants aged 50+ (about 10% of the 2017-2025 intake); those places are
reassigned proportionally across ages 0-49, so the total number of immigrants is unchanged.
Child benefit: R = 2% of GDP moved from seniors' spending to the CCB from 2027 (tripling it), see policy.py.
R was chosen as the transfer at which this reduced-immigration policy matches the current plan's dependency
ratio by 2100 in the central fertility case (about 2070 in the high case).
"""
import contextlib, io
import numpy as np
import pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import policy as po
R = 2.0
f, m, npr, base_tfr = po.f, po.m, po.npr, po.base_tfr
from projection import summarize

AGES = np.arange(101)
def phased(target):
    def imm(y, P, probe):
        if y < 2028:
            return 380_000
        rate = 0.009 + (target - 0.009) * min(1.0, (y - 2028) / 10)
        return rate * (P["M"].sum() + P["F"].sum())
    return imm

orig = {s: m.mig[s]["imm_share"].copy() for s in "MF"}
def set_age_cap(cap):
    if cap is None:
        for s in "MF": m.mig[s]["imm_share"] = orig[s].copy()
        return
    kept = {s: np.where(AGES < cap, orig[s], 0.0) for s in "MF"}
    tot = kept["M"].sum() + kept["F"].sum()
    for s in "MF": m.mig[s]["imm_share"] = kept[s] / tot

def run(imm, tfr, cap=None):
    set_age_cap(cap)
    pops, imms, _ = m.run(tfr, imm, npr_share=npr)
    set_age_cap(None)
    s = summarize(pops)
    s["immigrants"] = pd.Series(imms)
    s["dep_total"] = (s.young + s.old) / s.working * 100
    s["spend65"] = pd.Series({y: sum(f.shares(P, year=y)) for y, P in pops.items()})
    return s

c = {
    "plan": run(po.plan, base_tfr),
    "p05": run(phased(0.005), base_tfr),
    "p05_age": run(phased(0.005), base_tfr, cap=50),
}
for lab, e in (("low", 0.05), ("central", 0.12), ("high", 0.23)):
    c[f"combo_{lab}"] = run(phased(0.005), po.tfr_with(R, e), cap=50)

T = f.TARGET
tab = lambda col: pd.DataFrame({k: v[col] for k, v in c.items()})
oadr, spend, pop, tot = tab("oadr"), tab("spend65"), tab("pop") / 1e6, tab("dep_total")
envelope = pd.Series({k: T - (R if k.startswith("combo") else 0.0) for k in c})
cut = ((1 - envelope / spend) * 100).clip(lower=0)
for name, d in [("oadr", oadr), ("spend65", spend), ("pop", pop), ("dep_total", tot), ("required_cut", cut)]:
    d.round(3).to_csv(f"combo_{name}.csv")

YRS = [2025, 2030, 2040, 2050, 2060, 2075, 2090, 2100]
print("Immigrants/yr under 0.5% (thousands):", {y: round(c['p05'].immigrants[y] / 1e3) for y in (2030, 2038, 2050, 2075, 2099)})
print("\nOld-age dependency ratio"); print(oadr.loc[YRS].round(1).to_string())
print("\nTotal dependency ratio"); print(tot.loc[YRS].round(1).to_string())
print("\nPopulation (M)"); print(pop.loc[YRS].round(1).to_string())
print("\nSeniors' spending at today's generosity (% GDP)"); print(spend.loc[YRS].round(2).to_string())
print("\nCut per senior to stay within envelope (%; combo envelope = 6.54 - R for the CCB)"); print(cut.loc[YRS].round(1).to_string())
print(f"\nAge cap effect on OADR: 2050 {oadr.p05[2050]-oadr.p05_age[2050]:.1f}, 2075 {oadr.p05[2075]-oadr.p05_age[2075]:.1f}, 2100 {oadr.p05[2100]-oadr.p05_age[2100]:.1f}")
