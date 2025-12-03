# **Georgia Nurse Practitioner Workforce Mapping & Public Health Analysis**

This repository contains an interactive geospatial and statistical analysis platform for visualizing **nurse practitioner (NP) distribution across Georgia** and examining how NP supply relates to **county-level public health outcomes**. The project was developed through the **Center of AI Learning, Emory School of Nursing & AI.Data Lab (2025)**.

### **Scatterplot Generator**: https://kennardliong-ga-np-map-src02-county-correlations-emu8wd.streamlit.app/ 
### **Choropleth**: https://kennardliong-ga-np-map-srcapp-streamlit-chqn1j.streamlit.app/

---

## **📌 Features**

### **1. Interactive NP Workforce Map (Streamlit + Folium)**
- Choropleth map of NP count or NPs per 1,000 population.
- Filter by NP specialty or county.
- Hover tooltips showing NP totals and per-capita metrics.
- Built with Leaflet/Folium and Streamlit.

### **2. County-Level Scatterplot Explorer (Streamlit + Plotly)**
- Select any public health metric (e.g., depression %, uninsured %, overdose mortality).
- Compare NP count or NP-per-capita against selected metric.
- Interactive scatterplots with:
  - OLS regression trendline
  - R² value
  - Hover labels for each county

### **3. Data Cleaning Pipeline**
- Remove identifiers and irrelevant fields.
- Regex normalization of NP specialties.
- ZIP → county geocoding.
- Output: `npmaster.csv` (cleaned, de-identified dataset).

---

## **📂 Repository Structure**
```
ga-np-map/
│
├── data/
│   ├── npmaster.csv
│   ├── public_health_metrics_by_county.csv
│   ├── ga_counties.geojson
│   └── georgia-counties-by-population-(2025).csv
│
├── src/
│   ├── app_streamlit.py
│   ├── 02_County_correlations.py
│   └── utils/
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## **🔧 Installation**

Clone the repository:
```bash
git clone https://github.com/<your-username>/ga-np-map.git
cd ga-np-map
```

Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## **🚀 Running the App Locally**

### **Interactive NP Map**
```bash
streamlit run src/app_streamlit.py
```

### **Scatterplot Generator**
```bash
streamlit run src/02_County_correlations.py
```

Local host will open at:
```
http://localhost:8501
```

---

## **📊 Data Processing Pipeline**

### **1. Data Cleaning**
- Started with **14,467 NP records**.
- Removed identifiers and irrelevant fields.
- Standardized NP specialties via regex.
- Produced clean master dataset: `npmaster.csv`.

### **2. Geocoding**
- ZIP → Georgia county mapping.
- Validated lat/long.
- Assigned each NP to one of GA's 159 counties.

### **3. Mapping**
- Aggregated NPs per county.
- Computed NP-per-1,000 population where possible.
- Generated interactive Folium/Leaflet choropleths.

### **4. Public Health Linking**
- Loaded county-level public health metrics.
- Merged NP data via county FIPS.
- Built live scatterplots with OLS regression & R².

---

## **📈 Use Cases**
- **Workforce planning**: Identify NP and specialty shortages.
- **Public health research**: Explore NP supply vs. health outcome relationships.
- **Policy**: Inform allocation of providers or telehealth resources.
- **Education**: Support clinical rotation planning.

---

## **🌐 Streamlit Cloud Deployment**
1. Push repo to GitHub.
2. Go to: https://share.streamlit.io
3. Connect GitHub.
4. Select repo.
5. Choose script:
   - `src/app_streamlit.py` or `src/02_County_correlations.py`
6. Deploy.

---

## **📜 Acknowledgments**
Developed as part of the **Ai.Data Lab 2025** initiative in collaboration with:
- Emory School of Nursing
- Center for AI Learning
- Emory AI.Data Lab

---

## **📝 License**
MIT License 

