"""
Riverside County Business Intelligence Dashboard
Standalone Dash app for Render.com deployment.
Data is fetched at startup from LEHD LODES + Census ACS — no local files needed.
"""

import os, io, warnings, json
import requests
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from sklearn.preprocessing import MinMaxScaler
import libpysal
from libpysal.weights import Queen, KNN
import esda
from esda.moran import Moran, Moran_Local
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go

warnings.filterwarnings('ignore')

# ── Configuration ────────────────────────────────────────────────────────────
STATE_FIPS  = '06'
COUNTY_FIPS = '06065'
COUNTY_CODE = '065'
LODES_YEAR  = 2021
ACS_YEAR    = 2021
LODES_BASE  = "https://lehd.ces.census.gov/data/lodes/LODES8/ca"

ACS_VARS = {
    'B19013_001E': 'median_income',
    'B01003_001E': 'total_pop',
    'B17001_002E': 'poverty_count',
    'B23025_004E': 'employed_civlabor',
    'B15003_022E': 'educ_bachelors',
    'B15003_023E': 'educ_masters',
    'B15003_024E': 'educ_professional',
    'B15003_025E': 'educ_doctorate',
}

SECTOR_LABELS = {
    'CNS01': 'Agriculture',       'CNS02': 'Mining/Oil',
    'CNS03': 'Utilities',         'CNS04': 'Construction',
    'CNS05': 'Manufacturing',     'CNS06': 'Wholesale Trade',
    'CNS07': 'Retail Trade',      'CNS08': 'Transportation/Warehouse',
    'CNS09': 'Information',       'CNS10': 'Finance/Insurance',
    'CNS11': 'Real Estate',       'CNS12': 'Professional Services',
    'CNS13': 'Management',        'CNS14': 'Admin/Support',
    'CNS15': 'Education',         'CNS16': 'Healthcare',
    'CNS17': 'Arts/Entertainment','CNS18': 'Accommodation/Food',
    'CNS19': 'Other Services',    'CNS20': 'Public Admin',
}

CENSUS_NULL_SENTINELS = [-666666999, -666666666, -999999999, -333333333]
CENSUS_API_KEY = os.environ.get('CENSUS_API_KEY', '')

# ── Data helpers ─────────────────────────────────────────────────────────────
def download_lodes(url, description):
    print(f"  Downloading {description}...")
    try:
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        df = pd.read_csv(
            io.BytesIO(r.content), compression='gzip',
            dtype={'w_geocode': str, 'h_geocode': str}
        )
        print(f"  {description}: {len(df):,} rows")
        return df
    except Exception as e:
        print(f"  Download failed ({description}): {e}")
        return None


