"""Chart: total public spending on seniors plus child benefits, % of GDP, with a dollar-for-dollar reallocation.

Total = spending on people 65+ (provincial health + OAS/GIS) + Canada Child Benefit (1.0% of GDP today).
Without reallocation: seniors at today's spending per senior, CCB at 1% of GDP.
With reallocation (from 2027): seniors' spending falls by 2% of GDP and the CCB rises by the same 2%, so total
spending is unchanged in the year of transfer. Any later difference comes only from the larger workforce
produced by higher fertility (more GDP per senior). Data: combo_spend65.csv (combo.py).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BLUE, ORANGE = "#1f77b4", "#c85a00"
plt.rcParams.update({"font.size": 10})
s = pd.read_csv("combo_spend65.csv", index_col="year")
CCB = 1.0
total = s + CCB          # reallocation moves 2% out of seniors and 2% into the CCB: net zero in each year
total.round(3).to_csv("chart3_total_spending_data.csv")

fig, ax = plt.subplots(figsize=(9.9, 6.2))
ax.plot(total.index, total["plan"], color="black", lw=2, label="Current plan, no reallocation")
ax.plot(total.index, total["p05_age"], color=ORANGE, lw=2, ls="-.", label="0.5% immigration, no immigrants 50+, no reallocation")
ax.fill_between(total.index, total["combo_high"], total["combo_low"], color=BLUE, alpha=0.18, lw=0,
                label="Range across fertility responses (elasticity 0.05 to 0.23)")
ax.plot(total.index, total["combo_central"], color=BLUE, lw=2,
        label="Same, + 2% of GDP moved from seniors to child benefits (central)")
for key, dy in [("plan", -7), ("p05_age", 0), ("combo_central", 7)]:
    ax.annotate(f"{total[key].iloc[-1]:.1f}%", (total.index[-1], total[key].iloc[-1]), xytext=(6, dy),
                textcoords="offset points", va="center", fontsize=9)
ax.set_xlim(2025, 2106)
ax.set_ylim(6, 15)
ax.set_ylabel("Public spending on people 65+ and child benefits\n(% of GDP)")
ax.set_xlabel("Year (July 1)")
ax.set_title("Total spending on seniors and child benefits, with a budget-neutral reallocation")
ax.legend(loc="upper left", fontsize=8.5)
fig.tight_layout()
fig.savefig("total-spending.png", dpi=110)
d = total["p05_age"] - total["combo_central"]
dh = total["p05_age"] - total["combo_high"]; dl = total["p05_age"] - total["combo_low"]
print("Saving vs same immigration without reallocation (pts of GDP), central [low, high]:")
for y in (2040, 2050, 2060, 2075, 2100):
    print(f"  {y}: {d[y]:.2f} [{dl[y]:.2f}, {dh[y]:.2f}]   totals: plan {total.plan[y]:.2f}, p05_age {total.p05_age[y]:.2f}, combo {total.combo_central[y]:.2f}")
