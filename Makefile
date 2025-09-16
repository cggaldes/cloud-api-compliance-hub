.PHONY: setup start build deploy permissions test-service pulumi-install pulumi-init pulumi-config pulumi-up pulumi-destroy pulumi-outputs

# Default values (can be overridden by environment variables or 'make' arguments)
PROJECT_ID ?= production-e9f48c
SERVICE_NAME ?= api-assessment-service
REGION ?= us-central1
ARTIFACT_REGISTRY_REPO ?= cloud-run-repo # Name of your Artifact Registry repository

# Pulumi specific variables
PULUMI_DIR ?= pulumi/wif_setup
PULUMI_STACK ?= dev

# Github
GITHUB_ORG ?= cggaldes
GITHUB_REPO ?= cloud-api-compliance-hub

setup:
	@echo "Installing Homebrew (if not already installed)..."
	/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true
	@echo "Installing Python using Homebrew..."
	brew install python || true
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Activating virtual environment and installing Python dependencies..."
	./venv/bin/pip install -r app/requirements.txt

start:
	@echo "Starting the Flask server locally..."
	export GOOGLE_CLOUD_PROJECT="$(PROJECT_ID)" && \
	./venv/bin/python app/app.py

build:
	@echo "Building Docker image..."
	docker build -t $(SERVICE_NAME):latest -f app/Dockerfile .

deploy:
	@echo "Cloud Run deployment is now managed by Pulumi."
	@echo "To deploy or update the Cloud Run service, run: make pulumi-up"
	@echo "This will also create/update Workload Identity Federation resources."

permissions:
	@echo "\n--- Setting up BigQuery Permissions for Cloud Run Service Account ---"
	@echo "Your Cloud Run service will run with a default service account, typically:"
	@echo "  $(PROJECT_ID)-compute@developer.gserviceaccount.com"
	@echo "You need to grant this service account the necessary BigQuery roles."
	@echo "\nOption 1: Using gcloud CLI (recommended for automation/scripting)"
	@echo "  1. Get the current IAM policy (replace PROJECT_ID with your actual project ID):"
	@echo "     gcloud projects get-iam-policy $(PROJECT_ID) --format=json > policy.json"
	@echo "  2. Manually edit 'policy.json' to add the following bindings (replace PROJECT_NUMBER with your project number):"
	@echo "     (Look for the 'bindings' array and add these if they don't exist or modify existing ones)"
	@echo "     {\"role\": \"roles/bigquery.dataViewer\", \"members\": [\"serviceAccount:$(PROJECT_ID)-compute@developer.gserviceaccount.com\"]}"
	@echo "     {\"role\": \"roles/bigquery.jobUser\", \"members\": [\"serviceAccount:$(PROJECT_ID)-compute@developer.gserviceaccount.com\"]}"
	@echo "  3. Apply the updated policy:"
	@echo "     gcloud projects set-iam-policy $(PROJECT_ID) policy.json"
	@echo "\nOption 2: Using Google Cloud Console (for visual confirmation)"
	@echo "  1. Go to IAM & Admin > IAM in the GCP Console: https://console.cloud.google.com/iam-admin/iam"
	@echo "  2. Find the service account: $(PROJECT_ID)-compute@developer.gserviceaccount.com"
	@echo "  3. Click the pencil icon (Edit principal) next to it."
	@echo "  4. Add the roles: 'BigQuery Data Viewer' and 'BigQuery Job User'."
	@echo "  5. Click 'SAVE'."
	@echo "\n-------------------------------------------------------------------"

test-service:
	@echo "Testing the deployed Cloud Run service..."
	@echo "Retrieving Cloud Run URL from Pulumi outputs..."
	$(eval CLOUD_RUN_URL := $(shell cd $(PULUMI_DIR) && pulumi stack output cloud_run_url))
	@if [ -z "$(CLOUD_RUN_URL)" ]; then \
	  echo "Error: Cloud Run URL not found in Pulumi outputs. Ensure 'make pulumi-up' has been run successfully."; \
	  exit 1; \
	fi
	@echo "Cloud Run Service URL: $(CLOUD_RUN_URL)"

	@echo "\n--- Testing Web UI Endpoints ---"
	@echo "Testing landing page: $(CLOUD_RUN_URL)/"
	curl -s "$(CLOUD_RUN_URL)/" > index.html
	@echo "Landing page HTML saved to index.html. Open it in your browser to view."
	@echo "\nTesting list APIs page: $(CLOUD_RUN_URL)/platforms/gcp/apis"
	curl -s "$(CLOUD_RUN_URL)/platforms/gcp/apis" > gcp_apis_list.html
	@echo "GCP APIs list HTML saved to gcp_apis_list.html. Open it in your browser to view."
	@echo "\nTesting Cloud Storage assessment (HTML): $(CLOUD_RUN_URL)/platforms/gcp/apis/storage.googleapis.com"
	curl -s "$(CLOUD_RUN_URL)/platforms/gcp/apis/storage.googleapis.com" > cloud_storage_assessment.html
	@echo "Cloud Storage assessment HTML saved to cloud_storage_assessment.html. Open it in your browser to view."

	@echo "\n--- Testing REST API Endpoints (JSON) ---"
	@echo "Testing list APIs endpoint: $(CLOUD_RUN_URL)/api/v1/assessments/platforms/gcp/apis"
	curl -s "$(CLOUD_RUN_URL)/api/v1/assessments/platforms/gcp/apis" | python3 -m json.tool
	@echo "\nTesting Cloud Storage assessment (JSON): $(CLOUD_RUN_URL)/api/v1/assessments/platforms/gcp/apis/storage.googleapis.com"
	curl -s "$(CLOUD_RUN_URL)/api/v1/assessments/platforms/gcp/apis/storage.googleapis.com" | python3 -m json.tool

