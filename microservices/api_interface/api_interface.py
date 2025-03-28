import os
import grpc
import logging
from flask import Flask, render_template, request
from jobreviews_pb2 import BestCompaniesRequest, UpdateJobReviewRequest
from jobreviews_pb2_grpc import JobReviewServiceStub
from jobpostings_pb2 import AverageSalaryRequest, JobPostingsForLargestCompaniesRequest
from jobpostings_pb2_grpc import JobPostingServiceStub

# Set up logging.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

jobpostings_host = os.getenv("JOBPOSTINSHOST", "job-postings")
jobreviews_host = os.getenv("JOBREVIEWSHOST", "job-reviews")

# Create gRPC channels and stubs.
jobpostings_channel = grpc.insecure_channel(f"{jobpostings_host}:50051", options=[
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
    ('grpc.max_receive_message_length', 10 * 1024 * 1024)
])
job_postings_client = JobPostingServiceStub(jobpostings_channel)

jobreviews_channel = grpc.insecure_channel(f"{jobreviews_host}:50051", options=[
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
    ('grpc.max_receive_message_length', 10 * 1024 * 1024)
])
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

@app.route("/jobsForLargestCompanies")
def render_jobsForLargestCompanies():
    logger.debug("JobsForLargestCompanies route called")
    
    jobsForLargestCompanies_request = JobPostingsForLargestCompaniesRequest()
    logger.debug("Sending JobsForLargestCompaniesRequest")
    
    jobsForLargestCompanies_response = job_postings_client.GetJobPostingsForLargestCompanies(jobsForLargestCompanies_request)
    
    return render_template(
        "jobsFromLargestCompanies.html",
        jobsForLargestCompanies_response=jobsForLargestCompanies_response.job
    )

@app.route("/updateReview", methods=["PUT"])
def update_review():
    logger.debug(f"UpdateReview route called with method: {request.method}")

    # If it's a GET request, just render the empty form
    if request.method == "GET":
        return render_template("updateReview.html", update_response=None)
    
    try:
        # Extract and validate input from the request.
        review_id = request.form.get("id") or (request.json and request.json.get("id"))
        rating = request.form.get("rating") or (request.json and request.json.get("rating"))
        headline = request.form.get("headline") or (request.json and request.json.get("headline"))
        current_status = request.form.get("current_status") or (request.json and request.json.get("current_status"))
        
        # Validate required fields.
        if not review_id or not rating or not headline or not current_status:
            logger.error("UpdateReview: Missing required fields in request")
            return "Invalid request body", 400
        
        # Build the gRPC request message. (Ensure these field names match your proto definitions.)
        update_request = UpdateJobReviewRequest(
            id=int(review_id),
            rating=float(rating),
            headline=headline,
            current_status=current_status
        )
        logger.debug("Sending UpdateJobReviewRequest: %s", update_request)
        
        # Call the gRPC method to update the review.
        update_response = job_reviews_client.UpdateJobReview(update_request)
        logger.debug("Received UpdateJobReviewResponse: %s", update_response)
        
        # If the response indicates success, return HTTP 200.
        return render_template("updateReview.html", update_response=update_response), 200
        
    except Exception as e:
        logger.exception("Internal server error during update review")
        return render_template("updateReview.html", update_response={"success": False, "message": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting API Interface on port 8082")
    app.run(host="0.0.0.0", port=8082)
