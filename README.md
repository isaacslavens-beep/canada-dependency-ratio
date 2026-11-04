# Canada's dependency ratio: data and code behind three charts

Three charts, the exact data plotted in each, the intermediate results, and the code to rebuild everything from public sources. These accompany the article *Canadian Demographic Sustainability* (November 2026) on [isaacslavens.com](https://isaacslavens.com).

The data collection, model and code were built with AI assistance (Claude). The research questions, scenarios and conclusions are my own. Everything here is published so the results can be checked independently.

## The charts

| Chart | Data plotted | Built by |
|---|---|---|
| `charts/1_required_inflow.png`: immigration needed to hold the old-age dependency ratio at its 2025 level | `data/chart1_required_inflow_data.csv` | `code/charts.py` |
| `charts/2_combined_policy.png`: dependency ratio to 2100 under a combined policy (0.5% immigration, no immigrants 50+, tripled child benefit) | `data/combo_oadr.csv` | `code/chart_combo.py` |
| `charts/3_total_spending.png`: total public spending on seniors plus child benefits, with a budget-neutral reallocation | `data/chart3_total_spending_data.csv` | `code/chart_total.py` |

The old-age dependency ratio (OADR) is people aged 65+ per 100 people aged 15-64.

## Key numbers

- OADR: 29.8 in 2025; 38.2 in 2050 and 45.6 in 2075 under the current immigration plan.
- Holding the OADR at 29.8 takes about 1.6M immigrants a year now and 2.8M a year by 2062; 77.5M in total over 2025-2074, for a population of 125M by 2075 (chart 1).
- Combined policy (0.5% immigration, no immigrants 50+, 2% of GDP moved from seniors to child benefits): OADR 38.7 in 2050, 48.2 in 2075 and 50.5 in 2100 in the central case, matching the current plan's 50.5 by 2100; in the high fertility case it matches by about 2070 and ends at 44.8. Range in 2100: 44.8 to 54.4. Population 53M in 2100 (range 49M to 60M), against 66M under the current plan (chart 2).
- Budget-neutral reallocation (chart 3): moving 2% of GDP from seniors' spending to child benefits leaves total spending unchanged when it happens. Later, the larger workforce lowers total spending on seniors plus child benefits, compared with the same immigration policy without the reallocation, by 0.8% of GDP in 2075 (range 0.3 to 1.5) and 1.65% in 2100 (range 0.7 to 3.0). Total spending reaches 12.4% of GDP in 2100 under the combined policy, against 12.3% under the current plan.

## Method in brief

**Projection model** (`code/projection.py`): cohort-component model, single years of age 0-100+ by sex, July 1 2025 onward. Statistics Canada inputs: 2025 population (17-10-0005), 2022/2024 life tables (13-10-0114), 2025 age-specific fertility (13-10-0418), migration by age (17-10-0014). Fertility, mortality and temporary-resident assumptions follow Statistics Canada's medium-growth scenario M1.

**Validation** (`code/validate.py`, `data/validation.csv`): with M1 assumptions the model reproduces Statistics Canada's official projection (17-10-0057) within 0.4% on population, and gives an OADR of 45.2 against StatCan's 45.1 in 2075. One number is calibrated (the 2025 temporary-resident share); everything after 2030 is out of sample.

**Scenarios** (`code/scenarios.py`): current plan is 380,000 a year to 2028, then 0.9% of population. The required inflow (chart 1) is solved each year as the smallest number of immigrants that keeps next year's OADR at or below 29.8 (the UN *Replacement Migration* method).

**Fiscal layer** (`code/fiscal.py`): provincial health spending by age (CIHI NHEX 2025, Series E1, 2023) plus OAS/GIS (Chief Actuary, 18th OAS Actuarial Report, 2023 totals), held constant relative to GDP per working-age person. OAS is deflated by 1% real wage growth to reflect price indexation, which reproduces the Chief Actuary's OAS path. Excess health cost growth is excluded, so health pressure is understated.

**Child benefit** (`code/policy.py`, `code/combo.py`): R% of GDP moved from seniors' spending to the Canada Child Benefit from 2027 (the CCB paid $32.7B in 2025-26, about 1% of GDP). The charts use R = 2%, which triples the CCB; R was chosen as the transfer at which the reduced-immigration policy matches the current plan by 2100 in the central case. Long-run fertility rises by (1 + transfer/CCB)^e, with e = 0.05 (low), 0.12 (central), 0.23 (high), from estimates summarized in Bokun (2024); phased in over 2028-2030. Assumptions after 2075 are extended unchanged.

**Combined policy** (`code/combo.py`): immigration phased linearly from 0.9% of population in 2028 to 0.5% in 2038; no immigrants aged 50+ (about 10% of the 2017-2025 intake), with their places reassigned proportionally to ages 0-49; plus the child benefit above at 2% of GDP.

**Total spending** (`code/chart_total.py`): spending on people 65+ at today's spending per senior (fiscal layer) plus the CCB at 1% of GDP. The reallocation subtracts 2% from seniors and adds 2% to the CCB, so it nets to zero each year; the only difference between lines comes from the age structure. Total net public spending is never cut.

## Limitations

- Moving 2% of GDP lowers spending per senior by about 29% relative to output per worker in 2027, falling to about 18% by 2075 as the senior population grows. It is a reallocation, not a net cut.
- The child benefit effect depends on a fertility response estimated in other countries, mostly from short-run studies of benefit increases of 10-50%. Tripling the CCB extrapolates well beyond that evidence, and the long-run effect may be smaller. The model ignores dilution of the benefit as births rise and the schooling and health costs of extra children.
- The immigrant age profile is fixed at the 2017-2025 average, apart from the age cap in the combined policy.
- These are mechanical projections, not forecasts.

## Rebuild from scratch

```
pip install pandas numpy matplotlib
cd code
python fetch_data.py      # Statistics Canada and FRED tables into raw/ (about 850 MB unzipped)
python validate.py
python scenarios.py
python fiscal.py
python combo.py
python charts.py && python chart_combo.py && python chart_total.py
```
The CIHI health spending extract is already included (`code/raw/cihi_e1_2023_canada.csv`); the full workbook is `nhex-2025-full-data-tables-en.zip` at cihi.ca/nhex. The scripts read and write in their own folder, and `charts.py`, `chart_combo.py` and `chart_total.py` save `required-inflow.png`, `combo-oadr.png` and `total-spending.png` (charts 1-3). To redraw the charts without rerunning the model, copy the `data/` CSVs into `code/` first.

## Sources

- Statistics Canada tables [17-10-0005-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000501) (population), [17-10-0014-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710001401) (migration by age), [13-10-0114-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310011401) (life tables), [13-10-0418-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1310041801) (fertility), [17-10-0057-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710005701) (projections)
- Statistics Canada, [Population Projections for Canada (2025 to 2075)](https://www150.statcan.gc.ca/n1/pub/17-20-0003/172000032026001-eng.htm)
- IRCC, [2026-2028 Immigration Levels Plan](https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/corporate-initiatives/levels.html)
- CIHI, [National Health Expenditure Trends 2025](https://www.cihi.ca/en/national-health-expenditure-trends), Series E1
- Office of the Chief Actuary, [18th Actuarial Report on the Old Age Security Program](https://osfi-bsif.gc.ca/en/oca/actuarial-reports/actuarial-report-18th-old-age-security-program-31-december-2021)
- Canada Revenue Agency, [Canada Child Benefit statistics, July 2025 to June 2026](https://www.canada.ca/en/revenue-agency/services/child-family-benefits/benefits-statistics/ccbstats2025-2026.html)
- FRED, [NGDPSAXDCCAQ](https://fred.stlouisfed.org/series/NGDPSAXDCCAQ) (Canada nominal GDP)
- Bokun (2024), [Cash transfers and fertility: Evidence from Poland's Family 500+ Policy](https://www.demographic-research.org/volumes/vol51/28/51-28.pdf), *Demographic Research* 51(28)
- Cruces and Rodriguez-Roman (2025), [Financial Incentives to Fertility: From Short to Long Run](https://frarodri.github.io/Papers/Cash%20transfers%20and%20fertility%20from%20short%20to%20long%20run.pdf)
- United Nations Population Division (2000), [*Replacement Migration*](https://digitallibrary.un.org/record/412547)
