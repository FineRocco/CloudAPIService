#!/bin/bash

# Script to deploy microservices to Google Kubernetes Engine
# with Anthos Service Mesh setup, GCSM integration (including CSI driver install),
# readiness check, and corrected location handling

# Exit immediately if a command exits with a non-zero status.
set -e

# Variables
GCP_PROJECT_ID="projectcloud-451415"
GCP_REGION="europe-west1" # Used for membership location
GCP_ZONE="europe-west1-b" # Make sure this matches the zone used in create_cluster.sh
GKE_CLUSTER="cluster-jobs"
K8S_NAMESPACE="job-app"
FLEET_MEMBERSHIP_NAME="${GKE_CLUSTER}-membership" # Convention for fleet membership name
PROJECT_DIR="." # Relative path to your project directory
ASM_REVISION_NAME="asm-managed" # The ASM revision your namespace will be labeled with

# GCSM Integration Variables
GSA_NAME="postgres-secrets-accessor"
GSA_EMAIL="${GSA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
KSA_NAME="postgres-ksa"
SECRET_NAME_DB_IN_GCSM="postgres-database"
SECRET_NAME_USER_IN_GCSM="postgres-username"
SECRET_NAME_PASSWORD_IN_GCSM="postgres-password"
K8S_SECRET_NAME_FOR_POSTGRES="postgres-db-credentials" # K8s secret that will be synced by CSI driver

# ASM Readiness Check Variables
MAX_ASM_WAIT_MINUTES=20
POLL_INTERVAL_SECONDS=30

# Secrets Store CSI Driver Variables
MAX_CSI_COMPONENT_WAIT_MINUTES=5
CSI_POLL_INTERVAL_SECONDS=15
MAX_OBJECT_WAIT_ATTEMPTS=30 
OBJECT_WAIT_INTERVAL=10     

CSI_DRIVER_DAEMONSET_NAME="csi-secrets-store" 
GCP_PROVIDER_DAEMONSET_NAME="csi-secrets-store-provider-gcp"
CSI_CONTROLLER_DEPLOYMENT_NAME="csi-secrets-store-controller" 
MAX_K8S_SECRET_WAIT_MINUTES=3


