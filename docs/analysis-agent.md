# Analysis Agent and Delay Prediction Model

The Analysis agent estimates the chance that a flight will be delayed, using a trained
flight delay model. It runs as a step in the LangGraph workflow
(`gate_availability` → `rule_engine` → `research_agent` → `analysis_agent` → `planning_agent`),
and its result is stored with the workflow, returned by the API and shown in the interface.

**Every number is an estimate** (`estimate: true`) for decision support. A person makes the
final decision.

## Two different risks

| Label in the interface | Source | Meaning |
|---|---|---|
| Operational risk score (rules) | Rule engine | Based on the current delay and status |
| Predicted delay risk (ML estimate) | Delay model | Chance of a future delay, predicted before departure |

## The model

- Training data: 444,127 completed US flights in 2023 (BTS) between ATL, ORD, DFW, DEN, JFK,
  LAX, SFO, SEA, MIA and BOS, joined with Open-Meteo weather.
- LightGBM classifier (delay above 15 minutes), LightGBM regressor (delay minutes) and an
  isotonic calibrator.
- Test result: ROC-AUC 0.66 on November and December flights the model never saw (moderate).
  Calibrated probabilities match the actual delay rate.
- Risk levels from the calibrated probability: Low below 0.15, Medium from 0.15, High from 0.30.

## Limitations

- US airports only, one year of data. Other airports and airlines still get an estimate, with a
  warning that it is less reliable.
- Forecast weather is less accurate than historical weather. If the forecast service is
  unavailable, the estimate uses historical patterns only and says so.
- Accuracy is moderate. Use it as decision support, not as a certainty.
- The previous-flight feature and retraining are not included.

## Code map

| File | Role |
|---|---|
| `backend/app/delay_model/` | Model package (`predictor.py`, `explain.py`, `weather_forecast.py`, `config.py`, `models/`) |
| `backend/app/agents/analysis_tools.py` | Validated delay tool with retry and logging. Never raises |
| `backend/app/agents/flight_mapper.py` | Converts a `flights` row into model input |
| `backend/app/agents/analysis_agent.py` | Builds the analysis result for up to 10 flights |
| `backend/app/agents/workflow.py` | `analysis_agent_node`, placed between research and planning |
| `backend/app/api/analysis.py` | The two delay estimate endpoints |
| `frontend/src/components/flight-operations/DelayEstimate.jsx` | Delay estimate panel |
| `frontend/src/components/flight-operations/AgentWorkflow.jsx` | Analysis step and results card |

## Set up

1. Python 3.13 and the packages in `backend/requirements.txt`. The model files only load with the
   training versions: lightgbm 4.7.0, scikit-learn 1.9.1, shap 0.53.0, joblib 1.6.0,
   pandas 3.0.6, numpy 2.5.4, holidays 0.106.
2. Copy the four model files (`clf.joblib`, `reg.joblib`, `calibrator.joblib`, `meta.joblib`)
   into `backend/app/delay_model/models/`. They are not in Git because of their size.
3. Create `backend/.env` with `JWT_SECRET_KEY=<any long random string>`. Never commit it.
4. Start the backend: `cd backend` then `uvicorn app.main:app --reload`.
5. Start the frontend: `cd frontend` then `npm install` and `npm run dev`.

If the model files are missing, the application still works: the estimate endpoints return
`503` with a clear message, and the workflow records an analysis result saying the model is
unavailable.

## API

All endpoints need a login. Any role (admin, operator, pilot) can read estimates.

| Endpoint | Purpose |
|---|---|
| `GET /api/flights/{flight_id}/delayestimate` | Estimate for one flight (database id or flight number). `404` flight not found, `422` flight cannot be converted, `503` model unavailable |
| `POST /api/analysis/delay-estimates` with `{"flight_numbers": [...]}` (1 to 10) | Analysis result for several flights |
| `POST /workflows/`, `GET /workflows/{id}` | Existing endpoints, now with `analysis_result` |

Analysis result fields: `flights_analysed`, `assessments` (per flight: `flight_id`, `route`,
`status`, `delay_probability`, `expected_delay_minutes`, `risk_level`, `top_factors`,
`warnings`, `weather_source`, `error`, `estimate`), `counts` (`High`, `Medium`, `Low`,
`failed`), `average_delay_probability`, `highest_risk` (up to 3 flights), `notes`,
`summary`, `summary_source` (`template`), `estimate`, `disclaimer`.

## Demo data

The model was trained on US flights, so demo with US flights between the 10 trained airports,
plus one outside example (HYD to DEL) to show the warnings. From `backend/`:

```
python seed_demo_user.py
python seed_demo_flights.py
```

`seed_demo_user.py` creates a local demo user (`tester`, role operator). It is for local
development only. The flights are dated two days ahead, so the weather forecast is available.

## Known gaps

- The summary always comes from the template, not from Gemini.
- Rule-engine findings are not added to the analysis notes.
- No audit log entry is written for analysis runs.
- Scheduled times are read as local airport times. When the two airports are in different time
  zones, the duration is estimated from the distance.