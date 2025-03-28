import os
import grpc
from flask import Flask, request, jsonify
from jobreviews_pb2 import BestCompaniesRequest, UpdateJobReviewRequest,CreateReviewRequest, ReviewinJob
from jobpostings_pb2 import AverageSalaryRequest, JobPostingsForLargestCompaniesRequest, JobsWithRatingRequest
from jobpostings_pb2_grpc import JobPostingServiceStub
from jobreviews_pb2_grpc import JobReviewServiceStub

app = Flask(__name__)

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

@app.route("/averageSalary", methods=["GET"])
def render_homepage():
    title = request.args.get("title", "")
    
    if not title:
        return jsonify({"error": "Title is required"}), 400


    averageSalary_request = AverageSalaryRequest(
        title=title
    )

    averageSalary_response = job_postings_client.AverageSalary(
        averageSalary_request
    )
    
    return jsonify({"averageSalary": averageSalary_response.averageSalary}), 200
    
@app.route("/jobsWithRating", methods=["GET"])
def render_jobsWithRating():
    title = request.args.get("title", "")
    city = request.args.get("city", "")

    if not title or not city:
        return jsonify({"error": "Title and city are required"}), 400

    jobsWithRating_request = JobsWithRatingRequest(
        title=title, city=city
    )

    jobsWithRating_response = job_postings_client.JobsWithRating(
        jobsWithRating_request
    )
    
    jobs = [
        {"title": job.job.title, "company": job.job.company_name, "description": job.job.description, "location": job.job.location, "views": job.job.views, "rating": job.rating}
        for job in jobsWithRating_response.jobs
    ]
    
    return jsonify({"jobs": jobs}), 200
    
@app.route("/addJobReview", methods=["POST"])
def render_addJobReview():
    data = request.get_json()

    required_fields = ["firm", "job_title", "location", "overall_rating", "pros", "cons"]
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    review = ReviewinJob(
        firm=data["firm"],
        job_title=data["job_title"],
        location=data["location"],
        overall_rating=data["overall_rating"],
        pros=data["pros"],
        cons=data["cons"],

        current=data.get("current", ""),
        work_life_balance=data.get("work_life_balance", 0.0),
        culture_values=data.get("culture_values", 0.0),
        diversity_inclusion=data.get("diversity_inclusion", 0.0),
        career_opp=data.get("career_opp", 0.0),
        comp_benefits=data.get("comp_benefits", 0.0),
        senior_mgmt=data.get("senior_mgmt", 0.0),
        recommend=data.get("recommend", ""),
        ceo_approv=data.get("ceo_approv", ""),
        outlook=data.get("outlook", ""),
        headline=data.get("headline", ""),
    )

    createJobReview_request = CreateReviewRequest(
        review=review
    )

    createJobReview_response = job_reviews_client.CreateReview(
        createJobReview_request
    )
    
    return jsonify({"success": createJobReview_response.success}), 200

@app.route("/bestCompanies", methods=["GET"])
def render_bestCompanies():
    bestCompanies_request = BestCompaniesRequest()
    bestCompanies_response = job_reviews_client.GetBestCompanies(bestCompanies_request)
    
    # Convert protobuf message to Python list for JSON serialization
    companies = []
    for company in bestCompanies_response.companyReview:
        companies.append({
            "firm": company.firm,
            "overall_rating": company.overall_rating,
            "work_life_balance": company.work_life_balance,
            "culture_values": company.culture_values,
            "diversity_inclusion": company.diversity_inclusion,
            "career_opp": company.career_opp
        })
    
    return jsonify({
        "bestCompanies": companies
    }),200

@app.route("/jobsForLargestCompanies", methods=["GET"])
def render_jobsForLargestCompanies():
    jobsForLargestCompanies_request = JobPostingsForLargestCompaniesRequest()
    jobsForLargestCompanies_response = job_postings_client.GetJobPostingsForLargestCompanies(jobsForLargestCompanies_request)
    
    # Convert protobuf message to Python list for JSON serialization
    jobs = []
    for job in jobsForLargestCompanies_response.job:
        jobs.append({
            "company": job.company,
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "company_id": job.company_id,
            "med_salary": job.med_salary
        })
    
    return jsonify({
        "jobs": jobs
    }),200

@app.route("/updateReview", methods=["PUT"])
def update_review():
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
            return jsonify({"error": "Missing required fields"}), 400
        
        # Build the gRPC request message. (Ensure these field names match your proto definitions.)
        update_request = UpdateJobReviewRequest(
            id=int(review_id),
            rating=float(rating),
            headline=headline,
            current_status=current_status
        )
        
        # Call the gRPC method to update the review.
        update_response = job_reviews_client.UpdateJobReview(update_request)
        
        # Return JSON response
        return jsonify({
            "success": True,
            "message": "Review updated successfully",
            "data": {
                "id": review_id,
                "rating": rating,
                "headline": headline,
                "current_status": current_status
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"Internal server error: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