# Function to install Secrets Store CSI Driver and GCP Provider
install_secrets_store_csi_driver() {
  echo "Starting Secrets Store CSI Driver and GCP Provider installation..."
  local max_attempts_crd_obj=$((MAX_CSI_COMPONENT_WAIT_MINUTES * 60 / OBJECT_WAIT_INTERVAL))
  local max_attempts_workload_check=$((MAX_CSI_COMPONENT_WAIT_MINUTES * 60 / CSI_POLL_INTERVAL_SECONDS))
  local current_attempt=0

  echo "Applying Secrets Store CSI Driver CRDs and RBAC..."
  kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/main/deploy/rbac-secretproviderclass.yaml
  
  # Apply RBAC for Kubernetes Secret Sync functionality
  echo "Applying RBAC for Kubernetes Secret Sync..."
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secrets-store-csi-driver-k8s-secrets-role
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: secrets-store-csi-driver-k8s-secrets-rolebinding
subjects:
- kind: ServiceAccount
  name: secrets-store-csi-driver # This SA is created by the driver's main manifest
  namespace: kube-system
roleRef:
  kind: ClusterRole
  name: secrets-store-csi-driver-k8s-secrets-role
  apiGroup: rbac.authorization.k8s.io
EOF
  echo "RBAC for Kubernetes Secret Sync applied."

  kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/main/deploy/secrets-store.csi.x-k8s.io_secretproviderclasses.yaml
  kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/main/deploy/secrets-store.csi.x-k8s.io_secretproviderclasspodstatuses.yaml

  echo "Verifying SecretProviderClass CRD installation..."
  current_attempt=0
  while ! kubectl get crd secretproviderclasses.secrets-store.csi.x-k8s.io &> /dev/null; do
    current_attempt=$((current_attempt + 1))
    if [[ ${current_attempt} -gt ${max_attempts_crd_obj} ]]; then
      echo "ERROR: SecretProviderClass CRD was not found after applying. Exiting."
      exit 1
    fi
    echo "SecretProviderClass CRD not yet recognized by API server (attempt ${current_attempt}/${max_attempts_crd_obj}). Waiting ${OBJECT_WAIT_INTERVAL}s..."
    sleep "${OBJECT_WAIT_INTERVAL}"
  done
  echo "SecretProviderClass CRD found."

  echo "Installing Secrets Store CSI Driver components (Controller, DaemonSet)..."
  if ! kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/main/deploy/secrets-store-csi-driver.yaml; then
    echo "ERROR: Failed to apply secrets-store-csi-driver.yaml. Exiting."
    exit 1
  fi
  echo "Applied secrets-store-csi-driver.yaml successfully. Waiting up to 60s for resources to be created and recognized by API server..."
  sleep 60 

  echo "Applying custom CSIDriver object from csidriver.yaml..."
  # Assuming csidriver.yaml is in the datasets directory and defines secrets-store.csi.k8s.io
  if ! kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/main/deploy/csidriver.yaml; then
    echo "ERROR: Failed to apply custom csidriver.yaml. Exiting."
    exit 1
  fi
  echo "Applied custom csidriver.yaml successfully."

  echo "Installing Google Cloud Secret Manager Provider for CSI Driver (${GCP_PROVIDER_DAEMONSET_NAME})..."
  if ! kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/secrets-store-csi-driver-provider-gcp/main/deploy/provider-gcp-plugin.yaml; then
    echo "ERROR: Failed to apply provider-gcp-plugin.yaml. Exiting."
    exit 1
  fi
  echo "Applied provider-gcp-plugin.yaml successfully."

  echo "Waiting for Secrets Store CSI Driver Node DaemonSet ('${CSI_DRIVER_DAEMONSET_NAME}') and GCP Provider DaemonSet ('${GCP_PROVIDER_DAEMONSET_NAME}') pods to be ready..."
  CSI_NODE_DRIVER_READY=false
  GCP_PROVIDER_READY=false
  SECONDS_CSI=0
  TIMEOUT_SECONDS_CSI=$((MAX_CSI_COMPONENT_WAIT_MINUTES * 60))

  while [[ "${CSI_NODE_DRIVER_READY}" != "true" || "${GCP_PROVIDER_READY}" != "true" ]]; do
    if [[ ${SECONDS_CSI} -gt ${TIMEOUT_SECONDS_CSI} ]]; then
      echo "ERROR: Timeout waiting for CSI Node Driver or GCP Provider DaemonSet pods to become ready."
      echo "Current status of ${CSI_DRIVER_DAEMONSET_NAME} DaemonSet:"
      kubectl get daemonset "${CSI_DRIVER_DAEMONSET_NAME}" -n kube-system -o yaml 2>/dev/null || echo "DaemonSet ${CSI_DRIVER_DAEMONSET_NAME} not found."
      echo "Current status of ${GCP_PROVIDER_DAEMONSET_NAME} DaemonSet:"
      kubectl get daemonset "${GCP_PROVIDER_DAEMONSET_NAME}" -n kube-system -o yaml 2>/dev/null || echo "DaemonSet ${GCP_PROVIDER_DAEMONSET_NAME} not found."
      exit 1
    fi

    if [[ "${CSI_NODE_DRIVER_READY}" != "true" ]]; then
      if kubectl get daemonset "${CSI_DRIVER_DAEMONSET_NAME}" -n kube-system &> /dev/null; then
        DESIRED_DRIVER=$(kubectl get daemonset "${CSI_DRIVER_DAEMONSET_NAME}" -n kube-system -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo -1)
        READY_DRIVER=$(kubectl get daemonset "${CSI_DRIVER_DAEMONSET_NAME}" -n kube-system -o jsonpath='{.status.numberReady}' 2>/dev/null || echo 0)
        if [[ "${DESIRED_DRIVER}" -gt 0 && "${READY_DRIVER}" -ge "${DESIRED_DRIVER}" ]]; then
          echo "Secrets Store CSI Driver Node DaemonSet ('${CSI_DRIVER_DAEMONSET_NAME}') pods are Ready."
          CSI_NODE_DRIVER_READY="true"
        else
          echo "Secrets Store CSI Driver Node DaemonSet ('${CSI_DRIVER_DAEMONSET_NAME}') pods not ready yet (Desired: ${DESIRED_DRIVER}, Ready: ${READY_DRIVER}) (after ${SECONDS_CSI}s)..."
        fi
      else
        echo "Secrets Store CSI Driver Node DaemonSet ('${CSI_DRIVER_DAEMONSET_NAME}') not found yet (after ${SECONDS_CSI}s)..."
      fi
    fi

    if [[ "${GCP_PROVIDER_READY}" != "true" ]]; then
      if kubectl get daemonset "${GCP_PROVIDER_DAEMONSET_NAME}" -n kube-system &> /dev/null; then
        DESIRED_PROVIDER=$(kubectl get daemonset "${GCP_PROVIDER_DAEMONSET_NAME}" -n kube-system -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo -1)
        READY_PROVIDER=$(kubectl get daemonset "${GCP_PROVIDER_DAEMONSET_NAME}" -n kube-system -o jsonpath='{.status.numberReady}' 2>/dev/null || echo 0)
        if [[ "${DESIRED_PROVIDER}" -gt 0 && "${READY_PROVIDER}" -ge "${DESIRED_PROVIDER}" ]]; then
          echo "GCP Provider for CSI Driver DaemonSet ('${GCP_PROVIDER_DAEMONSET_NAME}') pods are Ready."
          GCP_PROVIDER_READY="true"
        else
          echo "GCP Provider for CSI Driver DaemonSet ('${GCP_PROVIDER_DAEMONSET_NAME}') pods not ready yet (Desired: ${DESIRED_PROVIDER}, Ready: ${READY_PROVIDER}) (after ${SECONDS_CSI}s)..."
        fi
      else
          echo "GCP Provider for CSI Driver DaemonSet ('${GCP_PROVIDER_DAEMONSET_NAME}') not found yet (after ${SECONDS_CSI}s)..."
      fi
    fi

    if [[ "${CSI_NODE_DRIVER_READY}" == "true" && "${GCP_PROVIDER_READY}" == "true" ]]; then
      break
    fi
    sleep "${CSI_POLL_INTERVAL_SECONDS}"
    SECONDS_CSI=$((SECONDS_CSI + CSI_POLL_INTERVAL_SECONDS))
  done
  echo "All Secrets Store CSI Driver components (Node DaemonSet, Provider DaemonSet, CSIDriver object) are ready."
}

