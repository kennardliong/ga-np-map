Georgia Nurse Practitioner Workforce Mapping & Public Health Analysis

This project analyzes the geographic distribution of nurse practitioners (NPs) across Georgia and explores how NP supply relates to county-level public health indicators.
It supports dynamic filtering by NP specialty, interactive geographic visualization, and county-level correlation analysis against health metrics (e.g., depression prevalence, uninsured %, chronic disease rates).

The project was developed through the Emory School of Nursing + Ai.Data Lab (2025).

📌 Features
1. Interactive NP Workforce Map (Streamlit + Folium)

Visualizes NP density across Georgia’s 159 counties

Filter by NP specialty and county

Supports two metrics:

NP Count

NPs per 1,000 population

Hover tooltips show county name, NP totals, and NP-per-capita metrics

Uses Leaflet/Folium choropleth maps for geographic clarity

2. County-Level Scatterplot Explorer (Streamlit + Plotly)

Load county public-health metrics

Choose any NP metric (count or per-capita)

Compare against any health metric (e.g., depression %, drug overdose mortality, uninsured %)

Produces real-time scatterplots with:

OLS trendline

R² value

Interactive hover labels

3. Full Data Cleaning Pipeline

Removes identifiers and irrelevant fields from the NPI dataset

Regex-standardizes NP specialty names

Geocodes each provider’s ZIP → county

Produces a clean npmaster.csv used across all analyses

📂 Repository Structure
ga-np-map/
│
├── data/
│   ├── npmaster.csv                             # cleaned NP dataset (no identifiers)
│   ├── public_health_metrics_by_county.csv      # county-level health indicators
│   ├── ga_counties.geojson                      # GA county boundaries
│   └── georgia-counties-by-population-(2025).csv
│
├── src/
│   ├── app_streamlit.py                         # main interactive choropleth web app
│   ├── 02_County_correlations.py                # county-level scatterplot generator
│   └── utils/                                   # optional helpers
│
├── requirements.txt
├── README.md
└── .gitignore

🔧 Installation

Clone the repo:

git clone https://github.com/<your-username>/ga-np-map.git
cd ga-np-map


Create and activate a virtual environment:

python3 -m venv .venv
source .venv/bin/activate


Install dependencies:

pip install -r requirements.txt

🚀 Running the App Locally
Interactive NP Map
streamlit run src/app_streamlit.py

Scatterplot Generator
streamlit run src/02_County_correlations.py


A local server will open at:

http://localhost:8501

📊 Data Processing Pipeline
1. Data Cleaning

Began with 14,467 NP records from the NPI Registry

Removed names, certification dates, addresses, taxonomy codes

Standardized NP specialties with regex + credential parsing

Output: Clean master dataset (npmaster.csv)

2. Geocoding

Converted practice ZIP codes to GA counties

Validated latitude/longitude bounds

Assigned each NP one of the 159 Georgia counties

3. Mapping

Aggregated NPs per county

Calculated NP-per-1,000-population using 2025 county population estimates

Rendered in Folium with dynamic filtering and tooltips

4. Public Health Linking

Loaded county-level health metrics (depression %, risk factors, access indicators)

Joined with NP metrics using county FIPS codes

Built live scatterplots with OLS trendlines and R²

📈 Use Cases
Healthcare Workforce Planning

Identify counties with NP shortages

Prioritize placement of specialty NPs (e.g., Psych/MH, Pediatrics)

Public Health Research

Explore associations between provider supply and health outcomes

Hypothesis generation for rural health equity studies

Policy & Administration

Support workforce distribution planning

Inform funding, training, and telehealth allocation strategies

Education / Clinical Programs

Show gaps where academic institutions may expand clinical rotations

Provide students with real-world geospatial analytics tools

🌐 Deploy on Streamlit Cloud

Push repo to GitHub

Visit: https://share.streamlit.io

Connect your GitHub account

Select this repo

Choose the main app script:

src/app_streamlit.py

Click Deploy

Streamlit will install all dependencies automatically.

📜 Acknowledgments

This project was completed as part of the Ai.Data Lab 2025 initiative in collaboration with:

Emory School of Nursing

Center for AI Learning

Emory AI.Data Lab

📝 License

MIT License
