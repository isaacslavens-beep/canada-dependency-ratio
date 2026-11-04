"""Homepage charts, in the same plain matplotlib style as the existing debt-response charts."""
import contextlib, io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import scenarios as sc

BLUE, ORANGE, GRAY = "#1f77b4", "#c85a00", "#8c8c8c"
plt.rcParams.update({"font.size": 10})
oadr, runs, target = sc.oadr, sc.runs, sc.TARGET
yrs = oadr.index

# ---------------------------------------------------------------- Chart 1: OADR scenarios
fig, ax = plt.subplots(figsize=(9.9, 6.2))
series = [
    ("none", "No new permanent immigration", dict(color=GRAY, ls="--")),
    ("plan", "Current plan (380k, then 0.9% of pop.)", dict(color="black")),
    ("high", "High immigration (1.2% of pop.)", dict(color=BLUE)),
    ("plan_retire70", "Current plan + retirement age rises to 70", dict(color=ORANGE, ls="-.")),
]
for key, label, st in series:
    ax.plot(yrs, oadr[key], lw=2, label=label, **st)
    ax.annotate(f"{oadr[key].iloc[-1]:.0f}", (yrs[-1], oadr[key].iloc[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9)
ax.axhline(target, color="black", lw=1, ls=":")
ax.text(2026, target - 1.6, f"2025 level: {target:.1f}", fontsize=9)
ax.set_xlim(2025, 2078)
ax.set_ylim(20, 75)
ax.set_ylabel("People 65+ per 100 people aged 15-64")
ax.set_xlabel("Year (July 1)")
ax.set_title("Canada's old-age dependency ratio by scenario, 2025-2075")
ax.legend(loc="upper left", fontsize=8.5)
fig.tight_layout()
fig.savefig("dependency-scenarios.png", dpi=110)

# ---------------------------------------------------------------- Chart 2: required inflow
req = runs["required"][1]
plan = runs["plan"][1]
fy = req.index[:-1]                      # inflow during year t -> t+1
fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.9, 6.9), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
a1.bar(fy, req.immigrants.loc[fy] / 1e6, color=GRAY, width=0.8, label="Required to hold ratio at 2025 level")
a1.plot(fy, plan.immigrants.loc[fy] / 1e6, color="black", lw=2, label="Current plan")
peak = req.immigrants.loc[2045:].idxmax()
a1.annotate(f"{peak}: {req.immigrants[peak]/1e6:.1f}M ({req['imm_rate_%'][peak]:.1f}% of pop.)",
            (peak, req.immigrants[peak] / 1e6), xytext=(-250, -14), textcoords="offset points",
            fontsize=9, arrowprops=dict(arrowstyle="->", lw=0.8))
a1.set_ylabel("Permanent immigrants per year\n(millions)")
a1.set_title("Immigration required to keep the dependency ratio at its 2025 level")
a1.legend(loc="upper left", fontsize=8.5)

a2.plot(req.index, req["pop"] / 1e6, color="black", lw=2, label="Required path")
a2.plot(plan.index, plan["pop"] / 1e6, color="black", lw=1.2, ls="--", label="Current plan")
for s, lab in [(req, "Required path"), (plan, "Current plan")]:
    a2.annotate(f"{s['pop'].iloc[-1]/1e6:.0f}M", (s.index[-1], s["pop"].iloc[-1] / 1e6), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9)
a2.set_ylabel("Population\n(millions)")
a2.set_xlabel("Year")
a2.set_xlim(2024, 2079)
a2.legend(loc="upper left", fontsize=8.5)
fig.tight_layout()
fig.savefig("required-inflow.png", dpi=110)
c1 = pd.DataFrame({"required_immigrants": req.immigrants, "plan_immigrants": plan.immigrants,
                   "required_population": req["pop"], "plan_population": plan["pop"],
                   "required_oadr": req.oadr, "plan_oadr": plan.oadr})
c1.index.name = "year"
c1.round(1).to_csv("chart1_required_inflow_data.csv")
print("saved")