# --- Google Cloud and GKE Configuration ---
# ... (rest of the script is the same) ...
echo "Setting Google Cloud project to: ${GCP_PROJECT_ID}..."
gcloud config set project "${GCP_PROJECT_ID}"

echo "Authenticating with GKE cluster: ${GKE_CLUSTER} in zone ${GCP_ZONE}..."
gcloud container clusters get-credentials "${GKE_CLUSTER}" --zone "${GCP_ZONE}" --project "${GCP_PROJECT_ID}"

# --- Install Secrets Store CSI Driver (if not already installed/ready) ---
install_secrets_store_csi_driver

# --- Ensure Kubernetes Namespace Exists ---
echo "Ensuring namespace '${K8S_NAMESPACE}' exists..."
if ! kubectl get namespace "${K8S_NAMESPACE}" --dry-run=client -o name &> /dev/null; then
  echo "Creating namespace '${K8S_NAMESPACE}'..."
  kubectl create namespace "${K8S_NAMESPACE}"
else
  echo "Namespace '${K8S_NAMESPACE}' already exists."
fi

# --- Workload Identity and Secret Manager Setup ---
echo "Starting Workload Identity and Google Cloud Secret Manager setup..."
# 1. Create Google Service Account (GSA) if it doesn't exist
echo "Checking for GSA '${GSA_EMAIL}'..."
if ! gcloud iam service-accounts describe "${GSA_EMAIL}" --project="${GCP_PROJECT_ID}" &> /dev/null; then
  echo "Creating GSA '${GSA_NAME}'..."
  gcloud iam service-accounts create "${GSA_NAME}" \
      --project="${GCP_PROJECT_ID}" \
      --display-name="PostgreSQL Secrets Accessor GSA"
else
  echo "GSA '${GSA_EMAIL}' already exists."
fi

# 2. Grant GSA IAM Permission to Access Secrets in GCSM
echo "Granting GSA '${GSA_EMAIL}' access to GCSM secrets..."
gcloud secrets add-iam-policy-binding "${SECRET_NAME_DB_IN_GCSM}" \
    --project="${GCP_PROJECT_ID}" \
    --role="roles/secretmanager.secretAccessor" \
    --member="serviceAccount:${GSA_EMAIL}" \
    --condition=None || echo "Warning: Failed to bind GSA to DB secret ('${SECRET_NAME_DB_IN_GCSM}'). It may already have the permission or the secret might not exist."