# ── Main data pipeline ───────────────────────────────────────────────────────
def build_data():
    print("=" * 60)
    print("Building dashboard data...")

    sector_cols = list(SECTOR_LABELS.keys())

    # 1. WAC + crosswalk
    print("\n[1/6] LODES WAC + crosswalk")
    WAC_URL   = f"{LODES_BASE}/wac/ca_wac_S000_JT00_{LODES_YEAR}.csv.gz"
    XWALK_URL = f"{LODES_BASE}/ca_xwalk.csv.gz"

    df_wac_ca = download_lodes(WAC_URL, "LODES WAC (all CA)")
    r_xwalk   = requests.get(XWALK_URL, timeout=180)
    df_xwalk  = pd.read_csv(
        io.BytesIO(r_xwalk.content), compression='gzip',
        dtype={'tabblk2020': str, 'trct': str, 'cty': str, 'stplcfp': str}
    )
    print(f"  Crosswalk: {len(df_xwalk):,} blocks")

    riverside_blocks = df_xwalk[df_xwalk['cty'] == COUNTY_FIPS]['tabblk2020'].astype(str)
    rv_blocks_set    = set(riverside_blocks.values)
    df_wac = df_wac_ca[df_wac_ca['w_geocode'].isin(rv_blocks_set)].copy()

    # 2. Tract aggregation
    print("\n[2/6] WAC → tract aggregation")
    agg_cols = ['C000', 'CE01', 'CE02', 'CE03'] + sector_cols
    df_wac_xwalk = df_wac.merge(
        df_xwalk[['tabblk2020', 'trct']].rename(columns={'tabblk2020': 'w_geocode'}),
        on='w_geocode', how='left'
    )
    df_tract_jobs = (
        df_wac_xwalk.groupby('trct')[agg_cols].sum().reset_index()
        .rename(columns={
            'trct': 'GEOID', 'C000': 'total_jobs',
            'CE01': 'jobs_wage_low', 'CE02': 'jobs_wage_mid', 'CE03': 'jobs_wage_high'
        })
    )
    df_tract_jobs['dominant_sector'] = (
        df_tract_jobs[sector_cols].idxmax(axis=1).map(SECTOR_LABELS)
    )
    df_tract_jobs['dominant_sector_pct'] = (
        df_tract_jobs[sector_cols].max(axis=1)
        / df_tract_jobs['total_jobs'].clip(lower=1) * 100
    ).round(1)

    # 3. TIGER tract boundaries
    print("\n[3/6] TIGER tract boundaries")
    TIGER_URL   = "https://www2.census.gov/geo/tiger/GENZ2021/shp/cb_2021_06_tract_500k.zip"
    TIGER_LOCAL = "/tmp/ca_tracts.zip"
    r = requests.get(TIGER_URL, timeout=180)
    with open(TIGER_LOCAL, 'wb') as f:
        f.write(r.content)
    gdf_tracts    = gpd.read_file(f"zip://{TIGER_LOCAL}")
    gdf_rv_tracts = gdf_tracts[gdf_tracts['COUNTYFP'] == COUNTY_CODE].copy()
    gdf_rv_tracts = gdf_rv_tracts.to_crs(epsg=3857)
    gdf_rv_tracts['area_sqmi'] = gdf_rv_tracts.to_crs(epsg=32611).area / 2_589_988
    print(f"  Riverside tracts: {len(gdf_rv_tracts)}")

    # 4. Census ACS
    print("\n[4/6] Census ACS")
    BASE_URL   = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
    var_string = ','.join(ACS_VARS.keys())
    params = {
        'get': f'NAME,{var_string}',
        'for': 'tract:*',
        'in': f'state:{STATE_FIPS} county:{COUNTY_CODE}',
    }
    if CENSUS_API_KEY:
        params['key'] = CENSUS_API_KEY

    r      = requests.get(BASE_URL, params=params, timeout=60)
    data   = r.json()
    df_acs = pd.DataFrame(data[1:], columns=data[0])
    df_acs['GEOID'] = df_acs['state'] + df_acs['county'] + df_acs['tract']
    df_acs = df_acs.rename(columns=ACS_VARS)[['GEOID', 'NAME'] + list(ACS_VARS.values())].copy()
    for col in list(ACS_VARS.values()):
        df_acs[col] = pd.to_numeric(df_acs[col], errors='coerce')
        df_acs[col] = df_acs[col].replace(CENSUS_NULL_SENTINELS, np.nan)
        df_acs.loc[df_acs[col] < -10_000, col] = np.nan
    df_acs['poverty_rate']      = (df_acs['poverty_count']    / df_acs['total_pop'] * 100).round(1)
    df_acs['employment_rate']   = (df_acs['employed_civlabor'] / df_acs['total_pop'] * 100).round(1)
    df_acs['pct_bachelors_plus'] = (
        (df_acs['educ_bachelors'] + df_acs['educ_masters'] +
         df_acs['educ_professional'] + df_acs['educ_doctorate'])
        / df_acs['total_pop'] * 100
    ).round(1)

    # 5. Spatial join + derived metrics
    print("\n[5/6] Spatial join + derived metrics")
    for df in [gdf_rv_tracts, df_tract_jobs, df_acs]:
        df['GEOID'] = df['GEOID'].astype(str).str.zfill(11)

    gdf = (
        gdf_rv_tracts
        .merge(df_tract_jobs, on='GEOID', how='left')
        .merge(df_acs,        on='GEOID', how='left')
    )
    gdf['job_density']     = (gdf['total_jobs'] / gdf['area_sqmi'].clip(lower=0.01)).round(1)
    gdf['wage_quality_idx'] = (
        (gdf['jobs_wage_mid'] * 0.5 + gdf['jobs_wage_high'] * 1.0)
        / gdf['total_jobs'].clip(lower=1)
    ).round(3)

    gap_features = ['poverty_rate', 'job_density', 'median_income']
    gdf_gap = gdf[gap_features].copy().fillna(gdf[gap_features].median())
    scaler  = MinMaxScaler()
    scaled  = scaler.fit_transform(gdf_gap)
    gdf['opportunity_gap'] = (
        scaled[:, 0] + (1 - scaled[:, 1]) + (1 - scaled[:, 2])
    ) / 3 * 100
    gdf['opportunity_gap'] = gdf['opportunity_gap'].round(1)

    gdf_analysis = gdf[gdf['total_pop'] > 100].copy()

    # LISA
    try:
        gdf_proj = gdf_analysis.to_crs(epsg=32611)
        w = Queen.from_dataframe(gdf_proj)
        w.transform = 'r'
        y  = gdf_analysis['job_density'].fillna(0).values
        mi = Moran(y, w)
        lm = Moran_Local(y, w, permutations=499)

        sig  = lm.p_sim < 0.05
        quad_map = {1: 'HH (Hot Spot)', 2: 'LH (Spatial Outlier)',
                    3: 'LL (Cold Spot)', 4: 'HL (Spatial Outlier)'}
        gdf_analysis = gdf_analysis.copy()
        gdf_analysis['lisa_cluster'] = [
            quad_map.get(q, 'Not Significant') if s else 'Not Significant'
            for q, s in zip(lm.q, sig)
        ]
        lisa_i = mi.I
    except Exception as e:
        print(f"  LISA failed: {e} — skipping")
        gdf_analysis['lisa_cluster'] = 'Not Significant'
        lisa_i = 0.0

    # 6. Shift-share + OD commute
    print("\n[6/6] Shift-share + OD commute")
    rv_sector = df_tract_jobs[sector_cols].sum()
    rv_total  = df_tract_jobs['total_jobs'].sum()
    ca_sector = df_wac_ca[sector_cols].sum()
    ca_total  = df_wac_ca['C000'].sum()
    shift_data = []
    for col in sector_cols:
        E_i = rv_sector[col]
        r_i = ca_sector[col] / ca_total
        q_i = E_i / rv_total if rv_total > 0 else 0
        lq  = q_i / r_i if r_i > 0 else 0
        shift_data.append({
            'sector_code': col,
            'sector':      SECTOR_LABELS[col],
            'rv_jobs':     int(E_i),
            'rv_share_pct': round(q_i * 100, 2),
            'ca_share_pct': round(r_i * 100, 2),
            'location_quotient': round(lq, 3),
            'competitive_shift': round((q_i - r_i) * rv_total, 0),
            'lq_label': 'Concentrated' if lq > 1.2 else ('Average' if lq > 0.8 else 'Underrepresented')
        })
    df_shift = pd.DataFrame(shift_data).sort_values('competitive_shift', ascending=False)

    # OD commute
    OD_MAIN_URL = f"{LODES_BASE}/od/ca_od_main_JT00_{LODES_YEAR}.csv.gz"
    OD_AUX_URL  = f"{LODES_BASE}/od/ca_od_aux_JT00_{LODES_YEAR}.csv.gz"
    df_od_main  = download_lodes(OD_MAIN_URL, "OD Main")
    df_od_aux   = download_lodes(OD_AUX_URL,  "OD Aux")

    place_col  = [c for c in df_xwalk.columns if 'plc' in c.lower() or 'place' in c.lower()]
    name_col   = place_col[1] if len(place_col) > 1 else place_col[0]
    xwalk_city = df_xwalk[['tabblk2020', name_col]].copy()
    xwalk_city.columns = ['geocode', 'city_name']

    df_od_rv_workplace = df_od_main[df_od_main['w_geocode'].isin(rv_blocks_set)].copy()
    if df_od_aux is not None:
        df_od_rv_workplace = pd.concat(
            [df_od_rv_workplace, df_od_aux[df_od_aux['w_geocode'].isin(rv_blocks_set)]],
            ignore_index=True
        )
    df_od_rv_home = df_od_main[df_od_main['h_geocode'].isin(rv_blocks_set)].copy()

    df_inflow = (
        df_od_rv_workplace.rename(columns={'w_geocode': 'geocode'})
        .merge(xwalk_city, on='geocode', how='left')
        .groupby('city_name')['S000'].sum().reset_index()
        .rename(columns={'S000': 'jobs_inflow', 'city_name': 'city'})
    )
    df_outflow = (
        df_od_rv_home[~df_od_rv_home['w_geocode'].isin(rv_blocks_set)]
        .rename(columns={'h_geocode': 'geocode'})
        .merge(xwalk_city, on='geocode', how='left')
        .groupby('city_name')['S000'].sum().reset_index()
        .rename(columns={'S000': 'workers_outflow', 'city_name': 'city'})
    )
    df_commute = (
        df_inflow.merge(df_outflow, on='city', how='outer').fillna(0)
        .sort_values('jobs_inflow', ascending=False)
    )
    df_commute['net_flow']  = df_commute['jobs_inflow'] - df_commute['workers_outflow']
    df_commute['flow_type'] = np.where(df_commute['net_flow'] > 0, 'Net Importer', 'Net Exporter')
    df_commute_cities = df_commute[
        (df_commute['jobs_inflow'] + df_commute['workers_outflow']) > 1000
    ].head(20)

    # GeoJSON for Plotly choropleth
    gdf_dash = gdf_analysis.to_crs(epsg=4326).copy()
    gdf_dash['GEOID'] = gdf_dash['GEOID'].astype(str)
    for col in ['total_jobs', 'job_density', 'median_income', 'poverty_rate', 'opportunity_gap']:
        gdf_dash[col] = pd.to_numeric(gdf_dash[col], errors='coerce').fillna(0)
    geojson_dict = json.loads(gdf_dash[['GEOID', 'geometry']].to_json())

    print("\nData build complete.")
    return gdf_dash, geojson_dict, df_shift, df_commute_cities


