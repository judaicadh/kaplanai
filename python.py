import json
import requests
import re
import csv
import random
import google.generativeai as genai
import time

# Configure the Google Generative AI API key
GOOGLE_API_KEY = 'API KEY HERE'
genai.configure(api_key=GOOGLE_API_KEY)


model = genai.GenerativeModel(
    "models/gemini-1.5-flash-002",
    system_instruction= systeminstructions
)# Function to extract fields from the AI's text output
def extract_fields_from_text(text, record_id):
    try:
        # Clean the AI response text
        text = text.strip('```json').strip().strip('```')
        
        # Parse the AI response as JSON
        parsed_data = json.loads(text)
        return {
            "ID": record_id,
            "Title": parsed_data.get("Title", "NOT ENOUGH INFO"),
            "Description": parsed_data.get("Description", "NOT ENOUGH INFO"),
            "Bio": json.dumps(parsed_data.get("Bio", "NOT ENOUGH INFO"), ensure_ascii=False),
            "Publication Information": json.dumps(parsed_data.get("Publication Information", "NOT ENOUGH INFO"), ensure_ascii=False),
            "Person Name": parsed_data.get("Person Name", "NOT ENOUGH INFO"),
            "Business Name": parsed_data.get("Business Name", "NOT ENOUGH INFO"),
            "Subject Tags": parsed_data.get("Subject Tags", "NOT ENOUGH INFO"),
            "Type": parsed_data.get("Type", "NOT ENOUGH INFO"),
            "Subtype": parsed_data.get("Subtype", "NOT ENOUGH INFO"),
            "Address": parsed_data.get("Address", "NOT ENOUGH INFO"),
        }
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON for record ID {record_id}. Error: {e}")
        print(f"Raw text: {text}")
        return {
            "ID": record_id,
            "Title": "NOT ENOUGH INFO",
            "Description": "NOT ENOUGH INFO",
            "Bio": "NOT ENOUGH INFO",
            "Publication Information": "NOT ENOUGH INFO",
            "Person Name": "NOT ENOUGH INFO",
            "Business Name": "NOT ENOUGH INFO",
            "Subject Tags": "NOT ENOUGH INFO",
            "Type": "NOT ENOUGH INFO",
            "Subtype": "NOT ENOUGH INFO",
            "Address": "NOT ENOUGH INFO",
        }

# Function to adjust and retrieve image URLs from a manifest
def get_adjusted_image_urls_from_manifest(manifest_url, max_images=10):
    image_urls = []
    try:
        # Fetch the manifest
        response = requests.get(manifest_url)
        response.raise_for_status()  # Raise HTTP errors if they occur
        
        # Parse the JSON
        try:
            manifest = response.json()
        except ValueError as e:
            print(f"Error decoding JSON from {manifest_url}: {e}")
            return []
        
        # Extract image URLs
        for canvas in manifest.get("sequences", [{}])[0].get("canvases", []):
            for image in canvas.get("images", []):
                try:
                    image_url = image["resource"]["@id"]
                    # Adjust the URL
                    adjusted_url = re.sub(r"/full/!\d+,\d+/0/default\.jpg", "/full/!600,600/0/default.jpg", image_url)
                    image_urls.append(adjusted_url)
                except KeyError as e:
                    print(f"Error accessing image resource: {e}")
        
        # Return sampled URLs
        return random.sample(image_urls, min(max_images, len(image_urls)))
    
    except (KeyError, IndexError) as e:
        print(f"Error extracting image URLs from manifest: {e}")
        return []
    except requests.RequestException as e:
        print(f"Request error for {manifest_url}: {e}")
        return []

# Load JSON data
with open('./tradec.json', 'r') as file:
    data = json.load(file)

# Open the CSV file for incremental writing
output_file = './tradecards_processed2.csv'
with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
    fieldnames = ["ID", "Title", "Description", "Bio", "Publication Information", "Business Name", "Person Name", "Subject Tags", "Type", "Subtype", "Address"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Process each JSON record
    for record in data:
        record_id = record.get("id")
        manifest_url = record.get("manifestUrl")

        if manifest_url:
            # Collect up to 10 image URLs for this record
            image_urls = get_adjusted_image_urls_from_manifest(manifest_url, max_images=10)
            if not image_urls:
                print(f"No images found or sampled for record ID: {record_id}")
                continue

            # Combine all image URLs and record details into a single prompt for the AI
            input_data = {
                "Record Details": record,
                "Image URLs": image_urls
            }

            try:
                # Generate content using the AI model
                result = model.generate_content(json.dumps(input_data))

                # Check the AI response
                if result.candidates and result.candidates[0].content.parts:
                    response_text = result.candidates[0].content.parts[0].text
                    print(f"AI Response for Record ID {record_id}: {response_text}")
                    extracted_data = extract_fields_from_text(response_text, record_id)
                else:
                    print(f"No content generated for record ID: {record_id}")
                    extracted_data = {
                        "ID": record_id,
                        "Title": "NOT ENOUGH INFO",
                        "Description": "NOT ENOUGH INFO",
                        "Bio": "NOT ENOUGH INFO",
                        "Publication Information": "NOT ENOUGH INFO",
                        "Person Name": "NOT ENOUGH INFO",
                        "Business Name": "NOT ENOUGH INFO",
                        "Subject Tags": "NOT ENOUGH INFO",
                        "Type": "NOT ENOUGH INFO",
                        "Subtype": "NOT ENOUGH INFO",
                        "Address": "NOT ENOUGH INFO",
                    }

                # Debugging: Print the row being written
                print(f"Writing to CSV: {extracted_data}")

                # Write the consolidated row to CSV
                writer.writerow(extracted_data)
                print(f"Successfully wrote consolidated record ID: {record_id}")

            except Exception as e:
                print(f"Error processing record ID {record_id}: {e}")
        else:
            print(f"No manifest URL available for record ID {record_id}")

print(f"Processing complete. Data saved incrementally to '{output_file}'")