gcloud secrets add-iam-policy-binding "${SECRET_NAME_USER_IN_GCSM}" \
    --project="${GCP_PROJECT_ID}" \
    --role="roles/secretmanager.secretAccessor" \
    --member="serviceAccount:${GSA_EMAIL}" \
    --condition=None || echo "Warning: Failed to bind GSA to User secret ('${SECRET_NAME_USER_IN_GCSM}'). It may already have the permission or the secret might not exist."

gcloud secrets add-iam-policy-binding "${SECRET_NAME_PASSWORD_IN_GCSM}" \
    --project="${GCP_PROJECT_ID}" \
    --role="roles/secretmanager.secretAccessor" \
    --member="serviceAccount:${GSA_EMAIL}" \
    --condition=None || echo "Warning: Failed to bind GSA to Password secret ('${SECRET_NAME_PASSWORD_IN_GCSM}'). It may already have the permission or the secret might not exist."
echo "GSA permissions for GCSM secrets updated."

# 3. Create Kubernetes Service Account (KSA) if it doesn't exist
echo "Checking for KSA '${KSA_NAME}' in namespace '${K8S_NAMESPACE}'..."
if ! kubectl get serviceaccount "${KSA_NAME}" --namespace "${K8S_NAMESPACE}" &> /dev/null; then
  echo "Creating KSA '${KSA_NAME}'..."
  kubectl create serviceaccount "${KSA_NAME}" --namespace "${K8S_NAMESPACE}"
else
  echo "KSA '${KSA_NAME}' already exists in namespace '${K8S_NAMESPACE}'."
fi

# 4. Link GSA to KSA for Workload Identity (IAM binding)
echo "Linking GSA '${GSA_EMAIL}' with KSA '${KSA_NAME}' for Workload Identity..."
gcloud iam service-accounts add-iam-policy-binding "${GSA_EMAIL}" \
    --project="${GCP_PROJECT_ID}" \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${GCP_PROJECT_ID}.svc.id.goog[${K8S_NAMESPACE}/${KSA_NAME}]" \
    --condition=None || echo "Warning: Failed to add Workload Identity User role (may already exist)."

# 5. Annotate KSA
echo "Annotating KSA '${KSA_NAME}'..."
kubectl annotate serviceaccount "${KSA_NAME}" \
    --namespace "${K8S_NAMESPACE}" \
    "iam.gke.io/gcp-service-account=${GSA_EMAIL}" \
    --overwrite
echo "Workload Identity setup steps completed."

# --- Anthos Service Mesh (ASM) Setup ---
# ... (Rest of your script for ASM and application deployment) ...
echo "Starting Anthos Service Mesh (Google-managed) setup..."
echo "Ensuring necessary Google Cloud APIs are enabled..."
gcloud services enable \
    container.googleapis.com \
    gkehub.googleapis.com \
    mesh.googleapis.com \
    anthos.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com --project="${GCP_PROJECT_ID}"

echo "Checking for existing fleet membership '${FLEET_MEMBERSHIP_NAME}' in location '${GCP_REGION}'..."
if ! gcloud container fleet memberships describe "${FLEET_MEMBERSHIP_NAME}" --project="${GCP_PROJECT_ID}" --location="${GCP_REGION}" &> /dev/null; then
  echo "Registering GKE cluster '${GKE_CLUSTER}' to the fleet as '${FLEET_MEMBERSHIP_NAME}'..."
  gcloud container fleet memberships register "${FLEET_MEMBERSHIP_NAME}" \
    --gke-cluster="${GCP_ZONE}/${GKE_CLUSTER}" \
    --enable-workload-identity \
    --project="${GCP_PROJECT_ID}"
  echo "Cluster registration initiated."
else
  echo "Cluster membership '${FLEET_MEMBERSHIP_NAME}' already exists in location '${GCP_REGION}' or an error occurred checking."
fi

echo "Enabling Anthos Service Mesh feature on the fleet..."
gcloud container fleet mesh enable --project "${GCP_PROJECT_ID}"

