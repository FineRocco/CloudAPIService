#!/bin/bash

# Script to create a GKE cluster with a minimal footprint
# suitable for very limited GCE quotas (CPU=8, IP Addresses=4).

# Exit immediately if a command exits with a non-zero status.
set -e

# Variables (adjust if needed)
GCP_PROJECT="projectcloud-451415"
GKE_CLUSTER_NAME="cluster-jobs"
GCP_ZONE="europe-west1-b" # Choose ONE zone from the europe-west1 region

NODE_MACHINE_TYPE="e2-standard-4"  
INITIAL_NODE_COUNT=2          # Start with 2 nodes (uses 8 vCPUs, 2 IPs)
                              # This matches the IP address quota limit exactly.

NODE_DISK_TYPE="pd-standard"  # Use Standard Persistent Disk for boot disk
NODE_DISK_SIZE="30GB"         # Smaller boot disk size for pd-standard
RELEASE_CHANNEL="regular"     # Or "stable", "rapid"

# --- Google Cloud Configuration ---
echo "Setting Google Cloud project to: ${GCP_PROJECT}..."
gcloud config set project "${GCP_PROJECT}"

# --- GKE Cluster Creation ---
echo "Creating GKE ZONAL cluster '${GKE_CLUSTER_NAME}' in zone '${GCP_ZONE}'..."
echo "Initial node pool will have a FIXED size of ${INITIAL_NODE_COUNT} node(s) of type '${NODE_MACHINE_TYPE}' with '${NODE_DISK_TYPE}' boot disks."
echo "Autoscaling will be DISABLED."

gcloud container clusters create "${GKE_CLUSTER_NAME}" \
    --project "${GCP_PROJECT}" \
    --zone "${GCP_ZONE}" \
    --release-channel "${RELEASE_CHANNEL}" \
    --machine-type "${NODE_MACHINE_TYPE}" \
    --disk-type "${NODE_DISK_TYPE}" \
    --disk-size "${NODE_DISK_SIZE}" \
    --num-nodes "${INITIAL_NODE_COUNT}" \
    --no-enable-autoscaling \
    --workload-pool="${GCP_PROJECT}.svc.id.goog" \
    --enable-ip-alias \
    --enable-shielded-nodes \
    --addons=HttpLoadBalancing,HorizontalPodAutoscaling \
    --scopes="https://www.googleapis.com/auth/cloud-platform"

echo ""
echo "-----------------------------------------------------------------------"
echo "GKE cluster '${GKE_CLUSTER_NAME}' creation initiated in zone '${GCP_ZONE}'."
echo "Initial footprint: ${INITIAL_NODE_COUNT} node(s) * machine type ${NODE_MACHINE_TYPE}."
echo "Using ${INITIAL_NODE_COUNT} vCPUs and ${INITIAL_NODE_COUNT} In-Use IP Addresses from quota."
echo "This process can take several minutes."
echo "After creation, verify node count and types, then run your deployment script."
echo "-----------------------------------------------------------------------"
