import json

# Load the first JSON file
with open('combined_json_88.json', 'r') as f1:
    data1 = json.load(f1)

# Load the second JSON file
with open('combined_output_sixth.json', 'r') as f2:
    data2 = json.load(f2)

# Combine them — assuming both are dictionaries
combined_data = {**data1, **data2}

# Save the result to a new file
with open('combined.json', 'w') as fout:
    json.dump(combined_data, fout, indent=2)

print("Combined JSON saved to 'combined.json'")