echo "Updating fleet membership feature in location '${GCP_REGION}' to use Google-managed ASM for '${FLEET_MEMBERSHIP_NAME}'..."
UPDATE_EXIT_CODE=0
UPDATE_OUTPUT=$(gcloud container fleet mesh update \
  --management automatic \
  --memberships "${FLEET_MEMBERSHIP_NAME}" \
  --location "${GCP_REGION}" \
  --project "${GCP_PROJECT_ID}" 2>&1) || UPDATE_EXIT_CODE=$?

if [[ ${UPDATE_EXIT_CODE} -ne 0 ]]; then
  if [[ "${UPDATE_OUTPUT}" == *"ALREADY_EXISTS"* ]]; then
    echo "ASM feature configuration for membership '${FLEET_MEMBERSHIP_NAME}' in location '${GCP_REGION}' already exists. Continuing..."
  else
    echo "ERROR: Failed to update fleet mesh configuration:" >&2
    echo "${UPDATE_OUTPUT}" >&2
    exit ${UPDATE_EXIT_CODE}
  fi
fi
echo "Google-managed ASM provisioning/update command executed."

echo "Waiting for ASM ControlPlaneRevision '${ASM_REVISION_NAME}' to be ready (max ${MAX_ASM_WAIT_MINUTES} minutes)..."
SECONDS=0
RECONCILED_STATUS=""
TIMEOUT_SECONDS=$((MAX_ASM_WAIT_MINUTES * 60))

while [[ "${RECONCILED_STATUS}" != "True" ]]; do
  if [[ ${SECONDS} -gt ${TIMEOUT_SECONDS} ]]; then
    echo "ERROR: Timeout waiting for ASM ControlPlaneRevision '${ASM_REVISION_NAME}' to become ready."
    kubectl get controlplanerevision "${ASM_REVISION_NAME}" -n istio-system -o yaml 2>/dev/null || echo "ControlPlaneRevision ${ASM_REVISION_NAME} not found."
    exit 1
  fi

  if kubectl get crd controlplanerevisions.mesh.cloud.google.com &> /dev/null; then
      RECONCILED_STATUS=$(kubectl get controlplanerevision "${ASM_REVISION_NAME}" -n istio-system -o jsonpath='{.status.conditions[?(@.type=="Reconciled")].status}' 2>/dev/null || echo "NotFoundOrError")
  else
      echo "ControlPlaneRevision CRD not found yet, waiting..."
      RECONCILED_STATUS="CRDNotFound"
  fi

  if [[ "${RECONCILED_STATUS}" == "True" ]]; then
    echo "ASM ControlPlaneRevision '${ASM_REVISION_NAME}' is Reconciled (Status: True)."
    break
  elif [[ "${RECONCILED_STATUS}" == "NotFoundOrError" ]]; then
    echo "ASM ControlPlaneRevision '${ASM_REVISION_NAME}' not found or error fetching status (after ${SECONDS}s). Retrying..."
  elif [[ "${RECONCILED_STATUS}" == "CRDNotFound" ]]; then
    echo "ControlPlaneRevision CRD not found yet (after ${SECONDS}s). Retrying..."
  else
    CURRENT_STATUS_MESSAGE=$(kubectl get controlplanerevision "${ASM_REVISION_NAME}" -n istio-system -o jsonpath='{.status.conditions[?(@.type=="Reconciled")].message}' 2>/dev/null || echo "No message")
    echo "ASM ControlPlaneRevision '${ASM_REVISION_NAME}' not yet Reconciled (Status: ${RECONCILED_STATUS}, Message: ${CURRENT_STATUS_MESSAGE}). Waited ${SECONDS}s. Retrying in ${POLL_INTERVAL_SECONDS}s..."
  fi
  sleep "${POLL_INTERVAL_SECONDS}"
  SECONDS=$((SECONDS + POLL_INTERVAL_SECONDS))
done
echo "Anthos Service Mesh '${ASM_REVISION_NAME}' is ready!"

echo "Labeling namespace '${K8S_NAMESPACE}' for Istio sidecar injection ('${ASM_REVISION_NAME}')..."
kubectl label namespace "${K8S_NAMESPACE}" istio.io/rev="${ASM_REVISION_NAME}" --overwrite
echo "Namespace '${K8S_NAMESPACE}' labeled."

echo "Applying SecretProviderClass for PostgreSQL..."
kubectl apply -f "${PROJECT_DIR}/datasets/secret-provider-postgres.yaml" -n "${K8S_NAMESPACE}"

