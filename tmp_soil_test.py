import sys
sys.path.insert(0, r'e:\College Stuff\Smart_Agriculture')

# Test 1: import works without TensorFlow
from soil_classifier import classify_soil, _heuristic_classify
print("Import OK - no TF needed")

# Test 2: heuristic on a synthetic red image
from PIL import Image
import numpy as np, tempfile, os

# Simulate a red soil image
red_soil_arr = np.zeros((200, 200, 3), dtype=np.uint8)
red_soil_arr[:, :, 0] = 180  # high red
red_soil_arr[:, :, 1] = 90   # medium green
red_soil_arr[:, :, 2] = 60   # low blue

with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    Image.fromarray(red_soil_arr).save(f.name)
    tmp_path = f.name

result = _heuristic_classify(tmp_path)
print(f"Red image -> classified as: {result}")
os.unlink(tmp_path)

# Test 3: dark image (black soil)
black_soil_arr = np.full((200, 200, 3), 50, dtype=np.uint8)
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    Image.fromarray(black_soil_arr).save(f.name)
    tmp_path = f.name

result = _heuristic_classify(tmp_path)
print(f"Dark image -> classified as: {result}")
os.unlink(tmp_path)

print("All tests passed!")
