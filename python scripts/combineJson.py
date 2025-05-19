import os
import json

# Set the path to the folder containing the JSON files
folder_path = 'sixth run'  # Replace with your actual folder path

combined_json = []

# Loop through all files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith('.json'):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # If the file contains a list of items, extend the combined list
                if isinstance(data, list):
                    combined_json.extend(data)
                else:
                    combined_json.append(data)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from file {filename}: {e}")

# Save the combined list to a new JSON file
output_path = os.path.join(folder_path, 'combined_output_sixth.json')
with open(output_path, 'w', encoding='utf-8') as outfile:
    json.dump(combined_json, outfile, indent=2)

print(f"Combined {len(combined_json)} JSON entries into {output_path}")
