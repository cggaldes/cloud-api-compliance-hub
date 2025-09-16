

import os
import json
import argparse
import textwrap
import google.generativeai as genai

# --- Configuration ---
CRITERIA_FILE_PATH = 'data/assessment_criteria.json'
ASSESSMENTS_OUTPUT_DIR = 'data/assessments' # Updated output directory

def load_assessment_criteria(file_path):
    """Loads the assessment criteria from a newline-delimited JSON file."""
    criteria = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    criteria.append(json.loads(line))
        return criteria
    except FileNotFoundError:
        print(f"Error: Criteria file not found at '{file_path}'")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{file_path}'. Details: {e}")
        return None

def generate_prompt(platform, service_name, domain, criteria):
    """Generates a detailed, structured prompt for the AI model."""
    criteria_text = ""
    for item in criteria:
        criteria_text += f"- Category: {item['category']}, Criterion: {item['criterion']}, Description: {item['description']}\n"

    return textwrap.dedent(f"""
    As a principal cloud security architect, your task is to conduct a security assessment of a specific cloud service based on a predefined set of criteria.

    **Cloud Service Details:**
    - **Cloud Platform:** {platform.upper()}
    - **Service Name:** {service_name}
    - **Service Domain:** {domain}

    **Assessment Criteria:**
    {criteria_text}

    **Instructions:**
    For each criterion listed above, evaluate the service and provide a detailed assessment. Your response must be a series of newline-delimited JSON objects. Each JSON object represents a single criterion assessment and must conform to the following structure:
    {{
      "api_name": "{service_name}",
      "api_domain_name": "{domain}",
      "platform": "{platform.lower()}",
      "is_endorsed": false,
      "criterion_category": "...",
      "criterion_name": "...",
      "is_supported": boolean,
      "caveats": "...",
      "notes": "..."
    }}

    **Field Definitions:**
    - `api_name`: The friendly name of the API.
    - `api_domain_name`: The domain name of the API.
    - `platform`: The cloud platform identifier (e.g., "gcp", "aws", "azure").
    - `is_endorsed`: Always set this to `false`.
    - `criterion_category`: The category of the criterion being assessed.
    - `criterion_name`: The name of the specific criterion.
    - `is_supported`: A boolean (`true` or `false`).
    - `caveats`: A brief string explaining limitations or partial support. Empty if fully supported.
    - `notes`: A detailed explanation of how the service supports (or fails to support) the criterion.

    **IMPORTANT:**
    - Your final output must be **only the newline-delimited JSON objects**, with no surrounding text, explanations, or markdown formatting.
    - Ensure each JSON object is on a new line.
    - Base your assessment on publicly available documentation.
    """)

def generate_placeholder_assessment(platform, service_name, domain, criteria):
    """Generates a placeholder JSON file."""
    results = []
    for item in criteria:
        results.append({
            "api_name": service_name, "api_domain_name": domain, "platform": platform.lower(),
            "is_endorsed": False, "criterion_category": item['category'], "criterion_name": item['criterion'],
            "is_supported": False, "caveats": "Placeholder - please review and update.",
            "notes": "Placeholder - please provide a detailed assessment."
        })
    return results

def main():
    parser = argparse.ArgumentParser(description="Generate a security assessment for a new cloud API.")
    parser.add_argument("--platform", required=True, help="Cloud platform (e.g., gcp, aws).")
    parser.add_argument("--service-name", required=True, help="Friendly name of the service.")
    parser.add_argument("--domain", required=True, help="Service's API domain.")
    args = parser.parse_args()

    criteria = load_assessment_criteria(CRITERIA_FILE_PATH)
    if not criteria:
        return

    platform_dir = os.path.join(ASSESSMENTS_OUTPUT_DIR, args.platform.lower())
    os.makedirs(platform_dir, exist_ok=True)
    
    output_filename = f"{args.service_name.replace(' ', '_').replace('/', '_').lower()}_assessment.json"
    output_filepath = os.path.join(platform_dir, output_filename)

    api_key = os.getenv('GEMINI_API_KEY')

    if api_key:
        print("✅ GEMINI_API_KEY found. Generating real assessment...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = generate_prompt(args.platform, args.service_name, args.domain, criteria)
        
        try:
            response = model.generate_content(prompt)
            # Clean up the response to ensure it's valid NDJSON
            cleaned_response = "\n".join(line for line in response.text.strip().splitlines() if line.strip().startswith("{"))
            
            # Validate that the response is proper NDJSON
            json_objects = []
            for line in cleaned_response.splitlines():
                json_objects.append(json.loads(line)) # This will raise an error if a line is not valid JSON
            
            with open(output_filepath, 'w') as f:
                f.write(cleaned_response)
            print(f"✅ Successfully generated and saved real assessment to: {output_filepath}")

        except Exception as e:
            print(f"❌ An error occurred during AI generation: {e}")
            print("Falling back to placeholder generation.")
            placeholder_data = generate_placeholder_assessment(args.platform, args.service_name, args.domain, criteria)
            with open(output_filepath, 'w') as f:
                for record in placeholder_data:
                    f.write(json.dumps(record) + '\n')
            print(f"✅ Generated placeholder assessment file: {output_filepath}")

    else:
        print("⚠️ GEMINI_API_KEY not found. Generating placeholder assessment file...")
        placeholder_data = generate_placeholder_assessment(args.platform, args.service_name, args.domain, criteria)
        with open(output_filepath, 'w') as f:
            for record in placeholder_data:
                f.write(json.dumps(record) + '\n')
        print(f"✅ Generated placeholder assessment file: {output_filepath}")
        print("   To generate a real assessment, set the GEMINI_API_KEY environment variable.")

if __name__ == "__main__":
    main()
