import pulumi
import pulumi_gcp as gcp

# --- Configuration Variables ---
# These can be set via `pulumi config set <key> <value>`
# e.g., pulumi config set gcp_project_id your-gcp-project-id
#       pulumi config set github_organization your-github-org
#       pulumi config set github_repository your-github-repo

gcp_project_id = pulumi.Config().require("gcp_project_id")
github_organization = pulumi.Config().require("github_organization")
github_repository = pulumi.Config().require("github_repository")

# You might need to get the project number dynamically or set it as a config variable
# For simplicity, we'll assume it's available or can be fetched.
# A more robust way would be to fetch it using `gcp.organizations.get_project`
# For now, let's assume you know your project number or fetch it once.
# Example: gcp_project_number = "123456789012"
# Or fetch dynamically:
gcp_project_number = "281304798313"
# gcp_project_number = gcp.organizations.get_project(project_id=gcp_project_id).project_number

artifact_registry_repo_name = pulumi.Config().get("artifact_registry_repo_name", "cloud-run-repo")
cloud_run_region = pulumi.Config().get("cloud_run_region", "us-central1") # Must match your Cloud Run region
cloud_run_service_name = pulumi.Config().get("cloud_run_service_name", "api-assessment-service")

# The default compute service account for Cloud Run
cloud_run_compute_sa_email = f"{gcp_project_number}-compute@developer.gserviceaccount.com"

# --- Resource Definitions ---

# 0. Enable the Cloud Run API
cloud_run_api = gcp.projects.Service("cloud-run-api-enablement",
    service="run.googleapis.com",
    disable_on_destroy=False, # Keep the API enabled even after 'pulumi destroy'
    project=gcp_project_id
)

# 1. Create an Artifact Registry Repository (if it doesn't exist)
artifact_repo = gcp.artifactregistry.Repository("cloud-run-repo",
    location=cloud_run_region,
    repository_id=artifact_registry_repo_name,
    description="Docker repository for Cloud Run services",
    format="DOCKER",
    project=gcp_project_id
)

# 2. Create a Dedicated GCP Service Account for GitHub Actions
github_actions_sa = gcp.serviceaccount.Account("github-actions-sa",
    account_id="github-actions-sa",
    display_name="Service Account for GitHub Actions CI/CD",
    project=gcp_project_id
)

# 3. Grant Necessary IAM Roles to the Service Account
# Grant permission to build and push images to Artifact Registry
gcp.projects.IAMMember("artifact-registry-writer-binding",
    project=gcp_project_id,
    role="roles/artifactregistry.writer",
    member=github_actions_sa.member
)

# Grant permission to deploy to Cloud Run
gcp.projects.IAMMember("cloud-run-admin-binding",
    project=gcp_project_id,
    role="roles/run.admin",
    member=github_actions_sa.member
)

# Grant permission to impersonate the Cloud Run runtime service account (for BigQuery access)
gcp.serviceaccount.IAMMember("cloud-run-sa-user-binding",
    service_account_id=pulumi.Output.concat("projects/", gcp_project_id, "/serviceAccounts/", cloud_run_compute_sa_email),
    role="roles/iam.serviceAccountUser",
    member=github_actions_sa.member
)

# 4. Create an IAM Workload Identity Pool
github_pool = gcp.iam.WorkloadIdentityPool("github-pool",
    workload_identity_pool_id="github-pool",
    display_name="GitHub Actions Pool",
    description="Workload Identity Pool for GitHub Actions",
    project=gcp_project_id
)

# 5. Create an IAM Workload Identity Pool Provider (OIDC)
github_provider = gcp.iam.WorkloadIdentityPoolProvider("github-provider",
    workload_identity_pool_id=github_pool.workload_identity_pool_id,
    workload_identity_pool_provider_id="github-provider",
    display_name="GitHub Actions Provider",
    description="OIDC Provider for GitHub Actions",
    project=gcp_project_id,
    oidc=gcp.iam.WorkloadIdentityPoolProviderOidcArgs(
        issuer_uri="https://token.actions.githubusercontent.com",
    ),
    attribute_mapping={
        "google.subject": "assertion.sub",
        "attribute.actor": "assertion.actor",
        "attribute.repository": "assertion.repository",
    },
    # Attach the condition directly to the provider
    attribute_condition=pulumi.Output.concat(
        "assertion.repository == '", github_organization, "/", github_repository, "'"
    )
)

# 6. Grant the GitHub Actions Service Account Access to the Workload Identity Pool
# This binding is now simpler because the provider is already filtering by repository.
gcp.serviceaccount.IAMMember("github-actions-wif-binding",
    service_account_id=github_actions_sa.name, # Use .name for the fully qualified ID
    role="roles/iam.workloadIdentityUser",
    member=pulumi.Output.concat(
        "principalSet://iam.googleapis.com/projects/", gcp_project_number,
        "/locations/global/workloadIdentityPools/", github_pool.workload_identity_pool_id,
        "/attribute.repository/", github_organization, "/", github_repository
    )
)

# 7. Deploy Cloud Run Service
cloud_run_service = gcp.cloudrun.Service("api-assessment-service",
    location=cloud_run_region,
    name=cloud_run_service_name,
    project=gcp_project_id,
    template=gcp.cloudrun.ServiceTemplateArgs(
        spec=gcp.cloudrun.ServiceTemplateSpecArgs(
            containers=[gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                image=pulumi.Output.concat(
                    cloud_run_region, "-docker.pkg.dev/", gcp_project_id, "/",
                    artifact_repo.repository_id, "/",
                    cloud_run_service_name, ":latest"
                ),
                envs=[
                    gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                        name="GOOGLE_CLOUD_PROJECT",
                        value=gcp_project_id,
                    ),
                ],
            )],
            service_account_name=cloud_run_compute_sa_email, # Explicitly set the service account
        ),
    ),
    traffics=[gcp.cloudrun.ServiceTrafficArgs(
        percent=100,
        latest_revision=True,
    )],
    autogenerate_revision_name=True,
    opts=pulumi.ResourceOptions(depends_on=[
        artifact_repo,
        cloud_run_api # Explicitly depend on the API being enabled
    ])
)

# Allow unauthenticated access to the Cloud Run service
gcp.cloudrun.IamMember("api-assessment-service-invoker",
    service=cloud_run_service.name,
    location=cloud_run_region,
    role="roles/run.invoker",
    member="allUsers",
    project=gcp_project_id
)

# --- Outputs for GitHub Secrets and Testing ---
pulumi.export("wif_provider_name", github_provider.name)
pulumi.export("github_actions_service_account_email", github_actions_sa.email)
pulumi.export("cloud_run_url", cloud_run_service.statuses[0].url)