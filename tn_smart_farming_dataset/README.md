# Tamil Nadu Smart Farming AI Dataset — Starter Package

This is a **real, honestly-sourced starting point** for the full 15-dataset spec, not a
finished "complete dataset." Everything in `datasets/*.csv` that contains actual rows was
extracted from a named, linkable government/university source and is cited at the top of
the file. Every file that does **not** yet have real bulk data is a schema-only stub that
says so explicitly — nothing here is fabricated to look complete.

## What's actually in this package

| Folder | Contents |
|---|---|
| `docs/data_sources.md` | For all 15 datasets: the real source, whether it's bulk-API accessible / manual-portal / restricted, and exact URLs. Read this first. |
| `scripts/` | Working Python pullers for the two datasets that have genuine open bulk APIs (mandi prices, IMD weather/rainfall). Drop in a free API key and run. |
| `datasets/` | 16 CSVs matching your original spec. 5 are populated with real, cited Tamil Nadu / TNAU data (rice, as a worked example). The rest are header-only schema stubs with a sourcing note in row 1. |

## Why it isn't "complete" yet, honestly

Your spec asks for authentic-only data across 15 categories, all districts, down to village
level, with satellite layers — that's a multi-week data engineering project against a dozen
different government systems, several of which need registrations I can't create on your
behalf (data.gov.in API key), and a few of which have no bulk download at all (Soil Health
Card portal, CGWB groundwater viewer, ISRO Bhuvan/Sentinel-2 — these need GIS tools or
Google Earth Engine, not a CSV export). Filling every cell right now would mean inventing
numbers, which breaks the "no fabricated values" requirement you set. So instead: real
data where it's genuinely reachable, clear documentation of the path to get the rest, and
working code for the parts that are automatable.

## Next steps to actually fill this out

1. Register a free API key at https://data.gov.in (Sign Up → My Account → API Key) and drop
   it into `scripts/pull_agmarknet_prices.py`.
2. Repeat the TNAU Crop Production Guide extraction (see `docs/data_sources.md`) for the
   other ~20 crops in the series (rice was done manually here as the worked example) —
   this is straightforward but repetitive PDF extraction, good for a follow-up task.
3. For soil, groundwater, and satellite layers, the realistic path is contacting the
   relevant department (Soil Health Card portal / CGWB / NRSC-ISRO) for a data-sharing
   or bulk-export request, or using Google Earth Engine for the Sentinel-2/Landsat NDVI
   layer — none of these are one-click downloads even for government users.
