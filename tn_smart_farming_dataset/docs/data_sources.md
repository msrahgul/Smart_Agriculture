# Data Source Reference — all 15 datasets

Each entry lists: the real source, an **Access tier**, and what that tier means in practice.

- **Tier A — Bulk API/CSV, free registration required.** A real programmatic endpoint
  exists; you need a free account/API key, which I cannot create on your behalf.
- **Tier B — Public web portal, no bulk export.** Real, authoritative, government-published,
  but delivered as web pages or PDFs meant for one crop/district/report at a time. Getting
  a CSV out means scripted or manual extraction page-by-page.
- **Tier C — Restricted or specialist-tooling required.** Login-gated dashboards, or data
  that only exists as GIS/satellite layers needing tools like Google Earth Engine, not a
  flat file.

---

### 1. Crop Calendar — Tier B
**Source:** TNAU Crop Production Guides, published via the Tamil Nadu Agriculture Dept
portal — e.g. https://tnagriculture.in/dashboard/CPG/01_Rice.pdf (rice; the series is
numbered 01, 02, 03… by crop). Also cross-linked from the TNAU Agritech Portal
https://agritech.tnau.ac.in/.
**What's real here:** `datasets/crop_calendar.csv` is populated from the actual Rice guide —
7 agro-climatic zones × districts × season names (Kuruvai/Samba/Thaladi/Navarai etc.) with
real sowing months, extracted directly from the PDF above.
**To extend:** fetch `02_...pdf`, `03_...pdf` etc. from the same `dashboard/CPG/` path for
other crops (cotton, groundnut, sugarcane, maize, pulses) and repeat the extraction.

### 2. Crop Suitability — Tier B
**Source:** Same TNAU Agritech Portal / Crop Production Guides (climate requirement,
soil, duration are given at the top of each crop's guide, as seen in the Rice PDF: optimum
temp, rainfall range, soil type per crop). No bulk export; same page-by-page pattern as #1.

### 3. Soil Health — Tier C
**Source:** Soil Health Card portal (https://soilhealth.dac.gov.in) and NBSS&LUP soil maps.
The Soil Health Card portal is built around individual farmer/officer login and card
lookup, not a district/village bulk CSV export. NBSS&LUP data is distributed as GIS
shapefiles/maps, which need QGIS or similar, not a flat file. Realistic path: a formal
data request to TN Agriculture Dept or NBSS&LUP, not a web scrape.

### 4. Weather — Tier A (real endpoint, access unconfirmed)
**Source:** IMD's public API reference: https://api.imd.gov.in/public/api_reference.html —
documents real endpoints (current weather, 7-day city forecast, district nowcast, AWS/ARG
station data — state id 25 = Tamil Nadu). **Caveat, tested live:** a direct call to
`api.imd.gov.in/api/v1/aws_data?sid=25` returned HTTP 401 (unauthorized) even though the
docs don't mention a key requirement — so real access likely needs a token IMD issues on
request that isn't published on that page. `scripts/pull_imd_weather_rainfall.py` is
written against the documented schema and ready to run once you have that token, or once
you confirm the correct auth header with IMD.

### 5. Rainfall — Tier A/B mixed
**Source:** Same IMD API (`districtrainfall` endpoint — daily/weekly/monthly actual vs.
normal vs. % departure vs. category, exactly matching your schema) — same 401 caveat as
#4. Alternative: data.gov.in's rainfall catalog (https://www.data.gov.in/catalog/rainfall)
— note one of the specific monthly-grid resources I checked explicitly stated **"The API
for this resource does not exist"**, so not all rainfall resources there are API-backed;
check each resource page individually. Longer-term historical gridded rainfall (1951–2021)
is available from IMD Pune's National Climate Centre (https://www.imdpune.gov.in/lrfindex.php)
but that's a request-based archive, not a live API.

### 6. Irrigation — Tier C
**Source:** TNAU / TN-IAMWARM project publications, Agriculture Census. Delivered as
periodic PDF reports and project documentation, not a queryable dataset.

### 7. Fertilizer Recommendation — Tier B
**Source:** Same TNAU Crop Production Guides as #1/#2 — each guide has an explicit
"Nutrient Management" section with blanket N:P:K doses by zone/season, plus **STCR-IPNS
soil-test-based tables** for calculating fertilizer dose from actual soil N/P/K test
values. `datasets/fertilizer.csv` is populated from the real Rice guide (blanket doses by
zone and duration, e.g. Cauvery Delta short-duration dry season = 150:50:50 kg/ha
N:P₂O₅:K₂O).

### 8. Pest and Disease — Tier B
**Source:** Same TNAU Crop Production Guides, "Crop Protection" chapter (Pest Management /
Disease Management sections) — gives pest/disease name, scientific name, Economic
Threshold Level, and specific chemical controls with doses.
`datasets/pest_database.csv` and `datasets/disease_database.csv` are populated from the
real Rice guide.

### 9. Crop Yield — Tier A (registration needed) / B (fallback)
**Source:** Directorate of Economics & Statistics (DES), via data.gov.in catalog
"District-wise, season-wise crop production statistics" (area, production, by district/
crop/season/year) — https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0.
I could not confirm the exact `resource_id` for this specific dataset from outside
data.gov.in (its robots.txt blocks automated fetching, so I won't guess an ID — that would
risk a wrong/fabricated endpoint in the script). Look it up directly on that catalog page
after logging in — the resource_id sits in the "Data API" tab exactly like the Agmarknet
example in `pull_agmarknet_prices.py`. Fallback with no login: DES's own reporting tool at
https://data.desagri.gov.in/website/crops-apy-report-web or
https://aps.dac.gov.in/APY/Public_Report1.aspx (public web report, filterable by state/
district/year, not a raw bulk file).