# ── Build data once at startup ───────────────────────────────────────────────
gdf_dash, geojson_dict, df_shift, df_commute_cities = build_data()

# ── Dash app ─────────────────────────────────────────────────────────────────
server = app_server = None  # populated below for gunicorn

app = Dash(__name__, title="Riverside County BI Dashboard")
server = app.server  # expose Flask server for gunicorn

LAYER_OPTIONS = [
    {'label': 'Job Density (jobs/sq mi)',    'value': 'job_density'},
    {'label': 'Total Jobs',                  'value': 'total_jobs'},
    {'label': 'Median Household Income ($)', 'value': 'median_income'},
    {'label': 'Poverty Rate (%)',            'value': 'poverty_rate'},
    {'label': 'Opportunity Gap Score',       'value': 'opportunity_gap'},
]

app.layout = html.Div([
    # Header
    html.Div([
        html.H2("Riverside County Business Intelligence Dashboard",
                style={'color': 'white', 'margin': '0 0 4px 0', 'fontSize': '20px'}),
        html.P("Workforce, Industry & Opportunity Analysis | LEHD LODES + Census ACS 5-Year 2021",
               style={'color': '#cce4f7', 'margin': 0, 'fontSize': '12px'})
    ], style={'background': '#1a6ea8', 'padding': '14px 20px'}),

    # Controls
    html.Div([
        html.Div([
            html.Label("Map Layer:", style={'fontWeight': 'bold', 'fontSize': '12px'}),
            dcc.Dropdown(id='layer-select', options=LAYER_OPTIONS,
                         value='job_density', clearable=False,
                         style={'fontSize': '12px', 'width': '280px'})
        ], style={'marginRight': '30px'}),
        html.Div([
            html.Label("Top Cities (Commute Chart):", style={'fontWeight': 'bold', 'fontSize': '12px'}),
            dcc.Slider(id='city-slider', min=5, max=20, step=5, value=10,
                       marks={5: '5', 10: '10', 15: '15', 20: '20'})
        ], style={'width': '220px'})
    ], style={'display': 'flex', 'alignItems': 'center', 'padding': '12px 20px',
              'background': '#f0f4f8', 'borderBottom': '1px solid #ddd'}),

    # Top row: map + sector/commute charts
    html.Div([
        html.Div([dcc.Graph(id='choropleth-map', style={'height': '450px'})],
                 style={'width': '55%', 'paddingRight': '10px'}),
        html.Div([
            dcc.Graph(id='sector-bar',    style={'height': '215px'}),
            dcc.Graph(id='commute-chart', style={'height': '225px'}),
        ], style={'width': '45%'})
    ], style={'display': 'flex', 'padding': '12px 20px'}),

    # Bottom row: shift-share + opportunity scatter
    html.Div([
        html.Div([dcc.Graph(id='shift-share-chart',   style={'height': '280px'})],
                 style={'width': '50%', 'paddingRight': '10px'}),
        html.Div([dcc.Graph(id='opportunity-scatter', style={'height': '280px'})],
                 style={'width': '50%'})
    ], style={'display': 'flex', 'padding': '0 20px 20px 20px'}),

], style={'fontFamily': 'Arial, sans-serif', 'background': 'white'})


