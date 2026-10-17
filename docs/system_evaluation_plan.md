# PresyoPH – System Evaluation Plan

*Member 2 (Data Scientist / Backend). Draft for team review.*

This plan covers the **System Evaluation** in Section IV of the proposal: internal testing of the dashboard for functional correctness, data display accuracy, and dashboard functionality, and a short structured walkthrough with representative users whose feedback is summarized qualitatively. Forecast accuracy (MAE, RMSE, MAPE) is the other half of Section IV and is already reported in `modeling_method_and_results.md`.

Where the proposal does not fix a detail (number of participants, session length, rating scale), the value here is marked **Proposed** for the team to confirm or change.

---

## 1. What is evaluated

| Proposal criterion | How it is checked | Section |
|---|---|---|
| Functional correctness | Automated tests, plus a checklist of every control on every screen | 2.1, 2.3 |
| Data display accuracy | Values on screen compared with PSA OpenSTAT and with the database | 2.2 |
| Dashboard functionality | Checklist per feature from Section III of the proposal | 2.3 |
| User acceptance (clarity, usefulness) | Structured walkthrough with representative users | 3 |

## 2. Internal testing (proponent team)

Run once the screens are complete, and again after any data refresh. The Forecasts screen can be tested now.

### 2.1 Automated tests

```
.venv/Scripts/python -m pytest
```

Requires MySQL running with `presyoph_db` imported (see the README). The suite currently has 58 tests: the backend functions every screen uses, the database loader, the forecasting outputs, and the Forecasts page rendering for every indicator and horizon. **Pass condition:** all tests pass.

### 2.2 Data display accuracy

Each value below is read off the dashboard and compared with two references: the PSA OpenSTAT table it came from, and the database. A value passes if it matches PSA to the published decimal place.

| # | Check | Expected (from `presyoph_db`) | PSA reference |
|---|---|---|---|
| D1 | National CPI, all items, Aug 2026 | 136.4 (Jul 2026: 135.6) | OpenSTAT CPI, 2018 = 100 |
| D2 | National CPI, all items, Jan 2018 | 97.2 | OpenSTAT CPI, 2018 = 100 |
| D3 | National inflation, all items, Aug 2026 | 6.1% (Jul 2026: 6.2%) | OpenSTAT inflation rate |
| D4 | Purchasing power of the peso, Aug 2026 | 0.73 | OpenSTAT purchasing power |
| D5 | Highest-inflation category, Aug 2026 | 07 – Transport, 13.5% | OpenSTAT inflation by commodity group |
| D6 | Highest regional inflation, Aug 2026 | Caraga and Davao Region, both 8.9% (tied) | OpenSTAT inflation by region |
| D7 | Lowest regional inflation, Aug 2026 | NCR, 4.1% | OpenSTAT inflation by region |
| D8 | FIES 2023, Philippines, all income groups | Income 314.82, expenditure 229.99, savings 84.83 (thousand pesos) | PSA FIES 2023 table |
| D9 | FIES 2023, Philippines, first and tenth decile income | 127.70 and 798.10 | PSA FIES 2023 table |
| D10 | Next-month CPI forecast (Sep 2026) | 136.9, 95% interval 135.8–138.0, ARIMA | `datasets/outputs/forecasts.csv` |
| D11 | Selected model and its metrics table | ARIMA; values match `datasets/outputs/metrics.csv` | `datasets/outputs/` |

Also check on every screen: units are labelled (index points, %, pesos, thousand pesos), dates show the correct month, and the PSA source is credited.

D6 is a useful edge case: two regions are tied, so the screen should not imply that one is strictly higher than the other.

### 2.3 Functional checklist

One row per feature in Section III of the proposal. Mark each check Pass / Fail / Not built, with a note for any failure.

**1. Cost-of-Living Trends** (CPI and inflation over time)
- [ ] CPI and inflation charts load for the national series
- [ ] Changing the date range updates the chart and summary values; the start and end months are included
- [ ] Choosing a region or a commodity group shows that series
- [ ] Inflation starts in January 2019, as in the proposal's inflation dataset

**2. Purchasing Power Analysis**
- [ ] Purchasing power chart loads, Jan 2018 – Aug 2026
- [ ] Values fall as CPI rises (purchasing power = 100 ÷ CPI)

**3. Regional Comparison**
- [ ] All 18 regions appear, with names that match PSA
- [ ] The ranking and the difference from the national value are correct for the chosen month and indicator
- [ ] Changing the indicator (CPI, inflation, purchasing power) updates the comparison

**4. Household Financial Overview** (FIES 2023)
- [ ] Income, expenditure and savings show by region and by income decile
- [ ] Deciles are in order, first to tenth
- [ ] The screen states that FIES is a 2023 snapshot and has no trend or forecast