### 10. Agricultural Market Price — Tier A (confirmed working pattern)
**Source:** Agmarknet, mirrored on data.gov.in as "Variety-wise Daily Market Prices of
Commodity." **Verified real `resource_id`: `9ef84268-d588-465a-a308-a864a43d0070`**
(confirmed against multiple independent developer write-ups referencing the same ID).
Real columns: State, District, Market, Commodity, Variety, Group, Arrivals (Tonnes),
Min/Max/Modal Price (Rs./Quintal), Reported Date.
`scripts/pull_agmarknet_prices.py` is ready to run — just needs your free data.gov.in API
key. **Column mapping:** the script writes raw API field names (state, district, market,
commodity, variety, grade, arrival_date, min/max/modal_price); `datasets/market_prices.csv`'s
stub header uses your originally-requested names (Market, District, Crop, Date, Minimum/
Maximum/Modal_Price, Market_Arrival_Quantity, Price_Trend) — map market→Market,
commodity→Crop, arrival_date→Date directly; Market_Arrival_Quantity isn't in this specific
resource (arrivals data lives in a separate Agmarknet series) and Price_Trend would need to
be computed downstream from the time series, not pulled directly.

### 11. Water Resources — Tier C
**Source:** India-WRIS (https://indiawris.gov.in) and TN Water Resources Department.
Reservoir/tank storage data is published as dashboards and periodic bulletins; I did not
find a confirmed open bulk API for this in the time available — treat as portal-only until
verified otherwise.

### 12. Groundwater — Tier C
**Source:** Central Ground Water Board (CGWB) and TN Groundwater Department. Groundwater
level data is published via CGWB's WRIS-linked dashboards and periodic (usually annual)
PDF reports by block/district; not a village-level bulk CSV in the open.

### 13. Crop Production — Tier A/B
Same source and same caveat as #9 (DES) — these two requested datasets are effectively the
same underlying data cut two ways (by season/crop vs. by district trend); one pull covers
both.

### 14. Satellite Agriculture (NDVI etc.) — Tier C
**Source:** ISRO Bhuvan, Sentinel-2, Landsat. This is fundamentally a raster-processing
pipeline (Google Earth Engine, Sentinel Hub, or Bhuvan's WMS/WCS services), not a
downloadable table — NDVI per lat/long/date has to be *computed* from satellite imagery,
not fetched as rows. Out of scope for a CSV-based approach; needs a GEE script if you want
to pursue this next.

### 15. Agro-Climatic Zone — Tier B (done)
**Source:** TNAU's own 7-zone classification, stated directly in the Crop Production
Guides (Cauvery Delta, North Eastern, Western, North Western, High Altitude/Nilgiris,
Southern, High Rainfall zones), each with its member districts.
`datasets/agro_climatic_zone.csv` is fully populated from this real, citable classification.
