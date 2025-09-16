
import os
import json
from glob import glob
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# --- Configuration ---
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'production-e9f48c')
DATASET_ID = 'api_security_assessment'
CRITERIA_TABLE_ID = 'assessment_criteria'
ASSESSMENTS_TABLE_ID = 'api_assessments'

# Paths to data and schema files
CRITERIA_DATA_FILE = 'data/assessment_criteria.json'
CRITERIA_SCHEMA_FILE = 'data/assessment_criteria_schema.json'
ASSESSMENTS_SCHEMA_FILE = 'data/api_assessments_new_schema.json'
ASSESSMENTS_DATA_DIR = 'data/assessments' # Directory to scan for assessment files

# --- Initialize BigQuery Client ---
client = bigquery.Client(project=PROJECT_ID)

def create_dataset_if_not_exists():
    """Creates the BigQuery dataset if it does not already exist."""
    dataset_ref = client.dataset(DATASET_ID)
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset '{DATASET_ID}' already exists.")
    except NotFound:
        print(f"Creating dataset '{DATASET_ID}'...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        print(f"Dataset '{DATASET_ID}' created.")

def load_schema_from_file(schema_path):
    """Loads a BigQuery schema from a JSON file."""
    schema = []
    with open(schema_path, 'r') as f:
        schema_json = json.load(f)
        for field in schema_json:
            # Added support for 'mode' field in schema JSON
            mode = field.get('mode', 'NULLABLE')
            schema.append(bigquery.SchemaField(field['name'], field['type'], mode=mode))
    return schema

def setup_table(table_id, schema_file, data_files):
    """Creates a table, then loads data from one or more JSON files."""
    table_ref = client.dataset(DATASET_ID).table(table_id)
    
    print(f"\n--- Processing Table: {table_id} ---")

    try:
        print(f"Loading schema from {schema_file}...")
        schema = load_schema_from_file(schema_file)
    except Exception as e:
        print(f"Error loading schema for {table_id}: {e}")
        return

    table = bigquery.Table(table_ref, schema=schema)
    client.delete_table(table_ref, not_found_ok=True)
    print(f"Creating or recreating table '{table_id}'...")
    client.create_table(table)
    print(f"Table '{table_id}' is ready.")

    # Load data from all specified files
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    for data_file in data_files:
        try:
            with open(data_file, "rb") as source_file:
                print(f"  -> Loading data from '{data_file}'...")
                load_job = client.load_table_from_file(source_file, table_ref, job_config=job_config)
            load_job.result()  # Wait for the job to complete
            if load_job.errors:
                print(f"  -> Errors encountered while loading '{data_file}':")
                for error in load_job.errors:
                    print(f"     - {error}")
            else:
                print(f"  -> Successfully loaded '{data_file}'.")
        except Exception as e:
            print(f"  -> Error loading data from '{data_file}': {e}")
            
    destination_table = client.get_table(table_ref)
    print(f"--- Finished processing. Total rows in '{table_id}': {destination_table.num_rows} ---")


def main():
    """Main function to set up the BigQuery dataset and tables."""
    create_dataset_if_not_exists()
    
    # Setup for the assessment_criteria table (single data file)
    setup_table(CRITERIA_TABLE_ID, CRITERIA_SCHEMA_FILE, [CRITERIA_DATA_FILE])
    
    # Setup for the api_assessments table (scans for multiple data files)
    assessment_files = glob(os.path.join(ASSESSMENTS_DATA_DIR, '**', '*.json'), recursive=True)
    if not assessment_files:
        print(f"Warning: No assessment files found in '{ASSESSMENTS_DATA_DIR}'. The '{ASSESSMENTS_TABLE_ID}' table will be empty.")
        # Still create the table even if no files are found
        setup_table(ASSESSMENTS_TABLE_ID, ASSESSMENTS_SCHEMA_FILE, [])
    else:
        print(f"Found the following assessment files to load: {assessment_files}")
        setup_table(ASSESSMENTS_TABLE_ID, ASSESSMENTS_SCHEMA_FILE, assessment_files)

if __name__ == "__main__":
    main()
