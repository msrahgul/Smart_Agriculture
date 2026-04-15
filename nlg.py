"""
nlg.py – Natural Language Generator
Converts data dicts from data_engine into expert, conversational agricultural responses.
No external API. Pure Python template + contextual reasoning engine.
"""
import random

# ── Expert persona phrases ────────────────────────────────────
OPENERS = [
    "Based on the agricultural data I have for {district},",
    "Looking at the historical records for {district},",
    "From what our datasets tell us about {district},",
    "After analysing {district}'s agricultural profile,",
    "The data for {district} paints an interesting picture —",
]

CONNECTORS = [
    "What's particularly noteworthy is that",
    "Interestingly,",
    "It's also worth mentioning that",
    "On top of that,",
    "Another key insight is that",
    "Digging deeper into the data,",
]

CONCLUSIONS = [
    "Taking everything into account,",
    "Putting it all together,",
    "In summary,",
    "My recommendation, based on all this data, is that",
    "All things considered,",
]

HEDGES = [
    "Keep in mind this is based on historical trends up to 2019.",
    "As always, local conditions on the ground can vary.",
    "Note that on-farm conditions, pest pressure, and market prices should also factor into your final decision.",
    "This analysis draws from 20 years of district-level records — always validate with local agricultural officers.",
]


def _opener(district):
    return random.choice(OPENERS).format(district=district)

def _connector():
    return random.choice(CONNECTORS)

def _conclude():
    return random.choice(CONCLUSIONS)

def _hedge():
    return random.choice(HEDGES)


# ════════════════════════════════════════════════════════════
# 1. CROP RECOMMENDATION NLG
# ════════════════════════════════════════════════════════════
def describe_crops(district: str, crops_data: dict, rain_data: dict = None, irrigation_data: dict = None) -> str:
    if "error" in crops_data:
        return f"I wasn't able to find crop data for {district} with those filters. Could you double-check the district name or try without a soil or season filter?"

    crops = crops_data.get("crops", [])
    if not crops:
        return f"No crop records matched your query for {district}. Try broadening the search — for example, removing a soil type or season filter."

    soil_filter = crops_data.get("soil_filter", "all")
    season_filter = crops_data.get("season_filter", "all")

    # Keep best entry per crop
    seen = {}
    for c in crops:
        name = c["crop_name"]
        if name not in seen or c.get("rank_score", 0) > seen[name].get("rank_score", 0):
            seen[name] = c
    top = list(seen.values())[:5]

    paras = []

    intro_parts = [_opener(district)]
    if soil_filter != "all" and season_filter != "all":
        intro_parts.append(f"specifically for **{soil_filter}** during the **{season_filter}** season,")
    elif soil_filter != "all":
        intro_parts.append(f"when it comes to **{soil_filter}**,")
    elif season_filter != "all":
        intro_parts.append(f"focusing on the **{season_filter}** season,")
    else:
        intro_parts.append("when looking at overall crop performance,")
    paras.append(" ".join(intro_parts))

    top1 = top[0]
    top1_name = top1["crop_name"]
    top1_yield = top1["avg_yield"]
    top1_area = top1.get("area_ha", 0)
    top1_soil = top1["soil_type"].title()
    top1_season = top1["season"]

    paras.append(
        f"**{top1_name}** stands out as the strongest overall option, combining good historical yield, meaningful cultivation area, "
        f"and consistent presence in the records. In {district}, it averages **{top1_yield} tonnes per hectare** "
        f"on **{top1_soil}** during the **{top1_season}** season, with about **{top1_area:,} hectares** cultivated on average."
    )

    if len(top) >= 2:
        t2 = top[1]
        paras.append(
            f"{_connector()} **{t2['crop_name']}** is another strong choice, with an average yield of **{t2['avg_yield']} t/ha** "
            f"and around **{t2.get('area_ha', 0):,} ha** cultivated. That makes it a practical alternative for both commercial farming and crop rotation."
        )

    if len(top) >= 3:
        rest = [f"**{c['crop_name']}** ({c['avg_yield']} t/ha)" for c in top[2:5]]
        paras.append(f"Other promising crops in this environment include {', '.join(rest)}.")

    if rain_data and "error" not in rain_data:
        annual = rain_data.get("avg_annual_mm", 0)
        sw = rain_data.get("sw_monsoon_mm", 0)
        ne = rain_data.get("ne_monsoon_mm", 0)
        dominant = "Southwest Monsoon (June–September)" if sw > ne else "Northeast Monsoon (October–December)"
        paras.append(
            f"From a rainfall standpoint, {district} receives an average of **{annual} mm annually**, "
            f"with the {dominant} being the dominant rain source at **{max(sw, ne):.0f} mm**."
        )

    if irrigation_data and "error" not in irrigation_data:
        irr_pct = irrigation_data.get("irrigation_coverage_pct", 0)
        sources = irrigation_data.get("irrigation_sources", {})
        top_src = list(sources.keys())[0] if sources else None
        if top_src:
            paras.append(
                f"Irrigation coverage in {district} is **{irr_pct}%** of net sown area, with **{top_src}** as the primary water source. "
                f"{'This supports more flexible crop choices.' if irr_pct > 60 else 'So drought-tolerant or rainfall-aligned crops are safer choices.'}"
            )

    chosen_2 = top[1]['crop_name'] if len(top) > 1 else 'the crops listed above'
    paras.append(
        f"{_conclude()} if you're farming in {district}, starting with **{top1_name}** and **{chosen_2}** would be a sensible data-backed choice. "
        f"Final selection should still consider current market price, water availability, and local field conditions."
    )

    paras.append(f"*{_hedge()}*")

    table_lines = [
        "",
        "| Rank | Crop | Soil | Season | Avg Yield (t/ha) | Avg Area (ha) |",
        "|------|------|------|--------|-----------------|---------------|",
    ]
    for i, c in enumerate(top, 1):
        table_lines.append(
            f"| #{i} | **{c['crop_name']}** | {c['soil_type'].title()} | {c['season']} | {c['avg_yield']} | {c.get('area_ha', 0):,} |"
        )
    paras.append("\n".join(table_lines))

    return "\n\n".join(paras)