# --- Contributor Targets for Managing Assessments ---

new-assessment:
	@if [ -z "$(PLATFORM)" ] || [ -z "$(SERVICE_NAME)" ] || [ -z "$(DOMAIN)" ]; then \
	  echo "Error: PLATFORM, SERVICE_NAME, and DOMAIN must be provided."; \
	  echo "Usage: make new-assessment PLATFORM=aws SERVICE_NAME=\"Amazon S3\" DOMAIN=s3.amazonaws.com"; \
	  exit 1; \
	fi
	@echo "Generating new assessment files for $(SERVICE_NAME) on $(PLATFORM)..."
	./venv/bin/python assess_new_api.py --platform "$(PLATFORM)" --service-name "$(SERVICE_NAME)" --domain "$(DOMAIN)"

bq-load:
	@echo "Loading all assessment data into BigQuery..."
	./venv/bin/python setup_bq.py

# --- Pulumi Targets for Workload Identity Federation Setup ---

pulumi-install:
	@echo "Installing Pulumi CLI using Homebrew..."
	brew install pulumi/tap/pulumi || true


pulumi-init: pulumi-install
	@echo "Initializing Pulumi project and installing dependencies..."
	@mkdir -p $(PULUMI_DIR) # Ensure directory exists
	# Initialize Pulumi project if not already done. This also creates a venv inside PULUMI_DIR.
	cd $(PULUMI_DIR) && [ -f Pulumi.yaml ] || pulumi new python --yes --stack $(PULUMI_STACK)
	# Install/update dependencies in the Pulumi project's virtual environment
	cd $(PULUMI_DIR) && ./venv/bin/pip install -r requirements.txt
	cd $(PULUMI_DIR) && ./venv/bin/pip install pulumi_gcp

pulumi-config:
	@echo "Configuring Pulumi stack variables..."
	@if [ -z "$(GITHUB_ORG)" ] || [ -z "$(GITHUB_REPO)" ]; then \
	  echo "Error: GITHUB_ORG and GITHUB_REPO must be set. Example: make pulumi-config GITHUB_ORG=my-org GITHUB_REPO=my-repo"; \
	  exit 1; \
	fi
	@echo "Fetching GCP Project Number..."
	$(eval GCP_PROJECT_NUMBER := $(shell gcloud projects describe $(PROJECT_ID) --format='value(projectNumber)'))
	@if [ -z "$(GCP_PROJECT_NUMBER)" ]; then \
	  echo "Error: Could not fetch GCP Project Number for $(PROJECT_ID). Ensure gcloud is authenticated and project ID is correct."; \
	  exit 1; \
	fi
	@echo "GCP Project Number: $(GCP_PROJECT_NUMBER)"

	cd $(PULUMI_DIR) && pulumi config set gcp_project_id $(PROJECT_ID)
	cd $(PULUMI_DIR) && pulumi config set gcp_project_number $(GCP_PROJECT_NUMBER)
	cd $(PULUMI_DIR) && pulumi config set github_organization $(GITHUB_ORG)
	cd $(PULUMI_DIR) && pulumi config set github_repository $(GITHUB_REPO)
	cd $(PULUMI_DIR) && pulumi config set cloud_run_compute_sa_email "$(GCP_PROJECT_NUMBER)-compute@developer.gserviceaccount.com"

pulumi-up:
	@echo "Deploying Workload Identity Federation resources with Pulumi..."
	cd $(PULUMI_DIR) && pulumi up --yes

pulumi-destroy:
	@echo "Destroying Workload Identity Federation resources with Pulumi..."
	cd $(PULUMI_DIR) && pulumi destroy --yes

pulumi-outputs:
	@echo "Retrieving Pulumi stack outputs for GitHub Secrets..."
	cd $(PULUMI_DIR) && pulumi stack output wif_provider_name
	cd $(PULUMI_DIR) && pulumi stack output github_actions_service_account_email