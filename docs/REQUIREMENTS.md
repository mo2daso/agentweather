# Project requirements

This checklist follows the supplied AgentWeather brief and the mentor's clarification that any suitable documented dataset for a Pakistani city may be used. Data exploration does not complete the forecasting system.

Statuses: **Done** means implemented and checked; **Partial** means some work exists; **Pending** means not implemented.

| Requirement | Status | Evidence or next work |
| --- | --- | --- |
| Git repository with incremental work | Done | Source, documentation, and checks are versioned in GitHub |
| Pakistani city and documented data sources | Partial | Faisalabad; [dataset investigation](DATASET.md); acceptance remains conditional |
| Python implementation | Done | Collection and audit scripts use Python 3.11+ |
| Historical backfill | Partial | Monthly download and local audit; feature engineering and Hopsworks upload pending |
| Collect live weather and pollutant data hourly | Pending | Build ingestion with explicit source availability times |
| Fuse and time-align sources to one record per timestamp | Partial | Local historical UTC alignment; live fusion pending |
| Document and implement missing-data handling | Pending | Audit preserves gaps; choose rules after reviewing results |
| Time features: hour, day, month | Pending | Shared historical/live feature transformation |
| Rate-of-change and rolling-average features | Pending | Past-only transformations |
| Raw observations and features in Hopsworks Feature Store | Pending | Local files do not satisfy this requirement |
| Historical and live data use the same feature pipeline | Pending | Reuse transformations after source normalization |
| Targets shifted 24 hours ahead | Pending | Build target columns after quality decisions |
| Newest 24 hours used only for forecasting | Pending | Exclude unlabelled records from training |
| Thorough EDA for every metric | Partial | Coverage and quality audit; plots and relationships pending |
| Statistical model: SARIMAX or Prophet | Pending | Fit and evaluate |
| Classical model using scikit-learn | Pending | Ridge or Random Forest |
| LSTM using TensorFlow or PyTorch | Pending | Sequence construction, training, evaluation |
| Chronological train/validation split | Pending | Account for forecast horizon at split boundaries |
| Compare every model against daily seasonal naive baseline | Pending | Report scores by output and horizon |
| RMSE, MAE, R-squared for each required output | Pending | Add probability and angular metrics where appropriate |
| Hopsworks Model Registry | Pending | Save model artifacts and metadata |
| Promote new models only when validation improves | Pending | Define repeatable promotion policy |
| Daily and drift-requested training | Pending | GitHub Actions and guarded retraining trigger |
| Forecast all six groups, including rain probability and wind direction | Pending | Historical amount/direction columns alone are insufficient |
| Four agents in one LangGraph graph | Pending | Forecast, Alert, Weather Report, Drift |
| Shared state persists in Forecast Ledger | Pending | Save and restore state between runs |
| Forecast Agent hourly after ingestion | Pending | Load best registered models, save forecasts, pass state |
| Fixed hazard rules across all metric groups | Pending | Document threshold sources and check boundaries |
| Alerts for public, sensitive groups, outdoor workers | Pending | Audience-specific messages |
| Weather report daily and after a new alert | Pending | Ground report in forecast values and alerts |
| LLM API integration with proper fallbacks | Pending | Alert/report wording; deterministic fallback templates |
| Data drift: live versus training features | Pending | Reference windows, scores, thresholds |
| Model drift: recent forecast error versus validation error | Pending | Join matured forecasts to actual targets |
| Drift alerts team and requests extra training | Pending | Log action, notify configured destination, avoid repeated triggers |
| Every agent decision is logged | Pending | Include non-LLM actions, skipped steps, and failures |
| Forecast Ledger: time, metric, prediction | Pending | Also retain issue time, target time, model version |
| LLM logs: prompt, response, latency, status | Pending | Record failed calls in failure log |
| Drift logs: time, metric, type, score, threshold, action | Pending | Persist all required fields |
| All required logs stored in Feature Store | Pending | Local audit reports are not agent logs |
| GitHub Actions hourly ingestion | Pending | Scheduled and manually runnable workflow |
| Free-hosted public Streamlit or Gradio dashboard | Pending | Public URL in README when deployed |
| Dashboard shows 24-hour forecasts and weather report | Pending | Include all required outputs and update timestamps |
| Dashboard Agent Activity and alerts | Pending | Read persistent agent activity |
| Dashboard EDA and SHAP/LIME explanations | Pending | Implement explainability and views |
| Dashboard drift metrics/events and failed calls | Pending | Monitoring views |
| Final report: sources, imputation, models, issues/fixes | Partial | Dataset documentation started; final report pending |
| Final report: alert quality, drift detection, LLM failures | Pending | Evaluate and document real versus simulated evidence |
| Final submission is repository URL with dashboard URL and report inside | Pending | Verify end-to-end before submission |

## Source clarification

The pasted technology list names OpenWeather and AQICN. The PDF permits available sources, and the mentor explicitly allows any complete, sufficient dataset, including Open-Meteo. We are using that clarification for historical source selection. These APIs are not implemented or marked complete merely because they appear in the brief.

The brief mentions both the next 24 hours and a 24-hour-ahead target. The implementation plan retains explicit 24-hour-ahead evaluation and a next-24-hour dashboard. Neither is implemented yet.