# ════════════════════════════════════════════════════════════
# 2. RAINFALL NLG
# ════════════════════════════════════════════════════════════
def describe_best_districts_for_crop(data: dict) -> str:
    if "error" in data:
        return f"Sorry, I don't have enough data to rank districts for that crop. {data['error']} Please check the crop spelling once or twice."

    crop = data.get("crop", "this crop")
    rows = data.get("districts", [])
    season_filter = data.get("season_filter", "all")
    if not rows:
        return f"I couldn't find district records for **{crop}**. Please check the crop spelling once or twice."

    top = rows[0]
    season_text = "" if season_filter == "all" else f" during **{season_filter}**"
    paras = [
        f"### Best Districts For {crop}",
        f"Based on historical yield, cultivated area, and record consistency, **{top['district']}** ranks strongest for **{crop}**{season_text}. It has an average yield of **{top['avg_yield']} t/ha**, with **{top['common_season']}** as the most common season in the records.",
    ]

    lines = ["", "| Rank | District | Avg Yield (t/ha) | Avg Area (ha) | Common Season | Common Soil |", "|------|----------|------------------|---------------|---------------|-------------|"]
    for idx, row in enumerate(rows, 1):
        lines.append(
            f"| #{idx} | **{row['district']}** | {row['avg_yield']} | {row['avg_area_ha']:,} | {row['common_season']} | {str(row['common_soil']).title()} |"
        )
    paras.append("\n".join(lines))
    paras.append("*This is based on historical district records, so final choice should also consider current water availability, market price, and local field conditions.*")
    return "\n\n".join(paras)


def describe_rainfall(district: str, data: dict) -> str:
    if "error" in data:
        return f"I couldn't find rainfall data for {district}. Please check the district name and try again."

    annual = data.get("avg_annual_mm", 0)
    sw = data.get("sw_monsoon_mm", 0)
    ne = data.get("ne_monsoon_mm", 0)
    hot = data.get("hot_weather_mm", 0)
    winter = data.get("winter_mm", 0)
    period = data.get("period", "historical period")
    trend = data.get("yearly_trend", [])

    # Classify rainfall level
    if annual > 1500:
        rain_class = "very high rainfall"
        rain_context = "This puts it among the wetter districts of Tamil Nadu, making it well-suited for water-intensive crops like rice and sugarcane."
    elif annual > 900:
        rain_class = "moderate to high rainfall"
        rain_context = "This is a comfortable range for most Tamil Nadu crops — rice, groundnut, and most pulses can be cultivated with minimal irrigation dependency."
    elif annual > 500:
        rain_class = "moderate rainfall"
        rain_context = "Farmers here typically rely on irrigation to supplement rain, especially for water-intensive crops like paddy and sugarcane."
    else:
        rain_class = "relatively low rainfall"
        rain_context = "Water management is critical in this district. Drought-tolerant crops like jowar, bajra, and millets are recommended for rain-fed farming."

    dominant = "Southwest Monsoon" if sw > ne else "Northeast Monsoon"
    dominant_mm = max(sw, ne)
    secondary = "Northeast Monsoon" if sw > ne else "Southwest Monsoon"
    secondary_mm = min(sw, ne)

    paras = [
        f"{_opener(district)} the rainfall pattern falls in the **{rain_class}** category, "
        f"averaging **{annual} mm per year** over the {period} period. {rain_context}"
    ]

    paras.append(
        f"The **{dominant}** is the dominant rainy season, contributing **{dominant_mm:.0f} mm** — "
        f"roughly {round(dominant_mm/annual*100) if annual else 0}% of the annual total. "
        f"The {secondary} brings in **{secondary_mm:.0f} mm**, which is "
        f"{'still significant for the post-kharif season crops.' if secondary_mm > 400 else 'relatively modest, so post-monsoon crops need supplemental irrigation.'}"
    )

    if hot > 0:
        paras.append(
            f"The hot weather season (March–May) contributes about **{hot:.0f} mm** of pre-monsoon showers, "
            f"{'which helps in early Kharif land preparation.' if hot > 100 else 'though this is minimal and farmers should plan for dry spells in spring.'}"
        )

    # Trend analysis
    if len(trend) >= 3:
        recent_3 = [r["total_mm"] for r in trend[-3:]]
        avg_recent = sum(recent_3) / len(recent_3)
        direction = "increasing" if recent_3[-1] > recent_3[0] else "declining"
        paras.append(
            f"{_connector()} looking at recent years, the rainfall trend appears to be **{direction}**. "
            f"The last three recorded years averaged **{avg_recent:.0f} mm**, "
            f"{'suggesting improving water availability.' if direction == 'increasing' else 'which calls for more careful water conservation planning.'}"
        )

        table_lines = [
            "",
            "| Year | Annual Rainfall (mm) |",
            "|------|---------------------|",
        ]
        for r in trend:
            table_lines.append(f"| {int(r['year'])} | {r['total_mm']} |")
        paras.append("\n".join(table_lines))

    paras.append(f"*{_hedge()}*")
    return "\n\n".join(paras)