echo "Navigating to dataset directory: ${PROJECT_DIR}/datasets/"
cd "${PROJECT_DIR}/datasets/"

echo "Applying destination rule..."
kubectl apply -f destination-rule.yaml -n "${K8S_NAMESPACE}"

echo "Applying PostgreSQL PersistentVolumeClaim (PVC)..."
kubectl apply -f postgres-pvc.yaml -n "${K8S_NAMESPACE}"

echo "Applying PostgreSQL service..."
kubectl apply -f postgres-service.yaml -n "${K8S_NAMESPACE}"

echo "Applying PostgreSQL deployment..."
kubectl apply -f postgres-deployment.yaml -n "${K8S_NAMESPACE}"

echo "Waiting for Kubernetes Secret '${K8S_SECRET_NAME_FOR_POSTGRES}' to be created by CSI driver (max ${MAX_K8S_SECRET_WAIT_MINUTES} minutes)..."
SECONDS_K8S_SECRET=0
TIMEOUT_SECONDS_K8S_SECRET=$((MAX_K8S_SECRET_WAIT_MINUTES * 60))
while ! kubectl get secret "${K8S_SECRET_NAME_FOR_POSTGRES}" -n "${K8S_NAMESPACE}" &> /dev/null; do
  if [[ ${SECONDS_K8S_SECRET} -gt ${TIMEOUT_SECONDS_K8S_SECRET} ]]; then
    echo "ERROR: Timeout waiting for Kubernetes Secret '${K8S_SECRET_NAME_FOR_POSTGRES}' to be created."
    echo "Check logs of '${GCP_PROVIDER_DAEMONSET_NAME}' pods in 'kube-system' and the 'postgres-deployment' pod (if it's running and has the CSI volume)."
    exit 1
  fi
  echo "Kubernetes Secret '${K8S_SECRET_NAME_FOR_POSTGRES}' not found yet (after ${SECONDS_K8S_SECRET}s). Retrying in ${POLL_INTERVAL_SECONDS}s..."
  sleep "${POLL_INTERVAL_SECONDS}"
  SECONDS_K8S_SECRET=$((SECONDS_K8S_SECRET + POLL_INTERVAL_SECONDS))
done
echo "Kubernetes Secret '${K8S_SECRET_NAME_FOR_POSTGRES}' found."

echo "Navigating back to project root directory..."
cd ..

echo "Applying Data Access service..."
kubectl apply -f data-access-service.yaml -n "${K8S_NAMESPACE}"
echo "Applying Data Access deployment..."
kubectl apply -f data-access-deployment.yaml -n "${K8S_NAMESPACE}"

echo "Applying Job Postings service and deployment..."
if [[ -f "job-postings-service.yaml" ]]; then
  kubectl apply -f job-postings-service.yaml -n "${K8S_NAMESPACE}"
fi
kubectl apply -f job-postings-deployment.yaml -n "${K8S_NAMESPACE}"

echo "Applying Job Reviews service and deployment..."
if [[ -f "job-reviews-service.yaml" ]]; then
  kubectl apply -f job-reviews-service.yaml -n "${K8S_NAMESPACE}"
fi
kubectl apply -f job-reviews-deployment.yaml -n "${K8S_NAMESPACE}"

echo "Applying API Interface BackendConfig..."
kubectl apply -f api-interface-backendconfig.yaml -n "${K8S_NAMESPACE}"

echo "Applying API Interface service and deployment..."
kubectl apply -f api-interface-deployment.yaml -n "${K8S_NAMESPACE}"

echo "Applying Ingress resource..."
kubectl apply -f ingress.yaml -n "${K8S_NAMESPACE}"

echo ""
echo "-----------------------------------------------------------------------"
echo "Secrets Store CSI Driver, ASM setup, GCSM integration, and microservice deployment script completed!"
echo "Namespace '${K8S_NAMESPACE}' is configured for ASM with '${ASM_REVISION_NAME}' revision."
echo "PostgreSQL deployment should use KSA '${KSA_NAME}' and CSI driver for secrets."
echo "Your applications should now be deployed with Istio sidecars (2/2, except if PostgreSQL injection is false)."
echo "Monitor pod status with: kubectl get pods -n ${K8S_NAMESPACE} -w"
echo "-----------------------------------------------------------------------"
