from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
from flask_restx import Api, Resource, fields, reqparse, abort
from google.cloud import bigquery
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

# Add a new configuration for custom JS
app.config['SWAGGER_UI_OAUTH_CLIENT_ID'] = ''
app.config['SWAGGER_UI_OAUTH_REALM'] = '-'
app.config['SWAGGER_UI_OAUTH_APP_NAME'] = 'Cloud API Compliance Hub'
app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
app.config['SWAGGER_UI_OPERATION_ID'] = True
app.config['SWAGGER_UI_REQUEST_DURATION'] = True
app.config['SWAGGER_UI_SUPPORTED_SUBMIT_METHODS'] = ['get']
app.config['SWAGGER_UI_HEAD_TEXT'] = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-TCLLLCG8FT"></script>
<script src="/static/swagger-ga.js"></script>
"""

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT') # Or replace with your project ID if not set as env var
DATASET_ID = 'api_security_assessment'
TABLE_ID = 'api_assessments'
CRITERIA_TABLE_ID = 'assessment_criteria' # New: Table for criteria

# Initialize BigQuery client
# Ensure GOOGLE_APPLICATION_CREDENTIALS environment variable is set
# or configure authentication explicitly if running outside a GCP environment
client = bigquery.Client()

# Initialize Flask-RESTX API
api = Api(app, version='1.0', title='Cloud API Compliance Hub',
          description='A RESTful API for querying security assessment results of cloud APIs.',
          doc='/api/v1/docs', prefix='/api/v1') # Added prefix='/api/v1' # Swagger UI will be at /api/v1/docs

# Create a namespace for the API endpoints
ns = api.namespace('assessments', description='API Assessment Operations')

# --- Flask-RESTX Models for API Responses ---

api_list_item_model = api.model('ApiListItem', {
    'api_name': fields.String(required=True, description='Friendly name of the API'),
    'api_domain_name': fields.String(required=True, description='Domain name of the API (e.g., storage.googleapis.com)'),
})

assessment_criterion_model = api.model('AssessmentCriterion', {
    'criterion_category': fields.String(required=True, description='Category of the security criterion'),
    'criterion_name': fields.String(required=True, description='Name of the security criterion'),
    'is_supported': fields.Boolean(required=True, description='Whether the criterion is supported (True/False)'),
    'caveats': fields.String(description='Limitations or conditions for support'),
    'notes': fields.String(description='Original detailed notes for the assessment'),
})

api_assessment_model = api.model('ApiAssessment', {
    'api_name': fields.String(required=True, description='Friendly name of the API'),
    'platform': fields.String(required=True, description='Cloud platform (e.g., gcp)'),
    'api_domain_name': fields.String(required=True, description='Domain name of the API (e.g., storage.googleapis.com)'),
    'is_endorsed': fields.Boolean(required=True, description='Whether the API is endorsed for use by the organization'),
    'assessment_results': fields.List(fields.Nested(assessment_criterion_model), description='List of assessment results for each criterion'),
})

# --- Web UI Endpoints ---

# Serve static files for swagger GA
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    """
    Landing page to select a cloud provider.
    """
    # Query BigQuery to get a distinct list of platforms
    query = f"""
        SELECT DISTINCT platform
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        ORDER BY platform
    """
    try:
        query_job = client.query(query)
        platforms = [row.platform for row in query_job.result()]
    except Exception as e:
        # Handle cases where the table might not exist or other BQ errors
        print(f"Could not query BigQuery for platforms: {e}")
        platforms = []
        
    return render_template('index.html', platforms=platforms)

@app.route('/criteria', methods=['GET']) # New route for criteria list
def list_criteria():
    """
    Web page to list all assessment categories and criteria.
    """
    query = f"""
        SELECT category, criterion, description
        FROM `{PROJECT_ID}.{DATASET_ID}.{CRITERIA_TABLE_ID}`
        ORDER BY category, criterion
    """
    query_job = client.query(query)
    results = query_job.result()

    criteria_list = []
    for row in results:
        criteria_list.append({
            "category": row.category,
            "criterion": row.criterion,
            "description": row.description
        })
    return render_template('criteria_list.html', criteria=criteria_list)

@app.route('/platforms/<string:platform_name>/apis', methods=['GET'])
def web_list_apis_by_platform(platform_name):
    """
    Web page to list all unique API names for a given cloud platform, with optional search.
    """
    search_term = request.args.get('search', '').strip()
    platform_name_lower = platform_name.lower()

    # Base query
    query = f"""
        SELECT DISTINCT api_name, api_domain_name
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE platform = @platform_name_lower
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("platform_name_lower", "STRING", platform_name_lower)
        ]
    )

    # Add search condition if a search term is provided
    if search_term:
        query += " AND (LOWER(api_name) LIKE @search_term OR LOWER(api_domain_name) LIKE @search_term)"
        # Update job_config with the new parameter
        job_config.query_parameters += (
            bigquery.ScalarQueryParameter("search_term", "STRING", f"%{search_term.lower()}%"),
        )

    query += " ORDER BY api_name"
    
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    apis = []
    for row in results:
        apis.append({"api_name": row.api_name, "api_domain_name": row.api_domain_name})

    message = ""
    if not apis:
        message = f"No APIs found for platform: {platform_name}"
        if search_term:
            message += f" matching '{search_term}'"

    return render_template('api_list.html', platform=platform_name, apis=apis, message=message, search_term=search_term)