# ════════════════════════════════════════════════════════════
# 3. WAGE NLG
# ════════════════════════════════════════════════════════════
def describe_wages(district: str, data: dict) -> str:
    if "error" in data:
        return f"I don't have wage data on record for {district}. It may be a newer district or the data wasn't available in the 2024–25 profile."

    wages = data.get("wages", {})
    year = data.get("year", "2024–25")

    if not wages:
        return f"Wage data for {district} appears to be incomplete in the 2024–25 district profile. I'd recommend checking with the Tamil Nadu Department of Agriculture directly."

    # Extract key wages
    plough = wages.get("Plough Men", "N/A")
    reapers_men = wages.get("Reapers Harvesters Men", "N/A")
    reapers_women = wages.get("Reapers Harvesters Women", "N/A")
    transplant_women = wages.get("Transplanters Weeders Women", "N/A")
    tractor = wages.get("Tractor Driver Men", "N/A")

    paras = [
        f"Here's what the **{year} district profile** tells us about agricultural wages in **{district}**."
    ]

    paras.append(
        f"For ploughing work, men earn **{plough}** per day, while tractor drivers command **{tractor}** — "
        f"reflecting the premium placed on mechanised operations. "
        f"{'This is competitive compared to state averages and suggests active mechanisation adoption in this district.' if tractor != 'N/A' else ''}"
    )

    if reapers_men != "N/A" or reapers_women != "N/A":
        gender_note = ""
        if reapers_men != "N/A" and reapers_women != "N/A":
            gender_note = f"There is a wage gap between male ({reapers_men}) and female ({reapers_women}) harvesters — a pattern common across Tamil Nadu that agricultural policy aims to address gradually."
        paras.append(
            f"For harvesting work, the daily rates are: men at **{reapers_men}** and women at **{reapers_women}**. {gender_note}"
        )

    if transplant_women != "N/A":
        paras.append(
            f"Women transplanters and weeders earn **{transplant_women}** per day — a critical role in paddy cultivation, and one that remains predominantly women's work in Tamil Nadu."
        )

    paras.append(
        f"{_connector()} these wages directly affect the cost of cultivation per acre. "
        f"For planning purposes, labour cost is typically **40–60% of total cultivation cost** for rice, and somewhat lower for mechanised crops like sugarcane."
    )

    table_lines = ["", "| Operation | Daily Wage (₹) |", "|-----------|--------------|"]
    for k, v in list(wages.items())[:8]:
        table_lines.append(f"| {k} | **{v}** |")
    paras.append("\n".join(table_lines))

    paras.append(f"*Data sourced from the Tamil Nadu District Profile 2024–25.*")
    return "\n\n".join(paras)


# ════════════════════════════════════════════════════════════
# 4. IRRIGATION NLG
# ════════════════════════════════════════════════════════════
def describe_irrigation(district: str, data: dict) -> str:
    if "error" in data:
        return f"Irrigation data for {district} wasn't available in my records. Please verify the district name."

    net_sown = data.get("net_area_sown_ha", "N/A")
    total_irr = data.get("total_irrigated_ha", "N/A")
    irr_pct = data.get("irrigation_coverage_pct", 0)
    sources = data.get("irrigation_sources", {})
    gw_avg = data.get("groundwater_avg_m", "N/A")
    gw_monthly = data.get("groundwater_monthly", {})

    # Irrigation assessment
    if irr_pct > 70:
        irr_level = "excellent irrigation infrastructure"
        irr_context = "This district has very good water access and can support intensive double or triple cropping systems."
    elif irr_pct > 40:
        irr_level = "moderate irrigation coverage"
        irr_context = "Farmers here have reasonable water access, though supplemental strategies like drip and sprinkler systems would help maximise productivity."
    else:
        irr_level = "limited irrigation coverage"
        irr_context = "Most farming here is rain-dependent. Investing in water harvesting structures and selecting drought-resilient crop varieties is strongly advisable."

    paras = [
        f"{district} has **{irr_level}**, with **{irr_pct}% of the net sown area** being irrigated. "
        f"Out of {net_sown} hectares under cultivation, {total_irr} hectares have assured irrigation access. {irr_context}"
    ]

    if sources:
        top_src, top_area = list(sources.items())[0]
        paras.append(
            f"The primary water source is **{top_src}** ({top_area}), "
            f"{'which is typical for districts with strong canal network from major rivers.' if 'canal' in top_src.lower() else 'which is characteristic of groundwater-dependent districts in Tamil Nadu.'}"
        )
        if len(sources) > 1:
            others = ", ".join([f"{k} ({v})" for k, v in list(sources.items())[1:4]])
            paras.append(f"Other sources include {others} — reflecting a diversified water access strategy.")

    # Groundwater
    if gw_avg != "N/A":
        gw_assessment = "healthy groundwater levels" if gw_avg < 5 else ("moderate depth" if gw_avg < 10 else "deep groundwater levels warranting conservation efforts")
        paras.append(
            f"Groundwater depth averages **{gw_avg} metres** across the year, indicating {gw_assessment}. "
            f"{'Shallow groundwater makes open-well and tube-well irrigation economically viable.' if gw_avg < 5 else 'Depth of this level increases pumping costs — efficient irrigation methods like drip are increasingly important.'}"
        )

    table_lines = ["", "| Irrigation Source | Area Irrigated |", "|-------------------|----------------|"]
    for src, area in sources.items():
        table_lines.append(f"| {src} | {area} |")
    paras.append("\n".join(table_lines))

    paras.append(f"*{_hedge()}*")
    return "\n\n".join(paras)


