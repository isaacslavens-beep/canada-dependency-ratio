"""Chart: combined policy (0.5% immigration, no immigrants 50+, tripled child benefit) vs current plan, to 2100."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BLUE, ORANGE, GRAY = "#1f77b4", "#c85a00", "#8c8c8c"
plt.rcParams.update({"font.size": 10})
o = pd.read_csv("combo_oadr.csv", index_col="year")

fig, ax = plt.subplots(figsize=(9.9, 6.2))
ax.plot(o.index, o["plan"], color="black", lw=2, label="Current plan (0.9% of pop.)")
ax.plot(o.index, o["p05"], color=GRAY, lw=2, ls="--", label="Phased down to 0.5% of pop. by 2038")
ax.plot(o.index, o["p05_age"], color=ORANGE, lw=2, ls="-.", label="0.5%, no immigrants aged 50+")
ax.fill_between(o.index, o["combo_low"], o["combo_high"], color=BLUE, alpha=0.18, lw=0,
                label="Range across fertility responses (elasticity 0.05 to 0.23)")
ax.plot(o.index, o["combo_central"], color=BLUE, lw=2,
        label="0.5%, no immigrants 50+, child benefit tripled (2% of GDP from seniors' spending, central)")
for key, dy in [("plan", -7), ("p05", 0), ("p05_age", 0), ("combo_central", 7)]:
    ax.annotate(f"{o[key].iloc[-1]:.1f}", (o.index[-1], o[key].iloc[-1]), xytext=(6, dy),
                textcoords="offset points", va="center", fontsize=9)
ax.set_xlim(2025, 2105)
ax.set_ylim(25, 65)
ax.set_ylabel("People 65+ per 100 people aged 15-64")
ax.set_xlabel("Year (July 1)")
ax.set_title("Dependency ratio under a combined policy, 2025-2100")
ax.legend(loc="upper left", fontsize=8.5)
fig.tight_layout()
fig.savefig("combo-oadr.png", dpi=110)
print("saved")
