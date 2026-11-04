"""Budget-neutral reallocation from seniors' spending to child benefits, and its demographic payoff, 2025-2100.

Policy: from 2027, public spending on people 65+ is reduced by R% of GDP and the same amount is added to the
Canada Child Benefit (CCB). The CCB paid $32.7B in July 2025-June 2026 (CRA), about 1.0% of GDP, so
R = 0.5% raises it by half and R = 1.0% doubles it.

Fertility response: long-run TFR rises by (1 + R/CCB)^e, phased in over 2028-2030 (births lag the policy).
e is the elasticity of fertility with respect to the level of child benefits:
  low 0.05     South Korea (10% benefit increase -> 0.3-0.6% more births), as summarized in Bokun (2024)
  central 0.12
  high 0.23    Germany (20% increase -> ~4.6%) and Hungary (1% -> ~0.2%), as summarized in Bokun (2024)
Short-run estimates overstate completed fertility because some births are only moved earlier; Cruces and
Rodriguez-Roman (2025) put the long-run effect at about half the short-run effect, so treat "high" as an
upper bound.

Everything else follows the current-plan scenario (M1 fertility path, 380k then 0.9% immigration, M1 NPR share).
After 2075, assumptions are extended unchanged (mortality keeps improving at the same rate). Illustrative only.
"""
import contextlib, io
import numpy as np
import pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import fiscal as f
import projection as pj
from projection import summarize

pj.END_YEAR = 2100
sc = f.sc
m, base_tfr, npr, plan = sc.m, sc.tfr, sc.npr, sc.plan
CCB = 1.0  # % of GDP

def tfr_with(R, e):
    mult = (1 + R / CCB) ** e
    def tfr(y):
        ramp = min(1.0, max(0.0, (y - 2027) / 3))   # 0 in 2027, full by 2030
        return base_tfr(y) * (1 + (mult - 1) * ramp)
    return tfr

def run(tfr):
    pops, imms, _ = m.run(tfr, plan, npr_share=npr)
    s = summarize(pops)
    s["dep_total"] = (s.young + s.old) / s.working * 100
    s["spend65"] = pd.Series({y: sum(f.shares(P, year=y)) for y, P in pops.items()})
    return s

base = run(base_tfr)
out = {"base": base}
for R in (0.5, 1.0):
    for lab, e in (("low", 0.05), ("central", 0.12), ("high", 0.23)):
        out[f"R{R}_{lab}"] = run(tfr_with(R, e))

YRS = [2025, 2030, 2040, 2050, 2060, 2075, 2090, 2100]
oadr = pd.DataFrame({k: v.oadr for k, v in out.items()})
spend = pd.DataFrame({k: v.spend65 for k, v in out.items()})
tot = pd.DataFrame({k: v.dep_total for k, v in out.items()})
oadr.round(3).to_csv("policy_oadr.csv"); spend.round(3).to_csv("policy_spend65.csv"); tot.round(3).to_csv("policy_dep_total.csv")

print("Long-run TFR by case:", {f"R{R} e={e}": round(1.32 * (1 + R / CCB) ** e, 3)
                                for R in (0.5, 1.0) for e in (0.05, 0.12, 0.23)})
print("\nOld-age dependency ratio"); print(oadr.loc[YRS].round(1).to_string())
print("\nTotal dependency ratio (0-14 and 65+ per 100 aged 15-64)"); print(tot.loc[YRS].round(1).to_string())
print("\nSpending on 65+ at today's generosity, % of GDP"); print(spend.loc[YRS].round(2).to_string())

# Payback: fiscal relief from a larger workforce vs the R% of GDP moved each year
print("\nFiscal relief (base minus policy, % of GDP) and first year relief >= R")
for R in (0.5, 1.0):
    for lab in ("low", "central", "high"):
        relief = spend["base"] - spend[f"R{R}_{lab}"]
        hit = relief[relief >= R].index.min()
        print(f"  R={R} {lab:<8} relief 2050 {relief[2050]:.2f}  2075 {relief[2075]:.2f}  2100 {relief[2100]:.2f}  break-even: {hit}")
print("\nPopulation 2100 (M):", {k: round(v.loc[2100, 'pop'] / 1e6, 1) for k, v in out.items()})
