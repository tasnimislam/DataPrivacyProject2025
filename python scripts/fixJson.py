import json

# Load the JSON file
with open('combined_output_forth.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Process each company's companyInfo
for company in data.get("companies", []):
    company_info = company.get("companyInfo", {})
    
    # Copy values
    company["sharedDataType"] = company_info.get("dataCollected", "")
    company["DataShared"] = company_info.get("dataCategory", "")
    
    # Delete original keys
    company_info.pop("dataCollected", None)
    company_info.pop("dataCategory", None)

# Save the updated data
with open('updated_companies_forth.json', 'w', encoding='utf-8') as outfile:
    json.dump(data, outfile, indent=2)
