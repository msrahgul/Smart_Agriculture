"""Diagnose what the data_engine tools actually return."""
import data_engine as de

# 1. What districts are available?
print("ALL_DISTRICTS (first 10):", de.ALL_DISTRICTS[:10])
print()

# 2. Does fuzzy_district work?
for d in ["Madurai", "Coimbatore", "Thanjavur", "Erode", "Salem"]:
    result = de.fuzzy_district(d)
    print(f"fuzzy_district({d!r}) -> {result!r}")
print()

# 3. What do the tools return?
r = de.get_top_crops("Madurai")
print("get_top_crops('Madurai'):", str(r)[:200])
print()

r = de.get_rainfall_stats("Coimbatore")
print("get_rainfall_stats('Coimbatore'):", str(r)[:200])
print()

r = de.get_district_overview("Erode")
print("get_district_overview('Erode'):", str(r)[:200])
