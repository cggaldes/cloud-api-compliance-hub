# Cloud API Compliance Hub

## 1. Goal of the Application

The primary goal of this application is to provide a centralized service for assessing Google Cloud Platform (GCP) API services against a predefined set of organizational security guidelines and guardrails. It aims to store these assessment results in a structured database (BigQuery) and expose them via a web API, allowing for easy querying and visualization of an API's security posture.

Ultimately, this system will help determine if GCP API services meet the organization's security requirements, including aspects like data residency, encryption configurability, authentication, network security, logging, vulnerability management, and compliance.

## 2. Architecture

The application follows a client-server architecture with a Flask-based API serving data stored in Google BigQuery. A temporary Google Cloud Storage (GCS) bucket is used for data migration and transformation processes.

For a visual representation, please refer to the `cloud-api-assessment.xml` diagram file located in the `diagrams/` directory. You can import this XML into [draw.io (diagrams.net)](https://app.diagrams.net/) to view the diagram.

**Key Components:**
*   **User/Client:** Interacts with the API via HTTP/S requests.
*   **Flask API Application (`app.py`):** The core web service, built with Python, responsible for handling API requests, querying BigQuery, and rendering responses (JSON or HTML).
*   **Python Virtual Environment (`venv`):** An isolated environment for managing Python dependencies, ensuring project-specific package installations without conflicts with the system Python.
*   **Authentication:** Uses Google Cloud Application Default Credentials (ADC) or a Service Account Key to authenticate with GCP services.
*   **Google BigQuery:** The data warehouse storing two main tables:
    *   `api_security_assessment.assessment_criteria`: Stores the definitions of the security assessment criteria.
    *   `api_security_assessment.api_assessments`: Stores the actual assessment results for each GCP API, linked to the criteria.
*   **Google Cloud Storage (Temporary):** Used as an intermediary for exporting, transforming, and importing data into BigQuery during schema or data model changes.

## 3. Technical Decisions

### a. Programming Language & Framework
*   **Python with Flask:** Chosen for its robust Google Cloud client libraries (especially for BigQuery and future Generative AI integration), simplicity for building data-serving APIs, and a rich AI/ML ecosystem.
*   **Alternative Considered:** Node.js. While viable, Python was preferred due to its stronger ecosystem for data science and AI/ML, which aligns with potential future extensions involving Generative AI capabilities.

### b. Data Storage
*   **Google BigQuery:** Selected for its scalability, analytical capabilities, and native integration with other Google Cloud services, making it an ideal choice for storing structured assessment data.

### c. Environment Management
*   **Python Virtual Environments (`venv`):** Implemented to manage project dependencies in isolation, preventing conflicts and ensuring a clean development environment. This addresses common `externally-managed-environment` errors on macOS.

### d. Google Cloud Authentication
*   **Application Default Credentials (ADC) via `gcloud auth application-default login`:** Recommended for local development as it leverages user credentials securely without requiring direct management of key files.
*   **Service Account Key File via `GOOGLE_APPLICATION_CREDENTIALS`:** Provided as an explicit alternative for dedicated local testing, with strong warnings about key security and non-committal to version control.

### e. API Design & Endpoints
*   **Lowercase Platform Names in URLs:** Adopted for better API design practice, promoting consistency and ease of use (e.g., `/platforms/gcp/`). The application handles the case conversion for BigQuery queries.
*   **`api_domain_name` for Specific API Retrieval:** The endpoint for retrieving detailed API assessments was changed from `api_name` to `api_domain_name` (e.g., `storage.googleapis.com`). This aligns with how APIs are addressed in GCP, is DNS-compliant, and avoids issues with spaces or mixed-case descriptions in URLs.

### f. Data Model & API Response

The API response and underlying BigQuery data model have been refined for better clarity and machine consumption.

| Field Name         | Type    | Description                                                                                                                            |
| :----------------- | :------ | :------------------------------------------------------------------------------------------------------------------------------------- |
| `api_name`         | STRING  | Friendly name of the API (e.g., "Cloud Storage").                                                                                      |
| `api_domain_name`  | STRING  | The domain name of the API (e.g., "storage.googleapis.com"). Used as a unique identifier in API endpoints.                             |
| `platform`         | STRING  | The cloud platform (e.g., "gcp"). Stored in lowercase.                                                                                 |
| `is_endorsed`      | BOOLEAN | Indicates whether the API has been formally endorsed for use by the organization (`true`/`false`). Defaults to `false`.                |
| `criterion_category` | STRING  | The category of the security criterion (e.g., "Encryption").                                                                           |
| `criterion_name`   | STRING  | The specific name of the security criterion (e.g., "Encryption in Transit").                                                           |
| `is_supported`     | BOOLEAN | Indicates if the API supports the specific criterion (`true`/`false`). Transformed from original `assessment_answer` values.           |
| `caveats`          | STRING  | Provides specific limitations, conditions, or reasons for the `is_supported` status. Derived from original `assessment_answer` and `notes`. |
| `notes`            | STRING  | Original detailed notes or justification for the assessment. Retained for full context.                                                |

**HTML Rendering:** The HTML output (`assessment.html`) presents these results in a sortable table format with columns: `Category`, `Criteria Name`, `Is Supported`, `Notes`, and `Caveats`. It also includes a search/filter capability and displays the platform name in uppercase.

## 4. Current Implementation Status

As of now, the application has the following capabilities:

*   **BigQuery Data Storage:** Two tables (`assessment_criteria` and `api_assessments`) are set up in BigQuery to store assessment criteria and the assessment results for GCP APIs.
*   **Cloud Storage Assessment:** Initial assessment data for `storage.googleapis.com` (Google Cloud Storage) has been populated into the `api_assessments` table, adhering to the latest data model.
*   **Flask API:** A Flask application is implemented with endpoints to:
    *   List APIs for a given cloud platform.
    *   Retrieve detailed security assessment results for a specific API (identified by its domain name) on a given platform.
*   **Response Formats:** The API supports both JSON and human-readable HTML output for assessment results.
*   **Makefile for Operations:** A `Makefile` is provided to streamline setup (Python installation, virtual environment creation, dependency installation) and server startup.

## 5. How to Run the Application

1.  **Navigate to the project root directory:**
    ```bash
    cd /Users/christophergaldes/Documents/Repositories/api-assessment
    ```

2.  **Set up Google Cloud Project ID:**
    Ensure your Google Cloud Project ID is set as an environment variable. Replace `production-e9f48c` with your actual project ID.
    ```bash
    export GOOGLE_CLOUD_PROJECT="production-e9f48c"
    ```
    *Alternatively, if using a Service Account Key for authentication, also set:*
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
    ```
    *(Remember: Do NOT commit your service account key file to version control!)*

3.  **Install Python and Dependencies:**
    This command will install Homebrew (if not present), install Python (if not present), create a virtual environment, and install the required Python packages into it.
    ```bash
    make setup
    ```

4.  **Start the Flask Server:**
    ```bash
    make start
    ```
    The API will start and be accessible at `http://0.0.0.0:8080`.

### API Endpoints

The application exposes both a web interface and a RESTful API for programmatic access.

#### Web UI Endpoints (for browser access)

*   **Landing Page:** `/`
*   **List APIs for a Platform:** `/platforms/{platform_name}/apis`
    *   Example: `/platforms/gcp/apis`
*   **Get API Assessment by Domain Name:** `/platforms/{platform_name}/apis/{api_domain_name}`
    *   Example: `/platforms/gcp/apis/storage.googleapis.com`

#### REST API Endpoints (v1)

All REST API endpoints are prefixed with `/api/v1`.

*   **Swagger UI (API Documentation):** `/api/v1/docs`
    *   This provides an interactive interface to explore and test all available API endpoints.

*   **List APIs for a Platform:**
    *   **Endpoint:** `GET /assessments/platforms/{platform_name}/apis`
    *   **Description:** Lists all unique API names and their domain names for a given cloud platform.
    *   **Example:** `GET /api/v1/assessments/platforms/gcp/apis`

*   **Get API Assessment by Domain Name:**
    *   **Endpoint:** `GET /assessments/platforms/{platform_name}/apis/{api_domain_name}`
    *   **Description:** Retrieves all assessment results for a specific API on a given cloud platform.
    *   **Example:** `GET /api/v1/assessments/platforms/gcp/apis/storage.googleapis.com`

## 6. Contribution Guide

This section outlines the process for contributing new API assessments to the database. Contributions are managed via Pull Requests (PRs) to ensure data quality and consistency.

### 1. Prerequisites
*   Familiarity with Google Cloud Platform (GCP) services.
*   Basic understanding of security concepts related to cloud APIs.
*   `git` installed and configured.
*   `make` installed.
*   (Optional, but recommended for interactive assessment) [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed.

### 2. Fork the Repository
*   Fork this repository on GitHub.
*   Clone your forked repository to your local machine:
    ```bash
    git clone https://github.com/YOUR_USERNAME/api-assessment.git
    cd api-assessment
    ```

### 3. Set Up Your Local Environment
*   Ensure you have Python 3.8-3.12 installed (preferably via Homebrew on macOS).
*   Set up your Google Cloud Project ID and authentication credentials (ADC or Service Account Key) as described in the "How to Run the Application" section.
*   Install project dependencies:
    ```bash
    make setup
    ```

### 4. Choose an API to Assess
*   Identify a Google Cloud API service that has not yet been assessed.
*   You can use the existing API to list assessed APIs: `http://0.0.0.0:8080/api/v1/assessments/platforms/gcp/apis` (after running `make start`).

### 5. Perform the API Security Assessment
*   For the chosen API, research its features against each of the 26 assessment criteria defined in the `api_security_assessment.assessment_criteria` BigQuery table.
*   Gather information on:
    *   Data Residency & Sovereignty
    *   Encryption (in transit, at rest, CMEK/CSEK/GMEK support)
    *   Authentication & Authorization (IAM, Service Accounts, MFA, OAuth/OIDC, API Key Management)
    *   Network Security (Private Access, Firewall Rules, DDoS Protection, API Gateway Integration)
    *   Logging & Monitoring (Audit, Access, Monitoring/Alerting, Log Retention)
    *   Vulnerability Management & Patching (Security Updates, Vulnerability Scanning)
    *   Compliance & Certifications (Industry Certifications, Compliance Documentation)
    *   Data Loss Prevention (DLP, Masking/Redaction)
    *   Secure Development Lifecycle (API Design Principles, Code Review & Testing)
*   **Gemini CLI for Research Assistance:** You can use Gemini CLI to assist with your research, similar to how this application was built. For example:
    ```bash
    gemini-cli "Summarize Google Cloud Pub/Sub data residency options."
    gemini-cli "Does Google Cloud Functions support CMEK for encryption at rest?"
    ```
    Use the information gathered to determine the `is_supported` (true/false), `caveats`, and `notes` for each criterion.

### 6. Create the New Assessment Data File
*   Create a new JSON file in a `data/new_assessments/` directory (you may need to create this directory).
*   Name the file clearly, e.g., `pubsub_assessment.json`.
*   Each line in this file should be a single JSON object representing one criterion's assessment for the new API.
*   Ensure the `platform` field is **lowercase** (e.g., `"gcp"`).
*   Set `is_endorsed` to `false` initially. This will be updated by an approver if the API is deemed suitable.
*   **Example structure for a single criterion entry:**
    ```json
    {"api_name": "Cloud Pub/Sub", "api_domain_name": "pubsub.googleapis.com", "platform": "gcp", "is_endorsed": false, "criterion_category": "Data Residency & Sovereignty", "criterion_name": "Region Selection", "is_supported": true, "caveats": "", "notes": "Cloud Pub/Sub supports regional endpoints for message storage."}
    ```
*   Repeat for all 26 criteria for the new API.

### 7. Submit a Pull Request
*   Commit your new assessment data file(s) to a new branch in your forked repository.
    ```bash
    git checkout -b add-pubsub-assessment
    git add data/new_assessments/pubsub_assessment.json
    git commit -m "Add initial security assessment for Google Cloud Pub/Sub"
    git push origin add-pubsub-assessment
    ```
*   Open a Pull Request from your branch to the `main` branch of the original repository.
*   Provide a clear description of the API assessed and any key findings.

### 8. Review and Deployment
*   Your Pull Request will be reviewed by maintainers.
*   Upon approval, a Continuous Integration/Continuous Deployment (CI/CD) pipeline will automatically load your new assessment data into the BigQuery `api_assessments` table, making it available via the API.
*   The `is_endorsed` field will be updated by an authorized party after a full review and approval of the API for organizational use.

## 7. Deployment to Google Cloud Run

This section outlines how to deploy the API application to Google Cloud Run, a managed compute platform that enables you to run stateless containers via web requests or Pub/Sub events.

### Prerequisites for Deployment
*   **Google Cloud SDK (`gcloud CLI`):** Ensure it's installed and authenticated to your GCP project.
*   **Docker:** Docker Desktop or Docker Engine installed and running on your machine (for local image building, though `gcloud build` can handle this remotely).
*   **Enabled APIs:** Ensure the following APIs are enabled in your GCP project:
    *   Cloud Run API (`run.googleapis.com`)
    *   Cloud Build API (`cloudbuild.googleapis.com`)
    *   Artifact Registry API (`artifactregistry.googleapis.com`)
    *   IAM Service Account Credentials API (`iamcredentials.googleapis.com`) - Required for Workload Identity Federation.

### Google Cloud Setup for GitHub Actions (Workload Identity Federation)

To allow GitHub Actions to securely authenticate with your Google Cloud project, we will use Workload Identity Federation. This avoids storing long-lived GCP credentials directly in GitHub Secrets.

1.  **Create an Artifact Registry Repository:**
    If you haven't already, create a Docker repository in Artifact Registry. This is where your Docker images will be stored.
    ```bash
    gcloud artifacts repositories create cloud-run-repo \
      --repository-format=docker \
      --location=us-central1 \
      --description="Docker repository for Cloud Run services"
    ```
    *Note: The `ARTIFACT_REGISTRY_REPO` in your workflows is set to `cloud-run-repo` and `REGION` to `us-central1`. Adjust if you use different names/regions.*

2.  **Create a Dedicated GCP Service Account for GitHub Actions:**
    This service account will be impersonated by GitHub Actions.
    ```bash
    gcloud iam service-accounts create github-actions-sa \
      --display-name="Service Account for GitHub Actions CI/CD"
    ```

3.  **Grant Necessary IAM Roles to the Service Account:**
    This service account needs permissions to build, push, and deploy.
    ```bash
    # Grant permission to build and push images to Artifact Registry
    gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
      --member="serviceAccount:github-actions-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
      --role="roles/artifactregistry.writer"

    # Grant permission to deploy to Cloud Run
    gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
      --member="serviceAccount:github-actions-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
      --role="roles/run.admin"

    # Grant permission to impersonate the Cloud Run runtime service account (for BigQuery access)
    gcloud iam service-accounts add-iam-policy-binding \
      ${GOOGLE_CLOUD_PROJECT}-compute@developer.gserviceaccount.com \
      --member="serviceAccount:github-actions-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
      --role="roles/iam.serviceAccountUser"
    ```
    *Note: Replace `${GOOGLE_CLOUD_PROJECT}` with your actual project ID.*

4.  **Create an IAM Workload Identity Pool and Provider:**
    This establishes the trust relationship between GitHub and GCP.
    ```bash
    gcloud iam workload-identity-pools create github-pool \
      --display-name="GitHub Actions Pool"

    gcloud iam workload-identity-pools providers create-oidc github-provider \
      --workload-identity-pool="github-pool" \
      --display-name="GitHub Actions Provider" \
      --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
      --issuer-uri="https://token.actions.githubusercontent.com"
    ```

5.  **Grant the GitHub Actions Service Account Access to the Workload Identity Pool:**
    This allows the GitHub Actions identity to impersonate your `github-actions-sa`.
    ```bash
    gcloud iam service-accounts add-iam-policy-binding github-actions-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com \
      --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe ${GOOGLE_CLOUD_PROJECT} --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_ORG/YOUR_GITHUB_REPO" \
      --role="roles/iam.workloadIdentityUser"
    ```
    *Replace `YOUR_GITHUB_ORG` with your GitHub organization name and `YOUR_GITHUB_REPO` with your repository name (e.g., `google-gemini/api-assessment`).*

6.  **Configure GitHub Secrets:**
    In your GitHub repository, go to `Settings > Secrets and variables > Actions` and add the following repository secrets:
    *   `GCP_PROJECT_ID`: Your Google Cloud Project ID (e.g., `production-e9f48c`)
    *   `ARTIFACT_REGISTRY_REPO`: The name of your Artifact Registry repository (e.g., `cloud-run-repo`)
    *   `WIF_PROVIDER`: The full resource name of your Workload Identity Provider. You can get this by running:
        ```bash
        gcloud iam workload-identity-pools providers describe github-provider \
          --workload-identity-pool=github-pool \
          --location=global \
          --format="value(name)"
        ```
        *Example output: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/oidcProviders/github-provider`*
    *   `WIF_SERVICE_ACCOUNT`: The email of the service account created in step 2 (e.g., `github-actions-sa@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com`)

### Deployment Steps

Once Workload Identity Federation is set up and secrets are configured, your GitHub Actions workflows will automatically:

1.  **Build and Push:** On every push to `main`, the `build-and-push.yml` workflow will build the Docker image and push it to your Artifact Registry.
2.  **Deploy:** After a successful build and push, the `deploy-to-cloud-run.yml` workflow will trigger and deploy the latest image to your Cloud Run service.

This automates your CI/CD pipeline for Cloud Run deployments.


This section outlines the process for contributing new API assessments to the database. Contributions are managed via Pull Requests (PRs) to ensure data quality and consistency.

### 1. Prerequisites
*   Familiarity with Google Cloud Platform (GCP) services.
*   Basic understanding of security concepts related to cloud APIs.
*   `git` installed and configured.
*   `make` installed.
*   (Optional, but recommended for interactive assessment) [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed.

### 2. Fork the Repository
*   Fork this repository on GitHub.
*   Clone your forked repository to your local machine:
    ```bash
    git clone https://github.com/YOUR_USERNAME/api-assessment.git
    cd api-assessment
    ```

### 3. Set Up Your Local Environment
*   Ensure you have Python 3.8-3.12 installed (preferably via Homebrew on macOS).
*   Set up your Google Cloud Project ID and authentication credentials (ADC or Service Account Key) as described in the "How to Run the Application" section.
*   Install project dependencies:
    ```bash
    make setup
    ```

### 4. Choose an API to Assess
*   Identify a Google Cloud API service that has not yet been assessed.
*   You can use the existing API to list assessed APIs: `http://0.0.0.0:8080/api/v1/assessments/platforms/gcp/apis` (after running `make start`).

### 5. Perform the API Security Assessment
*   For the chosen API, research its features against each of the 26 assessment criteria defined in the `api_security_assessment.assessment_criteria` BigQuery table.
*   Gather information on:
    *   Data Residency & Sovereignty
    *   Encryption (in transit, at rest, CMEK/CSEK/GMEK support)
    *   Authentication & Authorization (IAM, Service Accounts, MFA, OAuth/OIDC, API Key Management)
    *   Network Security (Private Access, Firewall Rules, DDoS Protection, API Gateway Integration)
    *   Logging & Monitoring (Audit, Access, Monitoring/Alerting, Log Retention)
    *   Vulnerability Management & Patching (Security Updates, Vulnerability Scanning)
    *   Compliance & Certifications (Industry Certifications, Compliance Documentation)
    *   Data Loss Prevention (DLP, Masking/Redaction)
    *   Secure Development Lifecycle (API Design Principles, Code Review & Testing)
*   **Gemini CLI for Research Assistance:** You can use Gemini CLI to assist with your research, similar to how this application was built. For example:
    ```bash
    gemini-cli "Summarize Google Cloud Pub/Sub data residency options."
    gemini-cli "Does Google Cloud Functions support CMEK for encryption at rest?"
    ```
    Use the information gathered to determine the `is_supported` (true/false), `caveats`, and `notes` for each criterion.

### 6. Create the New Assessment Data File
*   Create a new JSON file in a `data/new_assessments/` directory (you may need to create this directory).
*   Name the file clearly, e.g., `pubsub_assessment.json`.
*   Each line in this file should be a single JSON object representing one criterion's assessment for the new API.
*   Ensure the `platform` field is **lowercase** (e.g., `"gcp"`).
*   Set `is_endorsed` to `false` initially. This will be updated by an approver if the API is deemed suitable.
*   **Example structure for a single criterion entry:**
    ```json
    {"api_name": "Cloud Pub/Sub", "api_domain_name": "pubsub.googleapis.com", "platform": "gcp", "is_endorsed": false, "criterion_category": "Data Residency & Sovereignty", "criterion_name": "Region Selection", "is_supported": true, "caveats": "", "notes": "Cloud Pub/Sub supports regional endpoints for message storage."}
    ```
*   Repeat for all 26 criteria for the new API.

### 7. Submit a Pull Request
*   Commit your new assessment data file(s) to a new branch in your forked repository.
    ```bash
    git checkout -b add-pubsub-assessment
    git add data/new_assessments/pubsub_assessment.json
    git commit -m "Add initial security assessment for Google Cloud Pub/Sub"
    git push origin add-pubsub-assessment
    ```
*   Open a Pull Request from your branch to the `main` branch of the original repository.
*   Provide a clear description of the API assessed and any key findings.

### 8. Review and Deployment
*   Your Pull Request will be reviewed by maintainers.
*   Upon approval, a Continuous Integration/Continuous Deployment (CI/CD) pipeline will automatically load your new assessment data into the BigQuery `api_assessments` table, making it available via the API.
*   The `is_endorsed` field will be updated by an authorized party after a full review and approval of the API for organizational use.