**5. CPI Forecasting** (built)
- [ ] Indicator switch: CPI, inflation, purchasing power
- [ ] Horizon switch: 3, 6, 12 months
- [ ] "Show other models" adds the non-selected models to the charts
- [ ] Model comparison table: every evaluation period and error measure (MAE, RMSE, MAPE) can be selected, and ARIMA is marked as selected
- [ ] The forecast table opens and the CSV download contains the shown forecast
- [ ] "How the forecast was made" explains the data, models and selection rule

**6. Interactive Dashboard** (whole app)
- [ ] Every screen is reachable from the navigation
- [ ] Summary indicator cards show the latest values (D1, D3, D4) with the change from the previous month
- [ ] Filterable tables can be filtered by region, income group and time period, as the proposal lists
- [ ] With MySQL stopped, the app shows the "Cannot reach the presyoph_db database… Start MySQL in the XAMPP Control Panel" message rather than crashing silently
- [ ] Layout is usable on a laptop screen and a narrow browser window

## 3. User walkthrough

### 3.1 Participants

The proposal names three kinds of user: household members, a student or researcher, and a planner-type user.

**Proposed:** 5 participants: 2 household members (people who manage a household budget), 2 students or researchers, and 1 planner-type user (for example a small-business owner, barangay or LGU staff, or anyone who plans around regional prices). Recruit from the team's own contacts; no expertise is needed beyond the role.

### 3.2 Privacy and consent

In line with the proposal's data privacy section, no personal information is recorded. Each participant is identified only by a code and role (for example "P1 – household"). Before starting, tell them what the session is for, that the dashboard is being tested and not them, that they can stop at any time, and that only their comments will be summarized in the report, with no names.

### 3.3 Session format

**Proposed:** one person at a time, about 20–30 minutes, in person or by screen share. One team member facilitates and one takes notes. Ask the participant to think aloud. The facilitator does not help with tasks unless the participant is stuck for more than about two minutes; note when that happens.

1. Introduction and consent (2 min)
2. Free exploration: "Take a minute to look around. What do you think this tool is for?" (2–3 min)
3. Tasks (15–20 min). Give the tasks for the participant's role from 3.4; everyone does T1 and T4
4. Closing questions (5 min), from 3.5

### 3.4 Tasks

The tasks follow the two decisions the proposal says PresyoPH supports: household budgeting and regional planning. For each task, note whether it was completed, completed with help, or not completed, and anything the participant found confusing.

| # | For | Task | Answer (Aug 2026 data) |
|---|---|---|---|
| T1 | All | "How much have prices risen compared with a year ago?" | Inflation 6.1% |
| T2 | Household | "Which kind of spending has gone up the most?" | Transport, 13.5% |
| T3 | Household | "How much is one peso worth today compared with 2018?" | About ₱0.73 |
| T4 | All | "What are prices expected to do over the next 6 months, and how sure is the forecast?" | CPI rising to about 138.9 by Feb 2027; the participant should mention the range (interval) |
| T5 | Household | "Find how much a family in the lowest income group earns and saves in a year." | ₱127,700 income, ₱13,740 savings (2023) |
| T6 | Student / researcher | "Which forecasting model did the system choose, and why?" | ARIMA: lowest MAE, RMSE and MAPE |
| T7 | Planner | "Which regions have the highest inflation right now? Where does your own region stand?" | Caraga and Davao Region (8.9%); own region varies |
| T8 | Planner | "Compare inflation in your region with NCR over the past year." | Varies by region |

T5, T7 and T8 need screens that are not built yet; drop or adapt them if those screens change.

### 3.5 Closing questions

The proposal asks for feedback on **clarity** and **usefulness**, summarized qualitatively.

Clarity
1. Was anything confusing or hard to find? What?
2. Were the charts and numbers easy to understand? Which one was hardest?
3. Did you understand what the forecast range (interval) means?

Usefulness
4. Would you use this for [budgeting / your studies / planning]? For what, specifically?
5. What is missing that would make it more useful to you?
6. If you could change one thing, what would it be?

**Proposed (optional):** two 1–5 ratings, "How clear was the dashboard?" and "How useful would it be for you?", reported only as a supplement to the comments, since the proposal calls for a qualitative summary.

## 4. Recording and reporting

During each session the note-taker fills one row per task in a shared sheet: participant code, role, task, outcome (completed / with help / not completed), time if relevant, and a short note or quote.

For the report:
- **Internal testing:** the test suite result, the D1–D11 table with Pass/Fail, and the functional checklist with any failures and how they were fixed.
- **User walkthrough:** a table of task outcomes by role, then themes from the comments grouped under Clarity and Usefulness, each with one or two short quotes, and a list of changes made (or proposed) in response.

## 5. Open decisions for the team

- [ ] Confirm the number of participants and their mix (3.1)
- [ ] Confirm session length and format (3.3)
- [ ] Keep or drop the optional 1–5 ratings (3.5)
- [ ] Assign facilitator and note-taker for each session
- [ ] Set dates: internal testing after the remaining screens are built; walkthroughs after any fixes from internal testing
- [ ] Update the expected values in 2.2 and 3.4 if the data is refreshed past August 2026