@app.route('/platforms/<string:platform_name>/apis/<string:api_domain_name>', methods=['GET'])
def web_get_api_assessment(platform_name, api_domain_name):
    """
    Web page to retrieve all assessment results for a specific API on a given cloud platform.
    """
    # Convert platform_name to lowercase to match BigQuery data
    platform_name_lower = platform_name.lower()
    query = f"""
        SELECT api_name, is_endorsed, criterion_category, criterion_name, is_supported, caveats, notes
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE platform = @platform_name_lower AND api_domain_name = @api_domain_name
        ORDER BY criterion_category, criterion_name
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("platform_name_lower", "STRING", platform_name_lower),
            bigquery.ScalarQueryParameter("api_domain_name", "STRING", api_domain_name)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    assessment_results = []
    api_name_for_display = api_domain_name # Default to domain name if no results
    is_endorsed_status = False # Default value

    for row in results:
        if not api_name_for_display or api_name_for_display == api_domain_name:
            api_name_for_display = row.api_name # Use the friendly name from BQ if available
        is_endorsed_status = row.is_endorsed # Get is_endorsed from the first row (assuming it's consistent per API)

        assessment_results.append({
            "criterion_category": row.criterion_category,
            "criterion_name": row.criterion_name,
            "is_supported": row.is_supported,
            "caveats": row.caveats,
            "notes": row.notes
        })

    if not assessment_results:
        return render_template('assessment.html',
                               platform=platform_name,
                               api_name=api_domain_name,
                               is_endorsed=False,
                               assessment_results=[],
                               message=f"No assessment found for API domain: {api_domain_name} on platform: {platform_name}"), 404

    return render_template('assessment.html',
                           platform=platform_name,
                           api_name=api_name_for_display,
                           is_endorsed=is_endorsed_status,
                           assessment_results=assessment_results)

# --- REST API Endpoints (refactored with Flask-RESTX) ---

@ns.route('/platforms/<string:platform_name>/apis')
@api.doc(params={'platform_name': 'The cloud platform (e.g., gcp)'})
class ApiListByPlatform(Resource):
    @ns.marshal_list_with(api_list_item_model)
    @ns.doc(description='Lists all unique API names and their domain names for a given cloud platform.')
    def get(self, platform_name):
        platform_name_lower = platform_name.lower()
        query = f"""
            SELECT DISTINCT api_name, api_domain_name
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            WHERE platform = @platform_name_lower
            ORDER BY api_name
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("platform_name_lower", "STRING", platform_name_lower)
            ]
        )
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        apis = []
        for row in results:
            apis.append({"api_name": row.api_name, "api_domain_name": row.api_domain_name})

        if not apis:
            abort(404, message=f"No APIs found for platform: {platform_name}")

        return apis

@ns.route('/platforms/<string:platform_name>/apis/<string:api_domain_name>')
@api.doc(params={
    'platform_name': 'The cloud platform (e.g., gcp)',
    'api_domain_name': 'The domain name of the API (e.g., storage.googleapis.com)'
})
class ApiAssessment(Resource):
    @ns.marshal_with(api_assessment_model)
    @ns.doc(description='Retrieves all assessment results for a specific API on a given cloud platform.')
    def get(self, platform_name, api_domain_name):
        platform_name_lower = platform_name.lower()
        query = f"""
            SELECT api_name, is_endorsed, criterion_category, criterion_name, is_supported, caveats, notes
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            WHERE platform = @platform_name_lower AND api_domain_name = @api_domain_name
            ORDER BY criterion_category, criterion_name
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("platform_name_lower", "STRING", platform_name_lower),
                bigquery.ScalarQueryParameter("api_domain_name", "STRING", api_domain_name)
            ]
        )
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        assessment_results = []
        api_name_for_display = api_domain_name # Default to domain name if no results
        is_endorsed_status = False # Default value

        for row in results:
            if not api_name_for_display or api_name_for_display == api_domain_name:
                api_name_for_display = row.api_name # Use the friendly name from BQ if available
            is_endorsed_status = row.is_endorsed # Get is_endorsed from the first row (assuming it's consistent per API)

            assessment_results.append({
                "criterion_category": row.criterion_category,
                "criterion_name": row.criterion_name,
                "is_supported": row.is_supported,
                "caveats": row.caveats,
                "notes": row.notes
            })

        if not assessment_results:
            abort(404, message=f"No assessment found for API domain: {api_domain_name} on platform: {platform_name}")

        return {
            "api_name": api_name_for_display,
            "platform": platform_name,
            "api_domain_name": api_domain_name,
            "is_endorsed": is_endorsed_status,
            "assessment_results": assessment_results
        }

if __name__ == '__main__':
    # For local development, set GOOGLE_CLOUD_PROJECT environment variable
    # or replace PROJECT_ID with your actual project ID.
    # Ensure GOOGLE_APPLICATION_CREDENTIALS is set if using a service account key
    app.run(debug=True, host='0.0.0.0', port=8080)
