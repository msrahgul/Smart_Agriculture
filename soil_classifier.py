import numpy as np
import cv2
from tensorflow.keras.models import load_model

# Load the model
model_path = "soil_classification_model.h5"
model = load_model(model_path)

def classify_soil(image_path):
    img = cv2.imread(image_path)
    img = cv2.resize(img, (224, 224))  # Resize the image to 224x224
    img = img.astype('float32') / 255.0  # Normalize the image
    img = np.expand_dims(img, axis=0)  # Add batch dimension

    preds = model.predict(img)
    
    # Get the predicted class index
    predicted_class_index = np.argmax(preds, axis=1)[0]

    # Map predicted class index to soil type
    soil_types = {0: 'Alluvial soil', 1: 'Black soil', 2: 'Clay soil', 3: 'Red soil'}
    return soil_types.get(predicted_class_index, 'Unknown Soil Type')
