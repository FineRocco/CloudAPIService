# Cloud Computing Project: Job Information Service

## 1. Introduction

This project, developed for the Cloud Computing course (CC2425-Project), aims to create a cloud-native application offering services that provide relevant information extracted from job-related datasets. The application exposes its functionalities through a REST API and is built using a microservice architecture with gRPC for internal communication. The primary goal is to design, implement, and deploy a scalable and robust application on Google Cloud Platform (GCP) leveraging services like Google Kubernetes Engine (GKE) and Cloud SQL (with considerations for BigQuery).

This README outlines the project architecture, setup, deployment, and key features, focusing on the achievements of Phase 5: Cloud Deployment and plans for Phase 6.

Postman Collection: https://.postman.co/workspace/My-Workspace~034a4811-b457-4b00-8931-4b72bda7fcbe/collection/42661225-2ba662b7-78bd-4011-b970-5a0ae8f0ca02?action=share&creator=42661225&active-environment=42661225-49bffba0-60a2-4232-9cb8-78307fb724b4

## 2. Architecture Overview

The application, JobMarketSearchAPI, follows a 3-Tier microservice architecture:

* **API Interface Layer (`api-interface` - `api_interface.py`):**
    * Exposes a REST API (built with Flask) to external clients.
    * Handles incoming API requests and interacts with the Business Logic services via gRPC.
* **Business Logic Layer (`job-postings` - `job_postings.py`, `job-reviews` - `job_reviews.py`):**
    * `job_postings.py`: Implements business logic related to job searching, retrieving company/salary data, and posting new jobs.
    * `job_reviews.py`: Implements business logic related to posting, updating, and deleting job reviews.
    * These services process requests, apply business rules, and coordinate interactions with the data access layer via gRPC.
* **Data Access Layer (`data-access` - `data_access.py`):**
    * Manages data interactions for both job postings and job reviews.
    * Provides a gRPC interface for the business logic services to query and manipulate data.
    * Currently configured to connect to a **Cloud SQL (PostgreSQL)** instance (which serves as the persistent data store for job postings and reviews, with tables created from the .csv datasets).
    * Investigation into using **Google BigQuery** as an alternative data store has also been conducted.

**Communication:**
* External: REST API (HTTP/S) via the `api-interface`.
* Internal: gRPC for communication between `api-interface`, `job-postings`, `job-reviews`, and `data-access`.

## 3. Technology Stack

* **Programming Language:** Python
* **Frameworks:**
    * Flask (for `api-interface` REST API)
    * gRPC (for internal microservice communication)
* **Database:**
    * Google Cloud SQL (PostgreSQL) - Current primary data store.
    * Google BigQuery - Investigated as an alternative, with CSV datasets loaded from Google Cloud Storage.
* **Cloud Provider:** Google Cloud Platform (GCP)
* **Containerization:** Docker
* **Orchestration:** Google Kubernetes Engine (GKE)
* **Build Automation:** Google Cloud Build (using `cloudbuild.yaml` configurations)
* **API Specification:** OpenAPI (Swagger) - *Assumed from project Phase 2*
* **Security Enhancements (Planned/Implemented in Phase 6):** Service Mesh (e.g., Istio for mTLS), enhanced Kubernetes Secrets usage.

## 5. Local Development and Testing (Using Docker Compose)

This section describes how to set up and run the project locally using Docker Compose, primarily for development and testing purposes before cloud deployment.

### 5.1. Download Files
To use this project locally, you need to download the dataset files. These files are available at the following link:

