import pandas as pd
from soil_classifier import classify_soil
from recommendation import recommend_crops_with_weather_wages_fertilizer
import tkinter as tk
from tkinter import filedialog

def load_crop_data(crop_data_path):
    crop_data = pd.read_csv(crop_data_path)
    return crop_data

def chatbot():
    crop_data_path = "data\India_Agriculture_Crop_Production_with_Soil_Types.csv"
    crop_data = load_crop_data(crop_data_path)

    print("Welcome to the Smart Farming Chatbot!")
    print("Available columns in crop data:", crop_data.columns)
    
    # Create a Tkinter window for file dialog
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Ask for image file
    image_path = filedialog.askopenfilename(title="Select an image for soil type identification",
                                             filetypes=[("Image files", "*.jpg;*.jpeg;*.png")])

    if not image_path:
        print("No image selected. Exiting...")
        return

    soil_type = classify_soil(image_path)
    print("Identified Soil Type:", soil_type)

    district = input("Enter District (or type 'exit' to quit): ")
    
    if district.lower() == 'exit':
        print("Thank you for using the Smart Farming Chatbot. Goodbye!")
        return

    recommended_crops = recommend_crops_with_weather_wages_fertilizer(crop_data, soil_type, district)
    
    print(recommended_crops)

if __name__ == "__main__":
    chatbot()