# ── Callbacks ────────────────────────────────────────────────────────────────
@app.callback(Output('choropleth-map', 'figure'), Input('layer-select', 'value'))
def update_map(layer):
    label_map    = {o['value']: o['label'] for o in LAYER_OPTIONS}
    color_scales = {
        'job_density': 'YlOrRd', 'total_jobs': 'YlOrRd',
        'median_income': 'Blues', 'poverty_rate': 'Reds',
        'opportunity_gap': 'RdYlGn_r'
    }
    fig = px.choropleth_mapbox(
        gdf_dash, geojson=geojson_dict,
        locations='GEOID', featureidkey='properties.GEOID',
        color=layer, color_continuous_scale=color_scales.get(layer, 'Viridis'),
        mapbox_style='carto-positron', zoom=8.5,
        center={'lat': 33.9, 'lon': -116.8}, opacity=0.7,
        hover_data={'total_jobs': True, 'median_income': True,
                    'dominant_sector': True, 'opportunity_gap': True},
        labels={layer: label_map.get(layer, layer)}
    )
    fig.update_layout(margin={'r': 0, 't': 30, 'l': 0, 'b': 0},
                      title_text=label_map.get(layer, layer),
                      title_x=0.01, title_font_size=13)
    return fig


@app.callback(Output('sector-bar', 'figure'), Input('layer-select', 'value'))
def update_sector_bar(_):
    top_sectors = df_shift.nlargest(10, 'rv_jobs')[['sector', 'rv_jobs', 'location_quotient']]
    fig = px.bar(
        top_sectors, x='rv_jobs', y='sector', orientation='h',
        color='location_quotient', color_continuous_scale='RdBu',
        color_continuous_midpoint=1.0,
        title='Top 10 Sectors by Employment',
        labels={'rv_jobs': 'Jobs', 'sector': '', 'location_quotient': 'LQ vs CA'}
    )
    fig.update_layout(margin={'t': 35, 'b': 5, 'l': 5, 'r': 5}, height=210, font_size=10)
    return fig