[https://drive.google.com/drive/folders/10ftw6VcKtccCAF1b4SB4rbededgfqXB1?usp=sharing](https://drive.google.com/drive/folders/10ftw6VcKtccCAF1b4SB4rbededgfqXB1?usp=sharing)

### 5.2. Setup
After downloading the files, place them in the `datasets` directory within the project root. The `docker-compose.yml` file is configured to mount this directory into the PostgreSQL container to initialize the database.

### 5.3. How to Run
To run the entire project locally (all microservices and the PostgreSQL database), use the following command from the project root directory (where `docker-compose.yml` is located):

```sh
docker compose up --build
```

### 5.5. Observations:

1. **gRPC Channel Limits:** The gRPC channels have a default limit of 4Mb capacity per call. Some use cases were upgraded to 10Mb, but the data transfer from the "Data-access" microservice to others can still be slow due to the size of the datasets being transferred in some scenarios.

2. **Data Cleaning:** The original datasets had empty data in some columns. These were edited/cleaned to ensure proper functionality within the project.

3. **Primary Key Addition:** A primary unique key was added to the reviews dataset to facilitate its association with other datasets and improve data integrity.

## 6. Setup and Deployment (Phase 5 - GKE)

### 6.1. Prerequisites

* Google Cloud SDK (`gcloud`) installed and configured.

* `kubectl` command-line tool installed.

* Docker installed (for local building if not using Cloud Build exclusively).

* A Google Cloud Project with billing enabled.

* Google Cloud APIs enabled: Kubernetes Engine API, Artifact Registry API, Cloud SQL Admin API, (BigQuery API if using BigQuery).

* The deployment scripts `create_cluster.sh` and `deploy_microservices.sh` are present in the project root.

### 6.2. Database Setup

**Currently using Cloud SQL (PostgreSQL):**

1. Create a Cloud SQL for PostgreSQL instance in your GCP project (e.g., named `datasets` in `europe-west1`). This step might be handled by your `create_cluster.sh` script or may need to be done manually beforehand if the script expects it.

2. Create a database (e.g., `mydatabase`) and a user (e.g., `myuser`) within the instance.

3. Load your datasets (previously CSVs) into the Cloud SQL tables.

**(Alternative) Using BigQuery:**

1. Upload your CSV dataset files to a Google Cloud Storage (GCS) bucket.

2. Create a BigQuery dataset (e.g., `job_data`).

3. Load each CSV from GCS into a new BigQuery table within the dataset, either via the BigQuery Console or `bq load` command, defining or auto-detecting the schema.

### 6.3. Building Docker Images

Each microservice has a `Dockerfile`. Images are built using Google Cloud Build and pushed to Google Artifact Registry. This step is assumed to be a prerequisite for the `deploy_microservices.sh` script, or potentially handled within it.

1. **Create an Artifact Registry Docker repository** (e.g., `cloudapiservice` in `europe-west1`).

2. For each microservice (e.g., `api_interface`):

   * Navigate to the `microservices/` directory.

   * Create a `cloudbuild-<service-name>.yaml` file (or use a shared one with substitutions). Example for `api_interface`:

     ```yaml
     steps:
     - name: 'gcr.io/cloud-builders/docker'
       args: [
         'build',
         '-t', 'europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/cloudapiservice/api_interface:latest',
         '-f', 'api_interface/Dockerfile',
         '.' # Build context is the microservices/ directory
       ]
     images:
     - 'europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/cloudapiservice/api_interface:latest'
     ```

   * Run the build: `gcloud builds submit --config cloudbuild-<service-name>.yaml .`

   * Repeat for `data-access`, `job-postings`, and `job-reviews`, updating the tag and Dockerfile path.

### 6.4. Kubernetes Deployment on GKE (Using Scripts)

The deployment to GKE is streamlined using shell scripts.

1. **Create/Configure Google Service Account (GSA) for `data-access` (if using Cloud SQL or BigQuery):**

   * This is a critical step for Workload Identity and might need to be performed manually before running the scripts, or the scripts might handle it.

gcloud iam service-accounts create data-access-sa --display-name="Data Access Microservice Account" --project=YOUR_PROJECT_ID
* Grant necessary roles (e.g., `roles/cloudsql.client` for Cloud SQL, or `roles/bigquery.dataViewer` & `roles/bigquery.jobUser` for BigQuery).

* Link GSA to the Kubernetes Service Account (KSA) `data-access-ksa` (which will be created in the `job-app` namespace by your deployment script) for Workload Identity.

2. **Execute Deployment Scripts:**

* **Create/Configure GKE Cluster:**

  * Make the script executable: `chmod +x create_cluster.sh`

  * Run the script: `./create_cluster.sh`

  * This script is expected to create the GKE cluster (e.g., `cluster-jobs`), enable necessary features like Workload Identity and Cluster Autoscaler, and configure `kubectl` to point to the new cluster.

* **Deploy Microservices and Kubernetes Manifests:**

  * Make the script executable: `chmod +x deploy_microservices.sh`

  * Run the script: `./deploy_microservices.sh`

  * This script is expected to:

    * Apply the `namespace.yaml`.

    * Apply secrets (e.g., `mydatabase-secret.yaml`).

    * Apply the Kubernetes Deployment and Service manifests for all microservices (`data-access`, `job-postings`, `job-reviews`, `api-interface`).

    * Apply HPA configurations (`hpa.yaml`).

    * Apply the Ingress configuration (`ingress.yaml`).

### 6.5. Accessing the Application

1. After the `./deploy_microservices.sh` script completes, get the external IP address assigned to the Ingress:

kubectl get ingress -n job-app
(Wait a few minutes for the `ADDRESS` field to populate if it's not immediate).

2. Access your API endpoints using `http://<INGRESS_IP>/<your-endpoint-path>`.

## 7. Key Features & Use Cases (JobMarketSearchAPI)

This application provides advanced job market searches and job review functionalities through a REST API.

### 7.1 Job Search Functionalities

* **Search for Remote Jobs:**

* Allows users to search for remote jobs based on optional criteria: City, Keyword, Company name.

* Returns a list of matching jobs or an empty list.

* Endpoint Example: `GET /jobs/remote?city=<city>&keyword=<keyword>&company=<company_name>`

* **Retrieve** the Average Salary **for a Job:**

* Allows users to retrieve the average salary for a given job title.

* Returns an integer representing the average salary.

* Endpoint Example: `GET /jobs/salary/average?job_title=<job_title>`

* **Search for Best Companies:**

* Allows users to retrieve a list of top-rated companies (based on high overall ratings).

* Endpoint Example: `GET /companies/best`

* **Search for Best Cities for Job Opportunities:**

* Allows users to retrieve a list of best cities for job opportunities, ranked by job availability.

* Endpoint Example: `GET /jobs/cities/best-opportunities`

* **Search for Jobs with Ratings:**

* Allows users to search for jobs filtered by title and city.

* Returns a list of jobs in the specified city along with the average rating of the top-ranked companies.

* Endpoint Example: `GET /jobs/with-ratings?title=<job_title>&city=<city>`

* **Search for Jobs in the Largest Companies:**

* Allows users to retrieve job postings from the largest companies (by employee count).

* Endpoint Example: `GET /jobs/largest-companies`

* **Search for Best Paying Companies for a Job Title:**

* Allows users to retrieve a list of companies offering the highest average salary for a specific job title.

* Returns a list of objects containing company name and average salary.

* Endpoint Example: `GET /jobs/best-paying-companies?job_title=<job_title>`

### 7.2 Job Posting and Review Functionalities

* **Post a New Job:**

* Allows users to add a new job posting (ID, Title, Company name, Job description, Location, Views (optional)).

* Returns a success response (201) on success.

* Endpoint Example: `POST /jobs`

* **Post a New Job Review:**

* Allows users to post a review for a job (ID, Job title, Company name, Review date, Rating, Headline, Location (optional)).

* Returns a success response (201) on success.

* Endpoint Example: `POST /reviews`

* **Update a Job Review:**

* Allows users to update an existing job review (Current status, Rating, Headline) by review ID.

* Returns a success response (200) on success.

* Endpoint Example: `PUT /reviews/<review_id>`

* **Delete a Job Review:**

* Allows users to delete a job review by providing the job ID (or review ID, clarification needed).

* Returns a success response (200) on success.

* Endpoint Example: `DELETE /reviews/<review_id_or_job_id>`

*(Note: Specific endpoint paths are examples and should be confirmed with the OpenAPI specification.)*

## 8. Phase 5 Deployment Goals Achieved

This deployment fulfills the key requirements of Phase 5:

* **Containers deployed to GKE:** All four microservices are containerized and deployed.

* **Namespace:** A dedicated `job-app` namespace is used.

* **HTTP Ingress:** An Ingress resource exposes the `api-interface` via a Google Cloud Load Balancer.

* **Scalability (HPA):** Horizontal Pod Autoscalers are configured for each microservice. Cluster Autoscaler is enabled on GKE.

* **Selective Exposure:** Only the `api-interface` is exposed externally; other services communicate internally.

* **Resource Utilization:** Deployments include `requests` and `limits` for CPU and memory. (Tuned down for presentation budget).

* **Probes:** Liveness, readiness, and startup probes are defined for each microservice container.

* **Rolling Updates/Rollback:** Kubernetes Deployments are configured with a rolling update strategy by default.

* **Database:**

* Connected to an external Cloud SQL instance using the Cloud SQL Auth Proxy and Workload Identity.

* (If BigQuery was implemented): Connected to BigQuery using Workload Identity and appropriate client libraries.

## 9. Phase 6: Security & Data Privacy Improvement Plan

This section details the plan for implementing specific security and data privacy enhancements for the Job Portal application deployed on Google Kubernetes Engine (GKE), as outlined in Phase 6 of the project.

### 9.1. Introduction

The focus is on establishing secure communication channels between microservices, improving secret management practices, and outlining approaches to enhance data privacy. These improvements leverage cloud-native patterns and Google Cloud Platform (GCP) services, preparing for the final implementation.

### 9.2. Use Cases Addressed by Security Enhancements

This plan introduces or enhances the following perspectives:

* **Operator:** Observe enhanced security posture through encrypted internal traffic and managed secrets. Verify adherence to data privacy principles through configuration and potential monitoring.

* **Developer:** Work within clearer security boundaries. Potentially rely on infrastructure (e.g., a service mesh) for secure transport. Implement data handling according to privacy requirements.

* **End-User:** Benefit from increased trust due to secure handling of data and encrypted communications within the application backend.

### 9.3. Non-Functional Requirements (Security Focus)

* **NFR-SEC-01 (Security - Secure Channels):** Communication between internal microservices (`api-interface`, `job-reviews`, `job-postings`, `data-access`) must be encrypted using mutual TLS (mTLS). Services must verify the identity of their peers.

* **NFR-SEC-02 (Security - Secret Management):** Sensitive configuration data (like database credentials beyond the initial setup) must be stored securely and injected into application pods without being exposed in code or plain configuration files.

### 9.4. Architecture Enhancements for Security

* **Current Architecture Summary:** The system uses microservices (`api-interface`, `job-reviews`, `job-postings`, `data-access`) on GKE. Communication uses Kubernetes Services. An Ingress exposes `api-interface`. Database credentials currently use Kubernetes Secrets.

* **Proposed Technical Architecture Enhancements for Phase 6:**

* **A. Secure Channels (Service Mesh - e.g., Istio):**

 * Implement a service mesh like Istio to automatically provide mTLS for all gRPC communication between microservices within the GKE cluster.

 * This offloads the complexity of certificate management and mTLS configuration from the application code.

 * Istio can also provide fine-grained traffic control, observability, and security policies.

* **B. Enhanced Secret Management (Leveraging Kubernetes Secrets & Potentially GCP Secret Manager):**

 * Continue using Kubernetes Secrets for injecting sensitive data like database passwords into pods.

 * For more advanced scenarios or secrets that need to be managed outside Kubernetes, consider integrating with GCP Secret Manager. Secrets can be fetched from GCP Secret Manager at pod startup or by an init container and made available to the application.

## 10. Future Work & Improvements (Beyond Phase 6)

Based on the project statement, future work could include:

* **CI/CD Pipeline (Phase 8):** Automate building, testing, and deployment using tools like Cloud Build triggers, Jenkins, GitLab CI, or GitHub Actions.

* **Advanced Microservice Patterns (Phase 7):** Further implement patterns like circuit breakers, retries, timeouts, distributed tracing, advanced service mesh configurations.

* **Serverless Components:** Explore using Cloud Functions or Cloud Run for specific event-driven tasks or parts of the API.

* **Full Implementation of Phase 6 Security Plan:** Complete the integration of Istio and potentially GCP Secret Manager.

* **Data Science & Analytics:** Further develop data analysis capabilities, potentially using BigQuery for complex aggregations, or integrating Machine Learning models.

* **Infrastructure as Code:** Manage GCP resources using Terraform or Deployment Manager.

## 11. Cleaning Up Resources

To avoid ongoing charges after the presentation:

1. **Stop/Delete Cloud SQL Instance:**

gcloud sql instances patch YOUR_INSTANCE_NAME --activation-policy=NEVEROR to delete:gcloud sql instances delete YOUR_INSTANCE_NAME
2. **Delete GKE Resources:**

kubectl delete namespace job-app
3. **Delete GKE Cluster (Optional, if no longer needed):**

gcloud container clusters delete cluster-jobs --region=europe-west1
4. **Delete Artifact Registry Images (Optional).**

5. **Delete GCS Buckets used for datasets (Optional).**

6. **Delete BigQuery Datasets/Tables (Optional).**

**Remember to replace `YOUR_PROJECT_ID` and other placeholders with your actual values.**
Good luck with your presentation!
