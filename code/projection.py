"""Cohort-component projection of Canada's population, July 1 2025 to July 1 2075.

Single years of age 0-99 plus an open 100+ group, by sex, one-year steps.

Inputs (Statistics Canada):
  17-10-0005-01  Base population by single age and sex, July 1 2025
  13-10-0114-01  Life tables, 2022/2024 (Lx used for survival)
  13-10-0418-01  Age-specific fertility rates, 2025 (5-year groups, spread evenly to single ages)
  17-10-0014-01  International migration by age and sex (age profiles of immigrants, emigration, NPRs)
  17-10-0057-01  Official projections (scenario M1), used only to validate the model

Step from t to t+1:
  P[x+1, t+1] = P[x, t] * S[x, t] + M[x+1, t]
  Births B_t = sum over women of ASFR * average of female population at t and t+1; sex ratio 105 boys per 100 girls.
  Mortality improves at a constant exponential rate per sex, solved so life expectancy at birth hits a target in 2075.
  Net migration M = immigrants (rate or count, fixed age-sex profile) - net emigration (age-sex specific rates)
                  + net non-permanent residents (flow, fixed age-sex profile).
"""
import numpy as np
import pandas as pd

RAW = "raw"
AGES = np.arange(101)          # 0..99, 100 = 100+
SEXES = ["M", "F"]
SRB = 1.05                      # boys per girl at birth
BASE_YEAR, END_YEAR = 2025, 2075


def _age_index(label):
    label = label.replace("Under 1 year", "0 years")
    return int(label.split()[0])


def single_age_rows(df, col="Age group"):
    ok = df[col].str.fullmatch(r"(\d+ years?|Under 1 year|100 years and (older|over))")
    out = df[ok].copy()
    out["age"] = out[col].map(_age_index)
    return out


# ---------------------------------------------------------------- base population
def base_population(year=BASE_YEAR):
    p = pd.read_csv(f"{RAW}/17100005.csv", dtype=str, usecols=["REF_DATE", "GEO", "Gender", "Age group", "VALUE"])
    p = p[(p.GEO == "Canada") & (p.REF_DATE == str(year)) & p.Gender.isin(["Men+", "Women+"])]
    p = single_age_rows(p)
    p["VALUE"] = pd.to_numeric(p.VALUE)
    out = {}
    for g, s in [("Men+", "M"), ("Women+", "F")]:
        v = p[p.Gender == g].set_index("age").VALUE
        out[s] = v.reindex(AGES).fillna(0).values.astype(float)
    return out


# ---------------------------------------------------------------- mortality
def life_table_q(period="2022/2024"):
    lt = pd.read_csv(f"{RAW}/13100114_ca.csv", dtype=str)
    lt = lt[(lt.REF_DATE == period) & (lt.Element == "Death probability between age x and x+1 (qx)")]
    out = {}
    for sx, s in [("Males", "M"), ("Females", "F")]:
        v = lt[lt.Sex == sx].copy()
        v["age"] = v["Age group"].str.extract(r"(\d+)").astype(int)[0]
        out[s] = v.set_index("age").VALUE.astype(float).sort_index().values  # ages 0..110
    return out


def table_from_q(q):
    """Life table pieces from qx at ages 0..110 (last age closes the table)."""
    q = np.clip(q, 0, 1).copy()
    q[-1] = 1.0
    l = np.concatenate([[1.0], np.cumprod(1 - q)[:-1]])
    d = l * q
    a = np.full_like(q, 0.5)
    a[0] = 0.1
    L = l - d * (1 - a)
    L[-1] = l[-1] * 1.5            # crude closing for 110+
    T = L[::-1].cumsum()[::-1]
    return l, L, T


def e0(q):
    l, L, T = table_from_q(q)
    return T[0]


def survival_from_q(q):
    """Survival ratios for the projection: S[x] moves age x at t to x+1 at t+1; S[100] keeps 100+ in 100+.
    Also returns survival of births in year t to age 0 on July 1 t+1."""
    l, L, T = table_from_q(q)
    S = np.empty(101)
    S[:100] = L[1:101] / L[:100]
    S[100] = T[101] / T[100]
    s_birth = L[0]                 # radix 1
    return S, s_birth


def improvement_rate(q0, target_e0, years):
    lo, hi = 0.0, 0.05
    for _ in range(60):
        k = (lo + hi) / 2
        if e0(q0 * np.exp(-k * years)) < target_e0:
            lo = k
        else:
            hi = k
    return k


