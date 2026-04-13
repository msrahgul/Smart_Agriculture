import pandas as pd

# Load additional datasets
rainfall_data = pd.read_csv("MONTHLY RAINFALL-District Level Data (1990-2015).csv")
wages_data = pd.read_csv("Wages-District Level Data (1966-2017).csv")
fertilizer_data = pd.read_csv("Season Fertilizer consumption-District Level Data (1990-2017).csv")

# Function to retrieve rainfall and wage data for a district
def get_rainfall_and_wage_data(district):
    district_rainfall = rainfall_data[rainfall_data['Dist Name'].str.strip().str.lower() == district.lower()]
    district_wages = wages_data[wages_data['Dist Name'].str.strip().str.lower() == district.lower()]

    if not district_rainfall.empty:
        rainfall_details = district_rainfall.iloc[0][[
            'JANUARY RAINFALL (Millimeters)', 'FEBRUARY RAINFALL (Millimeters)', 'MARCH RAINFALL (Millimeters)',
            'APRIL RAINFALL (Millimeters)', 'MAY RAINFALL (Millimeters)', 'JUNE RAINFALL (Millimeters)',
            'JULY RAINFALL (Millimeters)', 'AUGUST RAINFALL (Millimeters)', 'SEPTEMBER RAINFALL (Millimeters)',
            'OCTOBER RAINFALL (Millimeters)', 'NOVEMBER RAINFALL (Millimeters)', 'DECEMBER RAINFALL (Millimeters)',
            'ANNUAL RAINFALL (Millimeters)'
        ]]
    else:
        rainfall_details = None

    if not district_wages.empty:
        wage_details = district_wages.iloc[0][[
            'DISTRICT MALE FIELD LABOUR (Rs per Day)', 'DISTRICT FEMALE FIELD LABOUR (Rs per Day)'
        ]]
    else:
        wage_details = None

    return rainfall_details, wage_details

# Function to retrieve fertilizer consumption data for the district
def get_fertilizer_data(district):
    district_fertilizer = fertilizer_data[fertilizer_data['Dist Name'].str.strip().str.lower() == district.lower()]
    
    if not district_fertilizer.empty:
        fertilizer_details = district_fertilizer.iloc[0][[
            'NITROGEN KHARIF CONSUMPTION (tons)', 'NITROGEN RABI CONSUMPTION (tons)',
            'PHOSPHATE KHARIF CONSUMPTION (tons)', 'PHOSPHATE RABI CONSUMPTION (tons)',
            'POTASH KHARIF CONSUMPTION (tons)', 'POTASH RABI CONSUMPTION (tons)',
            'TOTAL KHARIF CONSUMPTION (tons)', 'TOTAL RABI CONSUMPTION (tons)'
        ]]
    else:
        fertilizer_details = None
    
    return fertilizer_details

# Updated recommend_crops function with rainfall, wage, fertilizer data, and crop season
def recommend_crops_with_weather_wages_fertilizer(crop_data, soil_type, district):
    # Filter data for the specific district and soil type
    filtered_data = crop_data[(crop_data['District'].str.lower() == district.lower()) & 
                              (crop_data['Soil_Type'].str.lower() == soil_type.lower())]
    
    if filtered_data.empty:
        return "No crop recommendations available for this district and soil type."
    
    # Get the best yield crops, grouped by crop and season
    best_yield_crops = filtered_data.groupby(['Crop', 'Season'], as_index=False)['Yield'].max()
    best_yield_crops = best_yield_crops.sort_values(by='Yield', ascending=False)
    
    # Fetch rainfall, wage, and fertilizer data for the district
    rainfall_details, wage_details = get_rainfall_and_wage_data(district)
    fertilizer_details = get_fertilizer_data(district)

    # Prepare output with crop details, season, rainfall, wages, and fertilizer data
    output = "Recommended Crops, Their Best Yields, and Crop Season:\n"
    for index, row in best_yield_crops.iterrows():
        output += f"Crop: {row['Crop']}, Best Yield: {row['Yield']} tonnes per hectare, Season: {row['Season']}\n"
    
    if rainfall_details is not None:
        output += "\nRainfall Details (mm) for the Year:\n"
        for month, value in rainfall_details.items():
            output += f"{month.replace(' RAINFALL (Millimeters)', '')}: {value} mm\n"
    
    if wage_details is not None:
        output += "\nAverage Daily Wage (Rs per Day):\n"
        output += f"Male Field Labour: {wage_details['DISTRICT MALE FIELD LABOUR (Rs per Day)']} Rs/day\n"
        output += f"Female Field Labour: {wage_details['DISTRICT FEMALE FIELD LABOUR (Rs per Day)']} Rs/day\n"

    if fertilizer_details is not None:
        output += "\nFertilizer Consumption (tons):\n"
        output += f"Nitrogen (Kharif): {fertilizer_details['NITROGEN KHARIF CONSUMPTION (tons)']} tons\n"
        output += f"Nitrogen (Rabi): {fertilizer_details['NITROGEN RABI CONSUMPTION (tons)']} tons\n"
        output += f"Phosphate (Kharif): {fertilizer_details['PHOSPHATE KHARIF CONSUMPTION (tons)']} tons\n"
        output += f"Phosphate (Rabi): {fertilizer_details['PHOSPHATE RABI CONSUMPTION (tons)']} tons\n"
        output += f"Potash (Kharif): {fertilizer_details['POTASH KHARIF CONSUMPTION (tons)']} tons\n"
        output += f"Potash (Rabi): {fertilizer_details['POTASH RABI CONSUMPTION (tons)']} tons\n"
        output += f"Total Fertilizer (Kharif): {fertilizer_details['TOTAL KHARIF CONSUMPTION (tons)']} tons\n"
        output += f"Total Fertilizer (Rabi): {fertilizer_details['TOTAL RABI CONSUMPTION (tons)']} tons\n"
    
    return output
