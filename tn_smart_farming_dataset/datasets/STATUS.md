| File | Status | Rows | Real source? |
|---|---|---|---|
| crop_calendar.csv | **Populated** | 18 | Yes — TNAU Rice Crop Production Guide |
| fertilizer.csv | **Populated** | 8 | Yes — TNAU Rice Crop Production Guide |
| pest_database.csv | **Populated** | 7 | Yes — TNAU Rice Crop Production Guide |
| disease_database.csv | **Populated** | 7 | Yes — TNAU Rice Crop Production Guide |
| agro_climatic_zone.csv | **Populated** | 7 | Yes — TNAU's own 7-zone classification |
| crop_suitability.csv | Header only | 0 | — see docs/data_sources.md #2 |
| soil_health.csv | Header only | 0 | — see docs/data_sources.md #3 |
| weather.csv | Header only | 0 | — see docs/data_sources.md #4 |
| rainfall.csv | Header only | 0 | — see docs/data_sources.md #5 |
| irrigation.csv | Header only | 0 | — see docs/data_sources.md #6 |
| crop_yield.csv | Header only | 0 | — see docs/data_sources.md #9 |
| market_prices.csv | Header only | 0 | — script ready, needs your data.gov.in API key |
| water_resources.csv | Header only | 0 | — see docs/data_sources.md #11 |
| groundwater.csv | Header only | 0 | — see docs/data_sources.md #12 |
| satellite_data.csv | Header only | 0 | — see docs/data_sources.md #14 |
| crop_production.csv | Header only | 0 | — see docs/data_sources.md #13 |
| master_farming_dataset.csv | Header only | 0 | Join target once component datasets are filled in |

All 5 "Populated" files cover **Rice only**, as the worked example. Extending to other
crops means repeating the same PDF-extraction pattern against the other TNAU Crop
Production Guides (see docs/data_sources.md #1).
