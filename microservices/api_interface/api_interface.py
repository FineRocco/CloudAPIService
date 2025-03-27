import os
import grpc
import logging
from flask import Flask, render_template, request
from jobreviews_pb2 import BestCompaniesRequest
from jobreviews_pb2_grpc import JobReviewServiceStub
from jobpostings_pb2 import AverageSalaryRequest
from jobpostings_pb2_grpc import JobPostingServiceStub

# Set up logging.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

jobpostings_host = os.getenv("JOBPOSTINSHOST", "job-postings")
jobreviews_host = os.getenv("JOBREVIEWSHOST", "job-reviews")

# Create gRPC channels and stubs.
jobpostings_channel = grpc.insecure_channel(f"{jobpostings_host}:50051")
job_postings_client = JobPostingServiceStub(jobpostings_channel)

jobreviews_channel = grpc.insecure_channel(f"{jobreviews_host}:50051")
job_reviews_client = JobReviewServiceStub(jobreviews_channel)

@app.route("/")
def render_homepage():
    logger.debug("Homepage route called")
    
    averageSalary_request = AverageSalaryRequest(title="Marketing Coordinator")
    logger.debug("Sending AverageSalaryRequest: %s", averageSalary_request)
    
    averageSalary_response = job_postings_client.AverageSalary(averageSalary_request)
    logger.debug("Received AverageSalaryResponse: %s", averageSalary_response)
    
    return render_template(
        "homepage.html",
        averageSalary_response=averageSalary_response.averageSalary
    )

@app.route("/bestCompanies")
def render_bestCompanies():
    logger.debug("BestCompanies route called")
    
    bestCompanies_request = BestCompaniesRequest()
    logger.debug("Sending BestCompaniesRequest")
    
    bestCompanies_response = job_reviews_client.GetBestCompanies(bestCompanies_request)
    logger.debug("Received BestCompaniesResponse: %s", bestCompanies_response)
    
    return render_template(
        "bestCompanies.html",
        bestCompanies_response=bestCompanies_response.companyReview
    )

if __name__ == "__main__":
    logger.info("Starting API Interface on port 8082")
    app.run(host="0.0.0.0", port=8082)
