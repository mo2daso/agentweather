# AgentWeather

A learning project to build an automated weather and air-quality forecasting system for Pakistan.

## Project status

Repository setup. Data collection, models, agents, and the dashboard are not implemented yet.

Target completion: **31 December 2026**. Submission deadline: **11 January 2027**.

## Planned cities

- Islamabad
- Karachi
- Lahore
- Faisalabad

Support for each city depends on verifying historical and live data coverage. We will complete one city's pipeline first, then extend it to the other cities.

## Forecast outputs

- Air Quality Index (AQI)
- Temperature (degrees Celsius)
- Precipitation amount and rain probability
- Relative humidity
- UV Index
- Wind speed and direction

The goal is a next-24-hour forecast display with explicit evaluation of the 24-hour-ahead horizon.

## Planned system

1. Collect historical and live weather and air-quality data.
2. Clean and align observations, then create model features.
3. Store observations and features in Hopsworks.
4. Compare statistical, classical machine-learning, and LSTM models against a daily seasonal baseline.
5. Use a LangGraph workflow for forecasting, alerts, weather reports, and drift monitoring.
6. Automate collection and training using GitHub Actions.
7. Deploy a public dashboard using free resources.

Data sources, free-tier limits, and historical coverage will be verified before modelling. Model forecasts and observed station measurements will be labelled separately.

## Learning and development

Work will progress through small, checked commits. Each stage combines implementation with explanations of the Python, data-science, and engineering concepts involved.

The next step is to inspect sample data and document coverage for all four candidate cities.

## Local files and secrets

API keys and credentials must stay out of Git. Local datasets, trained model files, and the supplied project PDF are ignored by default. Data access and regeneration instructions will be documented as the pipelines are implemented.

## Dashboard

Not deployed yet.