@app.callback(Output('commute-chart', 'figure'), Input('city-slider', 'value'))
def update_commute(n_cities):
    df_top = df_commute_cities.head(n_cities)
    fig = go.Figure()
    fig.add_bar(x=df_top['city'], y=df_top['jobs_inflow'],
                name='Jobs In (inflow)', marker_color='#1a6ea8')
    fig.add_bar(x=df_top['city'], y=df_top['workers_outflow'],
                name='Workers Out (outflow)', marker_color='#e07b34')
    fig.update_layout(
        barmode='group', title='Commuter Inflow vs Outflow by City',
        height=220, margin={'t': 35, 'b': 5, 'l': 5, 'r': 5},
        font_size=9, legend=dict(orientation='h', y=1.15)
    )
    return fig


@app.callback(Output('shift-share-chart', 'figure'), Input('layer-select', 'value'))
def update_shift(_):
    fig = px.bar(
        df_shift.sort_values('competitive_shift'),
        x='competitive_shift', y='sector', orientation='h',
        color='location_quotient', color_continuous_scale='RdYlGn',
        title='Shift-Share: Riverside Competitive Advantage',
        labels={'competitive_shift': 'Competitive Jobs (+/-)', 'sector': ''}
    )
    fig.add_vline(x=0, line_color='black', line_width=1)
    fig.update_layout(height=270, margin={'t': 35, 'b': 5, 'l': 5, 'r': 5}, font_size=9)
    return fig


@app.callback(Output('opportunity-scatter', 'figure'), Input('layer-select', 'value'))
def update_opportunity(_):
    fig = px.scatter(
        gdf_dash.dropna(subset=['median_income', 'opportunity_gap', 'total_jobs']),
        x='median_income', y='opportunity_gap',
        size='total_pop', color='poverty_rate',
        color_continuous_scale='Reds',
        hover_data=['NAME', 'dominant_sector', 'total_jobs'],
        title='Income vs. Opportunity Gap by Tract',
        labels={
            'median_income':    'Median Household Income ($)',
            'opportunity_gap':  'Opportunity Gap Score',
            'poverty_rate':     'Poverty Rate (%)'
        }
    )
    fig.update_layout(height=270, margin={'t': 35, 'b': 5, 'l': 5, 'r': 5}, font_size=9)
    return fig


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8051))
    app.run(debug=False, host='0.0.0.0', port=port)