# ---------------------------------------------------------------- fertility
def asfr_single(year="2025"):
    f = pd.read_csv(f"{RAW}/13100418_ca.csv", dtype=str)
    f = f[(f.REF_DATE == year) & f.Characteristics.str.startswith("Age-specific")]
    rates = np.zeros(101)
    for _, r in f.iterrows():
        lo = int(r.Characteristics.split("females ")[1].split()[0])
        rates[lo:lo + 5] = float(r.VALUE) / 1000
    return rates  # sums to ~TFR/5*5 = TFR


# ---------------------------------------------------------------- migration profiles
def migration_profiles(years=("2017/2018", "2018/2019", "2019/2020", "2021/2022", "2022/2023",
                              "2023/2024", "2024/2025")):
    m = pd.read_csv(f"{RAW}/17100014_ca.csv", dtype=str)
    m = m[m.REF_DATE.isin(years) & m.Gender.isin(["Men+", "Women+"])]
    m = single_age_rows(m)
    m["VALUE"] = pd.to_numeric(m.VALUE)
    piv = m.pivot_table(index=["Type of migrant", "Gender", "age"], columns="REF_DATE", values="VALUE")

    pop = pd.read_csv(f"{RAW}/17100005.csv", dtype=str, usecols=["REF_DATE", "GEO", "Gender", "Age group", "VALUE"])
    pop = pop[(pop.GEO == "Canada") & pop.Gender.isin(["Men+", "Women+"])]
    pop = single_age_rows(pop)
    pop["VALUE"] = pd.to_numeric(pop.VALUE)

    prof = {}
    for g, s in [("Men+", "M"), ("Women+", "F")]:
        imm = piv.loc[("Immigrants", g)].reindex(AGES).fillna(0).sum(axis=1)
        net_em = piv.loc[("Net emigration", g)].reindex(AGES).fillna(0)  # emigrants - returning + net temporary
        # emigration rates: net emigrants at age x / population at age x (start of migration year)
        rate = []
        for y in years:
            pp = pop[(pop.Gender == g) & (pop.REF_DATE == y[:4])].set_index("age").VALUE.reindex(AGES).fillna(1)
            rate.append(net_em[y].values / pp.values)
        prof[s] = {"imm": imm.values, "em_rate": np.mean(rate, axis=0),
                   "npr": piv.loc[("Net non-permanent residents", g), "2022/2023"].reindex(AGES).fillna(0).values}
    # Age-sex structure of the NPR stock in 2025, built by following net NPR flows along birth cohorts
    # from 2016/17 to 2024/25 (most of today's NPR stock arrived in that window).
    flows = pd.read_csv(f"{RAW}/17100014_ca.csv", dtype=str)
    flows = single_age_rows(flows[(flows["Type of migrant"] == "Net non-permanent residents")
                                  & flows.Gender.isin(["Men+", "Women+"])])
    flows["VALUE"] = pd.to_numeric(flows.VALUE)
    for g, s in [("Men+", "M"), ("Women+", "F")]:
        stock = np.zeros(101)
        for yr in range(2016, 2025):
            f = flows[(flows.Gender == g) & (flows.REF_DATE == f"{yr}/{yr+1}")].set_index("age").VALUE.reindex(AGES).fillna(0).values
            stock = np.concatenate([[0], stock[:-1]]) + f   # age the stock one year, add the year's flow
        prof[s]["npr_stock"] = np.clip(stock, 0, None)
    tot_stock = prof["M"]["npr_stock"].sum() + prof["F"]["npr_stock"].sum()
    for s in SEXES:
        prof[s]["npr_dist"] = prof[s]["npr_stock"] / tot_stock
    tot_imm = prof["M"]["imm"].sum() + prof["F"]["imm"].sum()
    tot_npr = prof["M"]["npr"].sum() + prof["F"]["npr"].sum()
    for s in SEXES:
        prof[s]["imm_share"] = prof[s]["imm"] / tot_imm      # age-sex distribution of immigrants
        prof[s]["npr_share"] = prof[s]["npr"] / tot_npr      # age-sex distribution of NPR flows
    return prof


