---
title: Riverside County BI Dashboard
emoji: 🗺
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Riverside County Business Intelligence Dashboard

**Spatial Workforce & Economic Analysis** | LEHD LODES 8 + Census ACS 5-Year | 2021

[![Live Demo](https://img.shields.io/badge/Live_Demo-HuggingFace-FFD21E?logo=huggingface&logoColor=000)](https://huggingface.co/spaces/darthsuvius/rv-bi-dashboard)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-0.14-139C5A?logo=python&logoColor=white)](https://geopandas.org)
[![Plotly Dash](https://img.shields.io/badge/Plotly_Dash-2.14-3F4F75?logo=plotly&logoColor=white)](https://dash.plotly.com)
[![ArcGIS Online](https://img.shields.io/badge/ArcGIS_Online-Embed-007AC2?logo=esri&logoColor=white)](https://www.arcgis.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

An end-to-end spatial business intelligence dashboard for **Riverside County, California** — the 4th largest county in the US by area, home to 2.4 million residents and one of the fastest-growing regional economies in Southern California.

This project integrates **LEHD LODES origin-destination job flow data** with **Census ACS 5-year demographic estimates** to produce four interconnected analyses at the Census tract level:

| # | Module | Method | Key Output |
|---|--------|--------|------------|
| 1 | Employment Density Mapping | Choropleth + Global Moran's I + LISA | HH/HL/LL/LH hotspot cluster map |
| 2 | Commuter Inflow/Outflow | LODES OD block-pair aggregation | Net importer vs. exporter cities |
| 3 | Shift-Share Industry Analysis | Location Quotient + competitive shift | Industry advantage vs. California |
| 4 | Opportunity Gap Score | MinMax composite (poverty + jobs + income) | Equity investment prioritization index |

All analysis is delivered through a **Plotly Dash interactive dashboard**, a standalone **Folium multi-layer HTML map**, and an **ArcGIS Online iframe embed** — bridging Python geospatial analysis with Esri enterprise GIS.

**Target employers:** RCTC · SCAG · Riverside County Economic Development Agency · Inland Empire cities

---

## Visualizations

### Employment Density + LISA Hotspot Clusters

![Employment Density and LISA Cluster Map](outputs/employment_lisa_map.png)

Global Moran's I = 0.247 (p = 0.001), confirming statistically significant spatial clustering of employment. Hot spots (HH) concentrate in the urbanized western corridor — Riverside, Moreno Valley, and the Coachella Valley core. Cold spots (LL) dominate the rural eastern desert.

---

### Opportunity Gap Score

![Riverside County Socioeconomic and Opportunity Analysis](outputs/opportunity_gap_map.png)

A composite index (0–100) ranking Census tracts by the mismatch between resident economic need and local job availability. Highest-gap tracts are concentrated in the Eastern Coachella Valley and parts of Moreno Valley — consistent with CalEnviroScreen 4.0 disadvantaged community designations.

---

### Shift-Share Industry Analysis

![Riverside County Shift-Share Analysis](outputs/shift_share_chart.png)

Transportation/Warehousing (LQ = 2.04) and Construction (LQ = 1.89) represent Riverside County's strongest competitive concentrations relative to California. Professional Services, Information, and Finance show significant structural underrepresentation — gaps that inform regional economic diversification planning.

---

## Pipeline

```
Raw Sources
    |
    +-- LEHD LODES8 WAC  --> Block-level jobs by sector + wage tier
    +-- LEHD LODES8 OD   --> Home <-> work block-pair flows
    +-- Census ACS 5-Year --> Tract-level demographics
    +-- TIGER Boundaries  --> Census tract polygons
            |
            v
    Spatial Join (GEOID 11-digit)
            |
            +-- Tract aggregation --> job_density, wage_quality_idx
            +-- Opportunity Gap Score (MinMax composite)
            +-- Queen weights -> Moran's I -> LISA clusters
            +-- OD city routing -> inflow / outflow / net flow
            +-- Location Quotient -> competitive shift (shift-share)
            |
            v
    Outputs
    +-- Plotly Dash app (5 interactive panels)
    +-- Folium HTML map (3 toggle layers)
    +-- Static Plotly HTML (GitHub Pages / portfolio)
    +-- GeoJSON export (ArcGIS Online upload)
```

---

## Key Findings

- **~650,000 total jobs** in Riverside County (LODES 2021 WAC)
- **Global Moran's I = 0.247** — statistically significant employment clustering (p = 0.001); jobs do not distribute randomly across the county
- **Top locally concentrated sectors (LQ > 1.2):** Transportation & Warehousing, Construction, Accommodation/Food — driven by the Inland Empire logistics corridor, residential growth boom, and regional hospitality demand
- **Net commute exporter cities** (bedroom communities): Jurupa Valley, Eastvale, Menifee — residents primarily commute to Los Angeles and Orange counties
- **Net commute importer cities** (employment centers): Riverside, Moreno Valley, Temecula
- **Highest opportunity gap tracts:** Eastern Coachella Valley and parts of Moreno Valley — high poverty, low job density, below-median income

---

## Deployment

The interactive dashboard is deployed on **Hugging Face Spaces** using Docker:

- **Live app:** https://huggingface.co/spaces/darthsuvius/rv-bi-dashboard
- **Runtime:** Python 3.11 · Gunicorn · Docker (CPU Basic — 2 vCPU, 16GB RAM)
- **Cold start:** ~2 minutes — the data pipeline fetches LODES + ACS live at startup; no local files required

To redeploy after changes:
```bash
git push hf main
```

---

## Outputs

| File | Description | How to View |
|------|-------------|-------------|
| `rv_county_bi_dashboard.html` | Standalone Plotly charts (no server) | Open in any browser / GitHub Pages |
| `rv_county_bi_dashboard_folium.html` | Interactive Folium map — 3 layer toggles | Open in any browser |
| `rv_county_tracts_portfolio.geojson` | Processed tract data for ArcGIS Online | Upload to arcgis.com → Map Viewer |
| `employment_lisa_map.png` | Static LISA + density map | GitHub README, reports |
| `shift_share_chart.png` | LQ + competitive shift chart | GitHub README, presentations |
| `opportunity_gap_map.png` | 3-panel socioeconomic map | GitHub README, reports |

---

## Data Sources

| Source | Dataset | Year | Access |
|--------|---------|------|--------|
| [LEHD LODES8](https://lehd.ces.census.gov/data/lodes/LODES8/) | WAC (workplace area characteristics), OD (origin-destination flows), geography crosswalk | 2021 | Direct `.csv.gz` download |
| [Census ACS 5-Year](https://api.census.gov) | Median income, poverty rate, employment, educational attainment by tract | 2021 | Census API (free, no key required) |
| [TIGER/Line (Census)](https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html) | California Census tract cartographic boundary shapefiles | 2021 | `zip://` download via GeoPandas |
| [ArcGIS Online](https://www.arcgis.com) | Interactive map embed (public MapViewer) | Live | iframe embed + ArcGIS Developer account |

All data sources are **free and publicly available** — no paid API keys required.

---

## Setup

### Option A — Conda (recommended for local development)

```bash
# 1. Clone the repository
git clone https://github.com/Suvamp/riverside-county-business-intelligence-dashboard.git
cd riverside-county-business-intelligence-dashboard

# 2. Create the environment from the YAML
conda env create -f environment.yml

# 3. Activate
conda activate rv-bi-dashboard

# 4. Launch JupyterLab
jupyter lab rv_bi_dashboard.ipynb
```

### Option B — Google Colab

1. Open [Google Colab](https://colab.research.google.com)
2. **File → Upload notebook** → select `rv_bi_dashboard.ipynb`
3. **Runtime → Change runtime type → Python 3** (GPU not required)
4. Run **Cell 2** — it auto-detects Colab and installs all dependencies
5. Run all cells top to bottom (`Runtime → Run all`)

> **Colab note for the Dash app (Cell 19):** After the server starts, run the following in a new cell to get the public URL:
> ```python
> from google.colab.output import eval_js
> print(eval_js("google.colab.kernel.proxyPort(8051)"))
> ```

### Environment Details

```yaml
name: rv-bi-dashboard
Python: 3.11
Key packages:
  conda-forge: geopandas, libpysal, esda, contextily, folium, scikit-learn, plotly
  pip:         dash, dash-leaflet, census
```

See [`environment.yml`](environment.yml) for pinned versions.

---

## Notebook Structure

```
rv_bi_dashboard.ipynb  (21 cells)
|
+-- PART 1: Setup (Cells 1-4)
|   +-- Cell 1  -- Project title (markdown)
|   +-- Cell 2  -- Colab installs
|   +-- Cell 3  -- All imports
|   +-- Cell 4  -- Configuration (FIPS, URLs, NAICS labels, colors)
|
+-- PART 2: Data Acquisition (Cells 5-8)
|   +-- Cell 5  -- LODES WAC download + crosswalk filter -> Riverside blocks
|   +-- Cell 6  -- Aggregate WAC blocks -> Census tracts
|   +-- Cell 7  -- TIGER cartographic boundary download
|   +-- Cell 8  -- Census ACS API pull (income, poverty, employment, education)
|
+-- PART 3: Feature Engineering (Cell 9)
|   +-- Cell 9  -- Spatial join (GEOID merge) + job_density + Opportunity Gap Score
|
+-- PART 4: Spatial Analysis (Cells 10-11)
|   +-- Cell 10 -- Global Moran's I + LISA (Queen weights, 999 permutations)
|   +-- Cell 11 -- Employment density + LISA choropleth map (matplotlib + contextily)
|
+-- PART 5: Commute Analysis (Cells 12-13)
|   +-- Cell 12 -- LODES OD download (main + aux files)
|   +-- Cell 13 -- City-level inflow / outflow / net flow
|
+-- PART 6: Shift-Share (Cells 14-15)
|   +-- Cell 14 -- Location Quotient + competitive shift (all 20 NAICS sectors)
|   +-- Cell 15 -- LQ bar chart + competitive shift visualization
|
+-- PART 7: Opportunity Gap (Cell 16)
|   +-- Cell 16 -- Three-panel map: poverty rate, job density, composite gap score
|
+-- PART 8: Interactive Maps (Cells 17-18)
|   +-- Cell 17 -- Folium multi-layer map (3 toggles, measure tool, fullscreen)
|   +-- Cell 18 -- GeoJSON export + ArcGIS Online iframe embed
|
+-- PART 9: Dashboard (Cells 19-20)
|   +-- Cell 19 -- Plotly Dash app (5 panels, 4 callbacks, Flask server)
|   +-- Cell 20 -- Standalone HTML export for GitHub Pages
|
+-- PART 10: Wrap-Up (Cell 21)
    +-- Cell 21 -- Portfolio README generator (populated with actual results)
```

---

## Dashboard Preview

### Plotly Dash — 5-Panel Interactive App

| Panel | Chart Type | Controlled By |
|-------|-----------|---------------|
| Choropleth Map | `px.choropleth_mapbox` — switchable layer | Layer dropdown |
| Top Sectors Bar | `px.bar` — employment by NAICS, colored by LQ | Auto-updates with map |
| Commuter Flow | `go.Figure` grouped bar — inflow vs. outflow | City count slider |
| Shift-Share | `px.bar` horizontal — competitive advantage/deficit | Static context |
| Income vs. Gap Scatter | `px.scatter` — income (x) vs. gap score (y), bubble = pop | Hover for tract details |

### Folium Map Layers

| Layer | Default | Description |
|-------|---------|-------------|
| Employment Density | On | YlOrRd choropleth, job density per sq mi, click for tract stats |
| LISA Clusters | Off | Red=HH hotspot, Blue=LL cold spot, standard LISA color convention |
| Opportunity Gap | Off | RdYlGn_r choropleth, composite gap score 0-100 |

---

## Methodology Notes

### Opportunity Gap Score

A composite index (0–100) identifying Census tracts with the greatest mismatch between resident economic need and local job availability. Computed as the mean of three MinMax-scaled components:

```
gap = mean([
    MinMax(poverty_rate),          # higher poverty = more gap
    1 - MinMax(job_density),       # lower job density = more gap
    1 - MinMax(median_income)      # lower income = more gap
]) x 100
```

This mirrors the composite scoring approach used in [CalEnviroScreen 4.0](https://oehha.ca.gov/calenviroscreen/report/calenviroscreen-40) for disadvantaged community identification.

### Location Quotient (Shift-Share)

```
LQ_i = (Riverside jobs in sector i / Total Riverside jobs)
       / (CA jobs in sector i / Total CA jobs)

LQ > 1.2  ->  Locally concentrated (potential cluster)
LQ < 0.8  ->  Underrepresented vs. state average
```

### LISA Cluster Classification

Uses Queen contiguity weights (row-standardized) with 999 Monte Carlo permutations at p < 0.05 significance threshold:

| Quadrant | Label | Meaning |
|----------|-------|---------|
| HH (q=1) | Hot Spot | High-job tract surrounded by high-job neighbors |
| LL (q=3) | Cold Spot | Low-job tract surrounded by low-job neighbors |
| HL (q=4) | Spatial Outlier | High-job tract in a low-job neighborhood |
| LH (q=2) | Spatial Outlier | Low-job tract in a high-job neighborhood |

---

## Industry Relevance

This project directly mirrors the analytical toolkit used by:

- **RCTC** — commute shed and jobs-housing balance studies use LODES OD flows; competitive shift analysis appears in economic nexus reports
- **SCAG** — shift-share and employment cluster mapping are standard Regional Transportation Plan deliverables
- **Riverside County EDA** — opportunity gap scoring supports SB 535 disadvantaged community identification and RHNA equity screening
- **Site selection firms** — Location Quotient analysis is a core suitability metric in commercial real estate targeting

---

## Adapting to Another County

Change three values in **Cell 4**:

```python
STATE_FIPS   = '06'      # California (always 06)
COUNTY_FIPS  = '06065'   # 06 + 3-digit county code
COUNTY_CODE  = '065'     # 3-digit county code only

# Examples:
# San Bernardino:  COUNTY_FIPS='06071', COUNTY_CODE='071'
# Los Angeles:     COUNTY_FIPS='06037', COUNTY_CODE='037'
# San Diego:       COUNTY_FIPS='06073', COUNTY_CODE='073'
```

All download functions, crosswalk filters, TIGER boundary filters, and ACS API calls read from these constants — nothing else needs changing.

---

## ArcGIS Online Integration

After running **Cell 18**:

1. Download `rv_county_tracts_portfolio.geojson` from `/tmp/`
2. Sign in to [arcgis.com](https://arcgis.com) → **Content → New Item → Your Device** → upload the GeoJSON
3. Open in **Map Viewer** → configure Smart Mapping renderer (Counts & Amounts → `job_density`)
4. **Share → Everyone (public)**
5. Copy the WebMap ID from the URL bar
6. In Cell 18, replace `YOUR_ARCGIS_ONLINE_ITEM_ID_HERE` with your ID and re-run

The ArcGIS Online map will render as a live iframe directly in the notebook output.

---

## Repository Structure

```
riverside-county-bi-dashboard/
+-- rv_bi_dashboard.ipynb               # Main analysis notebook (21 cells)
+-- environment.yml                     # Conda environment spec
+-- Dockerfile                          # Hugging Face Spaces deployment
+-- requirements.txt                    # Python dependencies
+-- README.md                           # This file
+-- outputs/
|   +-- rv_county_bi_dashboard.html         # Standalone Plotly dashboard
|   +-- rv_county_bi_dashboard_folium.html  # Interactive Folium map
|   +-- rv_county_tracts_portfolio.geojson  # ArcGIS Online upload file
|   +-- employment_lisa_map.png             # Static LISA cluster map
|   +-- shift_share_chart.png               # Shift-share visualization
|   +-- opportunity_gap_map.png             # Socioeconomic overlay maps
+-- docs/
    +-- rv_bi_dashboard_guide.docx          # Technical project guide
    +-- rv_bi_walkthrough_with_code.docx    # Step-by-step walkthrough
```

---

## License

[MIT License](LICENSE) — free to use, adapt, and share with attribution.

---

## Author

**Suvam Patel** | GIS Data Science Portfolio
GitHub: [@Suvamp](https://github.com/Suvamp)

*Built as part of a GIS Data Science portfolio targeting roles in regional planning, economic development, and urban analytics.*