# ════════════════════════════════════════════════════════════
# 5. YIELD TREND NLG
# ════════════════════════════════════════════════════════════
def describe_yield_trend(district: str, crop: str, data: dict) -> str:
    if "error" in data:
        return f"I don't have yield trend data for **{crop}** in {district}. It's possible this crop isn't commonly cultivated there, or the name is slightly different. Try names like 'Rice', 'Groundnut', 'Sugarcane', 'Banana', or 'Cotton'."

    avg_yield = data.get("avg_yield_t_ha")
    best_year = data.get("best_year")
    best_yield = data.get("best_yield_t_ha")
    trend = data.get("trend", [])

    # Trend direction
    if len(trend) >= 4:
        first_half = sum(r["avg_yield_t_ha"] for r in trend[:len(trend)//2]) / (len(trend)//2)
        second_half = sum(r["avg_yield_t_ha"] for r in trend[len(trend)//2:]) / (len(trend) - len(trend)//2)
        trend_dir = "improving" if second_half > first_half * 1.05 else ("declining" if second_half < first_half * 0.95 else "stable")
        trend_pct = abs((second_half - first_half) / first_half * 100) if first_half else 0
    else:
        trend_dir = "limited data"
        trend_pct = 0

    paras = [
        f"Let me walk you through what the historical records say about **{crop}** cultivation in **{district}**."
    ]

    paras.append(
        f"Over the years in our dataset, {crop} has averaged **{avg_yield} tonnes per hectare** in this district. "
        f"The best recorded yield was **{best_yield} t/ha** in **{best_year}** — "
        f"{'an exceptional result that suggests the crop can thrive under ideal conditions here.' if best_yield > avg_yield * 1.5 else 'showing consistent performance across seasons.'}"
    )

    if trend_dir != "limited data" and trend_pct > 2:
        paras.append(
            f"{_connector()} over time, yields have been on a **{trend_dir}** trajectory — "
            f"{'rising by' if trend_dir == 'improving' else 'falling by'} roughly **{trend_pct:.1f}%** comparing earlier years to more recent ones. "
        )
        if trend_dir == "improving":
            paras.append("This upward movement likely reflects improved varieties, better agronomic practices, or more reliable irrigation access in recent years.")
        elif trend_dir == "declining":
            paras.append("The declining trend may point to soil exhaustion, changing rainfall patterns, or increasing pest pressure — this warrants attention from local agricultural authorities.")
        else:
            paras.append("Stable yields suggest consistent farming practices, though there may be room for improvement through better inputs and variety selection.")

    # Year range
    if trend:
        yr_start = int(trend[0]["year"])
        yr_end = int(trend[-1]["year"])
        paras.append(f"The data covers **{yr_start} to {yr_end}**, giving us a {yr_end - yr_start + 1}-year view of this crop's performance in {district}.")

    table_lines = ["", "| Year | Avg Yield (t/ha) |", "|------|-----------------|"]
    for r in trend:
        table_lines.append(f"| {int(r['year'])} | {r['avg_yield_t_ha']} |")
    paras.append("\n".join(table_lines))

    paras.append(f"*{_hedge()}*")
    return "\n\n".join(paras)


# ════════════════════════════════════════════════════════════
# 6. PEST RISK NLG
# ════════════════════════════════════════════════════════════
def describe_pest_risk(district: str, data: dict) -> str:
    if "error" in data:
        return f"I wasn't able to run pest risk analysis for {district}. Please verify the district name."

    risks = data.get("risks", [])
    annual = data.get("avg_annual_rain_mm", 0)
    sw = data.get("sw_monsoon_mm", 0)
    ne = data.get("ne_monsoon_mm", 0)
    dev = data.get("deviation_pct", "N/A")

    paras = [
        f"Let me give you a pest risk assessment for **{district}** based on its historical rainfall and climate profile."
    ]

    paras.append(
        f"The district receives about **{annual} mm annually**, with the Southwest Monsoon contributing **{sw:.0f} mm** "
        f"and the Northeast Monsoon **{ne:.0f} mm**. "
        f"{'High monsoon intensity creates humid conditions that are particularly favourable for fungal diseases and certain insect pests.' if max(sw,ne) > 800 else 'The moderate rainfall pattern limits some moisture-dependent pests, though dry spells can trigger a different set of risks.'}"
    )

    for risk in risks:
        sev = risk["severity"]
        pests = risk["pests"]
        crops = risk["crops_affected"]
        prevention = risk["prevention"]
        emoji = "🔴" if sev == "High" else ("🟡" if "Moderate" in sev else "🟢")

        paras.append(
            f"{emoji} **{sev} Risk — {', '.join(pests[:2])}{'...' if len(pests) > 2 else ''}**\n\n"
            f"Crops most at risk: **{', '.join(crops)}**.\n\n"
            f"*Recommended action:* {prevention}"
        )

    if dev != "N/A" and isinstance(dev, (int, float)):
        deviation_str = f"{'+' if dev >= 0 else ''}{dev}%"
        paras.append(
            f"{_connector()} Tamil Nadu's statewide rainfall deviation for this district's period is **{deviation_str}** from normal. "
            f"{'A positive deviation means surplus water — watch for waterlogging and fungal outbreaks.' if dev > 5 else ('A negative deviation indicates drier than normal conditions — water stress in crops can make them more vulnerable to sucking pests.' if dev < -5 else 'Rainfall is near normal levels, so standard seasonal pest management should suffice.')}"
        )

    paras.append(
        "**General advisory for Tamil Nadu:** Integrate pest management (IPM) is always recommended — combining biological controls, resistant varieties, and chemical use only as a last resort. The Tamil Nadu Agricultural University (TNAU) publishes district-specific pest calendars that are extremely useful."
    )

    return "\n\n".join(paras)


# ════════════════════════════════════════════════════════════
# 7. DISTRICT OVERVIEW NLG
# ════════════════════════════════════════════════════════════
def describe_overview(district: str, data: dict, rain_data: dict = None) -> str:
    if "error" in data:
        return f"I don't have a detailed profile for {district}. Please check the district name spelling."

    top_crops = data.get("top_5_crops", [])
    soil_types = data.get("soil_types", {})
    seasons = data.get("seasons", {})
    years = data.get("data_years", "historical period")
    total_area = data.get("total_area_ha", "N/A")
    net_sown = data.get("net_area_sown_ha", "N/A")
    total_irr = data.get("total_irrigated_ha", "N/A")

    paras = [
        f"Let me give you a comprehensive agricultural snapshot of **{district}**."
    ]

    # Land use
    paras.append(
        f"**{district}** covers a total geographical area of **{total_area} hectares**, with **{net_sown} ha** under active cultivation. "
        f"Of this, **{total_irr} ha** has irrigation access — giving us a broad picture of the district's farming intensity."
    )

    # Soil
    if soil_types:
        dominant_soil = max(soil_types, key=soil_types.get)
        paras.append(
            f"The dominant soil type is **{dominant_soil.title()}**, which shapes the crop selection significantly. "
            + {
                "alluvial soil": "Alluvial soils are extremely fertile and support a wide range of crops — from rice and sugarcane to banana and vegetables.",
                "black soil": "Black soil has excellent water retention, making it ideal for cotton, jowar, and groundnut cultivation.",
                "red soil": "Red soil is well-drained and iron-rich — well-suited for groundnut, millets, ragi, and pulses.",
                "clay soil": "Clay soils are dense and moisture-retentive, making them suitable for paddy, vegetables, and legumes.",
            }.get(dominant_soil, f"{dominant_soil.title()} soil supports diverse cultivation patterns.")
        )

    # Top crops
    if top_crops:
        top_names = [c["crop"] for c in top_crops[:3]]
        paras.append(
            f"Based on **{years}** of records, the highest-yielding crops in {district} are "
            f"**{top_names[0]}**, **{top_names[1] if len(top_names) > 1 else ''}** "
            f"{'and **' + top_names[2] + '**' if len(top_names) > 2 else ''}. "
            f"These crops have consistently outperformed in yield and area coverage."
        )

        table_lines = ["", "| Crop | Avg Yield (t/ha) |", "|------|-----------------|"]
        for c in top_crops:
            table_lines.append(f"| {c['crop']} | {c['avg_yield_t_ha']} |")
        paras.append("\n".join(table_lines))

    # Seasons
    if seasons:
        dom_season = max(seasons, key=seasons.get)
        paras.append(
            f"The **{dom_season}** season dominates agriculture here in terms of number of crop entries, "
            f"reflecting the agroclimate's natural alignment with {'the SW monsoon.' if dom_season == 'Kharif' else 'the NE monsoon and winter cultivation patterns.' if dom_season == 'Rabi' else 'year-round cultivation.'}"
        )

    # Rainfall
    if rain_data and "error" not in rain_data:
        annual = rain_data.get("avg_annual_mm", 0)
        paras.append(
            f"Rainfall averages **{annual} mm annually** — "
            f"{'ample for water-intensive crops.' if annual > 1200 else 'sufficient for most crops with proper water management.' if annual > 700 else 'on the lower side, making irrigation and water harvesting critical.'}"
        )

    paras.append(
        f"{_conclude()} {district} is "
        f"{'an agriculturally rich district with strong yield potential across multiple crop categories.' if top_crops and top_crops[0]['avg_yield_t_ha'] > 10 else 'a productive agricultural district with specific strengths in certain crop types.'} "
        f"For detailed farm planning, I'd recommend following up with rainfall queries, irrigation profiles, and specific crop recommendations using the options available."
    )

    return "\n\n".join(paras)


# ════════════════════════════════════════════════════════════
# 8. SOIL CLASSIFICATION NLG
# ════════════════════════════════════════════════════════════
SOIL_PROFILES = {
    "Alluvial soil": {
        "character": "extremely fertile, fine-grained, and moisture-retentive",
        "origin": "deposited by rivers over centuries",
        "best_crops": ["Rice", "Sugarcane", "Banana", "Wheat", "Jute"],
        "regions": "river delta and coastal districts",
        "advice": "This is among the most productive soil types in Tamil Nadu. You can aim for high-value crops and intensive double-cropping systems.",
    },
    "Black soil": {
        "character": "high clay content, swells when wet, cracks when dry, and retains moisture remarkably well",
        "origin": "formed from weathered volcanic basalt rock",
        "best_crops": ["Cotton", "Jowar", "Groundnut", "Sorghum", "Oilseeds"],
        "regions": "Coimbatore, Erode, and interior Tamil Nadu districts",
        "advice": "Black soil's moisture retention means it can sustain crops even during dry spells. However, waterlogging can be a problem — ensure good drainage before the rainy season.",
    },
    "Clay soil": {
        "character": "dense, compacted, and slow-draining, but nutrient-rich when properly managed",
        "origin": "fine mineral particles formed through long-term weathering",
        "best_crops": ["Paddy", "Vegetables", "Legumes", "Horsegram"],
        "regions": "widely distributed across Tamil Nadu",
        "advice": "Clay soil needs careful water management. Tillage before planting is important to break compaction. Adding organic matter (compost) significantly improves its structure and drainage.",
    },
    "Red soil": {
        "character": "well-drained, iron and aluminium-rich, and relatively poor in moisture retention",
        "origin": "weathered from ancient crystalline rocks under high temperature and leaching",
        "best_crops": ["Groundnut", "Ragi", "Small Millets", "Pulses", "Castor"],
        "regions": "widely across interior Tamil Nadu — Salem, Dharmapuri, Vellore",
        "advice": "Red soil needs regular organic matter additions and is best suited to drought-tolerant crops. With mulching and drip irrigation, productivity can be significantly improved.",
    },
}

def describe_soil(soil_type: str, district: str = None, crop_data: dict = None) -> str:
    profile = SOIL_PROFILES.get(soil_type, None)

    if not profile:
        return f"I detected **{soil_type}** from the image, though I don't have a detailed profile for this type. Speak to your local soil testing laboratory for a precise nutrient analysis."

    crops_str = ", ".join(f"**{c}**" for c in profile["best_crops"][:4])
    paras = [
        f"From the image you uploaded, I've identified this as **{soil_type}**."
    ]

    paras.append(
        f"This soil is {profile['character']}. It forms by {profile['origin']}, and is commonly found in the {profile['regions']} of Tamil Nadu."
    )

    paras.append(
        f"Crops that historically perform best on {soil_type} include {crops_str}, and in some conditions, {', '.join(f'**{c}**' for c in profile['best_crops'][4:])}."
        if len(profile["best_crops"]) > 4
        else f"Crops that perform best on {soil_type} include {crops_str}."
    )

    paras.append(f"**My advice:** {profile['advice']}")

    if district and crop_data and "error" not in crop_data:
        crops = crop_data.get("crops", [])
        if crops:
            top_crop = crops[0]["crop_name"]
            top_yield = crops[0]["avg_yield"]
            paras.append(
                f"Cross-referencing with {district}'s data: **{top_crop}** is the top-yielding crop on this soil type in your district, "
                f"averaging **{top_yield} t/ha**. This strongly supports cultivating it on this field."
            )

    paras.append("*For the most precise recommendations, a laboratory soil test for pH, NPK levels, and micronutrients is always the best starting point.*")
    return "\n\n".join(paras)


# ════════════════════════════════════════════════════════════
# 9. SUITABILITY SCORE NLG
# ════════════════════════════════════════════════════════════
def describe_fertilizer(data: dict) -> str:
    if "error" in data:
        return f"I couldn't prepare a fertilizer recommendation: {data['error']} Please check the crop name once or twice."

    crop = data.get("crop", "this crop")
    district = data.get("district")
    soil = data.get("soil_type")
    season = data.get("season")
    cost = data.get("estimated_fertilizer_cost_per_acre", {})
    context_bits = []
    if district:
        context_bits.append(f"in **{district}**")
    if soil:
        context_bits.append(f"on **{soil}**")
    if season:
        context_bits.append(f"during **{season}**")
    context = " ".join(context_bits)

    paras = [
        f"### Fertilizer Recommendation — {crop}{(' ' + context) if context else ''}",
        data.get("baseline", "Use a balanced nutrient plan based on soil testing."),
        f"**Organic support:** {data.get('organic', 'Add compost or farmyard manure before sowing where available.')}",
        f"**Important caution:** {data.get('caution', 'Avoid over-application and follow local soil-test recommendations.')}",
    ]

    if cost:
        paras.append(
            f"Estimated fertilizer input cost is roughly **₹{cost.get('min', 0):,}–₹{cost.get('max', 0):,} per acre**, depending on current input prices and soil condition."
        )

    paras.append("*Use this as planning guidance only. A local soil test is still the best way to decide exact fertilizer quantity.*")
    return "\n\n".join(paras)


def describe_planting_time(data: dict) -> str:
    if "error" in data:
        return f"I couldn't find a reliable planting-time record for that crop. {data['error']} Please check the crop spelling once or twice."

    crop = data.get("crop", "this crop")
    district = data.get("district")
    best_season = data.get("best_season", "the locally suitable season")
    best_months = data.get("best_months", "the locally recommended sowing window")
    note = data.get("note")
    summary = data.get("season_summary", [])

    place = f" in **{district}**" if district else " in Tamil Nadu records"
    paras = [
        f"### Best Time To Grow — {crop}{place}",
        f"The best season for **{crop}**{place} is **{best_season}**.",
        f"**Best month/window:** {best_months}",
    ]

    if note:
        paras.append(f"**Practical note:** {note}")

    if summary:
        lines = ["", "| Season | Records | Avg Yield (t/ha) | Avg Area (ha) |", "|--------|---------|------------------|---------------|"]
        for row in summary[:4]:
            lines.append(f"| {row.get('season')} | {row.get('records')} | {row.get('avg_yield')} | {row.get('avg_area')} |")
        paras.append("\n".join(lines))

    paras.append("*Use this as guidance from historical records; final timing should follow local rainfall, irrigation availability, and nursery/seedling readiness.*")
    return "\n\n".join(paras)


def _bar(score: float, max_score: float, width: int = 10) -> str:
    """Create a simple text progress bar."""
    filled = round((score / max(max_score, 0.01)) * width)
    return "█" * filled + "░" * (width - filled)


def describe_suitability_score(district: str, crop: str, data: dict) -> str:
    if "error" in data:
        return f"❌ Couldn't compute suitability for **{crop}** in {district}: {data['error']}"

    total = data["total_score"]
    label = data["label"]
    subscores = data.get("subscores", {})
    soil = data.get("soil_type", "Unknown").title()
    season = data.get("season", "All seasons")
    rain_mm = data.get("annual_rainfall_mm", 0)
    need_mm = data.get("crop_water_need_mm", 0)
    irr_pct = data.get("irrigation_pct", 0)
    is_present = data.get("historical_presence", False)

    emoji_map = {"Excellent": "🟢", "Very Good": "🟢", "Moderate": "🟡", "Below Average": "🟠", "Poor": "🔴"}
    emoji = emoji_map.get(label, "🟡")

    paras = [
        f"### 📊 Suitability Analysis — {crop} in {district}\n\n{emoji} **{total}/10 — {label}**\n\nThis score combines yield performance, rainfall alignment, soil compatibility, irrigation coverage, and historical presence."
    ]

    table_lines = [
        "",
        "| Factor | Score | Max |",
        "|--------|-------|-----|",
        f"| Yield Performance | **{subscores.get('yield_performance', 0)}** | 3.0 |",
        f"| Rainfall Alignment | **{subscores.get('rainfall_alignment', 0)}** | 2.5 |",
        f"| Soil Compatibility | **{subscores.get('soil_compatibility', 0)}** | 2.0 |",
        f"| Irrigation Coverage | **{subscores.get('irrigation_coverage', 0)}** | 1.5 |",
        f"| Historical Presence | **{subscores.get('historical_presence', 0)}** | 1.0 |",
        f"| **TOTAL** | **{total}** | 10 |",
    ]
    paras.append("\n".join(table_lines))

    water_msg = "well-covered by rainfall" if rain_mm >= need_mm else f"a deficit of **{need_mm - rain_mm:.0f} mm** means irrigation support is important"
    paras.append(
        f"**Water Analysis:** District receives **{rain_mm:.0f} mm** annually versus crop need of **{need_mm} mm** — {water_msg}.\n\n"
        f"**Soil:** {soil}.\n\n"
        f"**Season considered:** {season}.\n\n"
        f"**Irrigation coverage used in scoring:** {irr_pct}%."
    )

    if not is_present:
        paras.append("⚠️ **Note:** This crop has not been historically cultivated in this district in our dataset. The score is based on environmental suitability analysis.")

    paras.append(f"💡 Try a scenario test next: *\"What if irrigation improved in {district} for {crop}?\"*")
    return "\n\n".join(paras)

# ════════════════════════════════════════════════════════════
# 10. WHAT-IF SIMULATION NLG
# ════════════════════════════════════════════════════════════
def describe_whatif(district: str, crop: str, data: dict) -> str:
    if "error" in data:
        return f"❌ What-if simulation failed: {data['error']}"

    baseline = data.get("baseline", {})
    modified = data.get("modified", {})
    delta = data.get("delta", 0)
    changes = data.get("changes_applied", [])
    verdict = data.get("verdict", "")

    b_score = baseline.get("total_score", 0)
    b_label = baseline.get("label", "Unknown")
    m_score = modified.get("total_score", 0)
    m_label = modified.get("label", "Unknown")
    delta_str = f"+{delta}" if delta > 0 else str(delta)

    paras = [
        f"### 🔬 What-If Simulation — {crop} in {district}\n\n**Scenario:** {', '.join(changes).title() if changes else 'No change'}",
        f"| Scenario | Score | Rating |\n|----------|-------|--------|\n| Current (Baseline) | **{b_score}/10** | {b_label} |\n| After Changes | **{m_score}/10** | {m_label} |\n| **Delta** | **{delta_str}** | — |",
        verdict or "This comparison shows how the score shifts under the simulated conditions.",
    ]

    b_sub = baseline.get("subscores", {})
    m_sub = modified.get("subscores", {})
    sub_table = ["| Factor | Before | After | Change |", "|--------|--------|-------|--------|"]
    for key, label in {"yield_performance": "Yield", "rainfall_alignment": "Rainfall", "soil_compatibility": "Soil", "irrigation_coverage": "Irrigation", "historical_presence": "History"}.items():
        bv = b_sub.get(key, 0)
        mv = m_sub.get(key, 0)
        change = round(mv - bv, 2)
        sub_table.append(f"| {label} | {bv} | {mv} | {change if change else '—'} |")
    paras.append("\n".join(sub_table))

    return "\n\n".join(paras)

# ════════════════════════════════════════════════════════════
# 11. COST ESTIMATION NLG
# ════════════════════════════════════════════════════════════
def describe_cost_estimate(district: str, crop: str, data: dict) -> str:
    if "error" in data:
        return f"❌ Cost estimation failed for **{crop}** in {district}: {data['error']}"

    area     = data.get("area_acres", 1.0)
    wage_adj = data.get("wage_adjustment_factor", 1.0)
    total_lo = data.get("total_cost_min", 0)
    total_hi = data.get("total_cost_max", 0)
    cpa_lo   = data.get("cost_per_acre_min", 0)
    cpa_hi   = data.get("cost_per_acre_max", 0)
    comps    = data.get("components", {})
    component_order = ["seeds", "fertilizer", "labour", "irrigation", "pesticide"]
    component_notes = []
    for key in component_order:
        vals = comps.get(key)
        if vals:
            component_notes.append(f"**{key.title()}**: ₹{vals['min']:,}–₹{vals['max']:,}")

    wage_note = ""
    if wage_adj > 1.1:
        wage_note = f" (labour costs adjusted upward by {round((wage_adj-1)*100)}% — {district} has above-average wages)"
    elif wage_adj < 0.9:
        wage_note = f" (labour costs adjusted downward by {round((1-wage_adj)*100)}% — {district} has below-average wages)"

    paras = [
        f"### 💰 Cultivation Cost Estimate — {crop} in {district}\n\n"
        f"Here's the estimated full-season cost to grow **{crop}** on **{area} acre{'s' if area != 1 else ''}** in **{district}**{wage_note}:",

        f"| Cost Component | Min (₹) | Max (₹) |\n"
        f"|----------------|---------|---------|"
        + "".join(
            f"\n| {comp.title()} | ₹{vals['min']:,} | ₹{vals['max']:,} |"
            for comp, vals in comps.items()
        )
        + f"\n| **🎯 TOTAL** | **₹{total_lo:,}** | **₹{total_hi:,}** |",
    ]

    if component_notes:
        paras.insert(1, "The estimate is built from the main cultivation cost heads: " + ", ".join(component_notes) + ".")

    mid_cost = (total_lo + total_hi) // 2
    paras.append(
        f"**Typical investment for {area} acre{'s' if area!=1 else ''}: ₹{total_lo:,} – ₹{total_hi:,}**\n\n"
        f"At the midpoint (~₹{mid_cost:,}), the cost per acre works out to approximately **₹{cpa_lo:,}–₹{cpa_hi:,}/acre**."
    )

    # Largest cost driver
    if comps:
        max_comp = max(comps, key=lambda k: comps[k]["max"])
        max_val  = comps[max_comp]["max"]
        pct      = round(max_val / total_hi * 100) if total_hi > 0 else 0
        paras.append(
            f"**Biggest cost driver:** {max_comp.title()} at up to **₹{max_val:,}** — about **{pct}%** of the total budget. "
            + {
                "labour":      "Consider mechanisation (transplanting machines, combine harvesters) to reduce labour expenditure.",
                "seeds":       "Use certified seeds from government supply centres — they're subsidised and higher quality.",
                "fertilizer":  "Soil testing before the season can optimise fertilizer use and cut costs by 15–25%.",
                "irrigation":  "Drip or sprinkler irrigation can reduce water costs by 30–40% vs. flood irrigation.",
                "pesticide":   "Integrated Pest Management (IPM) reduces pesticide costs and improves long-term soil health.",
            }.get(max_comp, "Careful planning can help reduce this component.")
        )

    paras.append(
        "📌 *These are typical ranges from Tamil Nadu's 2024–25 agricultural data and crop cost profiles. "
        "Actual costs vary with input prices, farm size, and local market conditions.*"
    )

    return "\n\n".join(paras)


def describe_profit_estimate(data: dict) -> str:
    crop = data.get("crop", "this crop")
    district = data.get("district", "this district")
    cost = data.get("cost", {})

    if "error" in data:
        paras = [
            f"### Profit Estimate — {crop} in {district}",
            data["error"],
        ]
        if cost:
            paras.append(
                f"I can still show the cultivation cost side: estimated cost is **₹{cost.get('total_cost_min', 0):,}–₹{cost.get('total_cost_max', 0):,} per acre**."
            )
            comps = cost.get("components", {})
            if comps:
                lines = ["", "| Cost Component | Min (₹) | Max (₹) |", "|----------------|---------|---------|"]
                for comp, vals in comps.items():
                    lines.append(f"| {comp.title()} | ₹{vals['min']:,} | ₹{vals['max']:,} |")
                paras.append("\n".join(lines))
        paras.append("I sincerely apologize for the inconvenience. I will improve this when more crop yield and market data are available.")
        return "\n\n".join(paras)

    area = data.get("area_acres", 1.0)
    paras = [
        f"### Profit Estimate — {crop} in {district}",
        f"For **{area} acre**, historical average yield is about **{data.get('avg_yield_t_acre')} tonnes/acre**.",
        f"Using an indicative planning price of **₹{data.get('price_rs_per_tonne'):,}/tonne**, gross revenue is about **₹{data.get('gross_revenue'):,}**.",
        f"Estimated cultivation cost is **₹{data.get('total_cost_min'):,}–₹{data.get('total_cost_max'):,}**.",
        f"So the indicative net profit range is **₹{data.get('net_profit_min'):,}–₹{data.get('net_profit_max'):,} per acre**.",
        "*This is a planning estimate only. Actual profit depends heavily on live market price, grade/quality, transport, harvest losses, and local input costs.*",
    ]
    return "\n\n".join(paras)