# ---------------------------------------------------------------- projection engine
class Model:
    def __init__(self, e0_2075=(87.5, 90.5), q_period="2022/2024"):
        self.P0 = base_population()
        self.q0 = life_table_q(q_period)
        mid = int(q_period[:4]) + 1
        self.k = {s: improvement_rate(self.q0[s], t, END_YEAR - mid) for s, t in zip(SEXES, e0_2075)}
        self.mid = mid
        self.asfr0 = asfr_single()
        self.tfr0 = self.asfr0.sum()
        self.mig = migration_profiles()

    def survival(self, s, year):
        return survival_from_q(self.q0[s] * np.exp(-self.k[s] * (year - self.mid)))

    def _step(self, P, NPR, y, I, tfr, npr_share, emigration):
        """Advance one year, July 1 y -> July 1 y+1, with I immigrants arriving during the year."""
        new = {}
        for s in SEXES:
            S, _ = self.survival(s, y)
            n = np.zeros(101)
            n[1:100] = P[s][:99] * S[:99]
            n[100] = P[s][99] * S[99] + P[s][100] * S[100]
            new[s] = n
        # births: ASFR scaled to the target TFR; exposure = same-age average of women on July 1 y and y+1
        fert = self.asfr0 * tfr(y) / self.tfr0
        B = (fert * (P["F"] + new["F"]) / 2).sum()
        for s, share in [("M", SRB / (1 + SRB)), ("F", 1 / (1 + SRB))]:
            _, sb = self.survival(s, y)
            new[s][0] = B * share * sb
        # immigrants and emigrants arrive/leave mid-year, so they are half a year older on July 1 y+1
        for s in SEXES:
            mig = self.mig[s]
            m = I * mig["imm_share"]
            if emigration:
                m = m - mig["em_rate"] * P[s]
            shifted = np.concatenate([[m[0] / 2], (m[:-1] + m[1:]) / 2])
            shifted[100] += m[100] / 2
            new[s] = np.maximum(new[s] + shifted, 0)
        NPR_new, flow = NPR, 0.0
        if npr_share is not None:
            aged = {}
            for s in SEXES:
                S, _ = self.survival(s, y)
                a = np.zeros(101)
                a[1:100] = NPR[s][:99] * S[:99]
                a[100] = NPR[s][99] * S[99] + NPR[s][100] * S[100]
                aged[s] = a
            sh = npr_share(y + 1)
            rest = sum(new[s].sum() - aged[s].sum() for s in SEXES)
            T = sh * rest / (1 - sh)              # stock such that T / (rest + T) = target share
            NPR_new = {}
            for s in SEXES:
                NPR_new[s] = T * self.mig[s]["npr_dist"]
                new[s] = np.maximum(new[s] - aged[s] + NPR_new[s], 0)
            flow = T - sum(aged[s].sum() for s in SEXES)
        return new, NPR_new, flow

    def run(self, tfr, immigrants, npr_share=None, emigration=True):
        """tfr(year) -> TFR.
        immigrants(year, P, probe) -> immigrants arriving between July 1 of year and year+1.
            probe(I) returns the population dict on July 1 year+1 if I immigrants arrive, so a callback
            can solve for the inflow that hits a target.
        npr_share(year) -> share of the population who are non-permanent residents on July 1 of year.
            The NPR stock keeps a fixed age-sex structure, so it is continually replenished at young ages
            while earlier NPRs age out (leave, or become immigrants).
        Returns (populations by year, immigrants by year, net NPR flow by year)."""
        P = {s: v.copy() for s, v in self.P0.items()}
        NPR = None
        if npr_share is not None:
            tot0 = sum(P[s].sum() for s in SEXES)
            NPR = {s: npr_share(BASE_YEAR) * tot0 * self.mig[s]["npr_dist"] for s in SEXES}
        out, imms, flows = {BASE_YEAR: P}, {}, {}
        for y in range(BASE_YEAR, END_YEAR):
            probe = lambda I, P=P, NPR=NPR, y=y: self._step(P, NPR, y, I, tfr, npr_share, emigration)[0]
            I = immigrants(y, P, probe)
            P, NPR, flows[y] = self._step(P, NPR, y, I, tfr, npr_share, emigration)
            imms[y] = I
            out[y + 1] = P
        return out, imms, flows


def summarize(res, retire_age=65):
    rows = []
    for y, P in res.items():
        tot = P["M"] + P["F"]
        ra = retire_age(y) if callable(retire_age) else retire_age
        lo = int(np.floor(ra))
        old = tot[lo + 1:].sum() + tot[lo] * (lo + 1 - ra)   # fractional threshold counts part of age lo
        work = tot[15:].sum() - old
        rows.append({"year": y, "pop": tot.sum(), "young": tot[:15].sum(), "working": work, "old": old,
                     "oadr": old / work * 100 })
    return pd.DataFrame(rows).set_index("year")


def oadr_from_counts(P, ra=65):
    tot = P["M"] + P["F"]
    return tot[ra:].sum() / tot[15:ra].sum() * 100
