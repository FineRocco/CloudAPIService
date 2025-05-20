import os
import grpc
from flask import Flask, request, jsonify
from jobreviews_pb2 import BestCompaniesRequest, UpdateJobReviewRequest,DeleteReviewRequest,CreateReviewRequest, ReviewinJob, BestCityRequest
from jobpostings_pb2 import AverageSalaryRequest, BestPayingCompaniesRequest,  JobPostingsForLargestCompaniesRequest, JobsWithRatingRequest, JobAddRequest, RemoteJobSearchRequest
from jobpostings_pb2_grpc import JobPostingServiceStub
from jobreviews_pb2_grpc import JobReviewServiceStub

app = Flask(__name__)

jobreviews_host = os.getenv("JOBREVIEWSHOST", "job-reviews-service")
jobpostings_host = os.getenv("JOBPOSTINSHOST", "job-postings-service")

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

@app.route("/readyz") # Or /healthz
def readiness():
  return "OK", 200

@app.route("/healthz") # Good to have liveness too
def liveness():
  return "OK", 200

@app.route("/jobs/search/average-salary", methods=["GET"])
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



@app.route("/jobs/search/best-cities", methods=["GET"])
def render_location():
    cities_request = BestCityRequest()
    cities_response = job_reviews_client.BestCity(cities_request)
    
    # Convert Protobuf message objects to dictionaries
    city_list = []
    for city in cities_response.city:
        city_dict = {
            "name": city.city,
            "average_rating": city.average_rating
        }
        city_list.append(city_dict)
    
    return jsonify({"cities": city_list}), 200
    
    
@app.route("/jobs/post/job-posting", methods=["POST"])
def render_AddJob():
    
    data = request.get_json()
    
    if not data or not all(key in data for key in ["title", "normalized_salary", "company_name", "description", "location"]):
        return jsonify({
            "message": "Invalid request: missing required fields.",
            "status": 400
        }), 400

    try:
        job_request = JobAddRequest(
            title=data["title"],
            normalized_salary=data["normalized_salary"],
            company_name=data["company_name"],
            description=data["description"],
            location=data["location"]
        )
    except Exception as e:
        return jsonify({
            "message": f"Error creating JobAddRequest: {e}",
            "status": 500
        }), 500

    try:
        job_response = job_postings_client.AddJob(job_request)
    except Exception as e:
        return jsonify({
            "message": f"Error calling gRPC service: {e}",
            "status": 500
        }), 500

    return jsonify({
        "job_request": {
            "title": job_request.title,
            "normalized_salary": job_request.normalized_salary,
            "company_name": job_request.company_name,
            "description": job_request.description,
            "location": job_request.location
        },
        "job_response": {
            "message": job_response.message,
            "status": job_response.status
        }
    }), job_response.status
    
@app.route("/jobs/search/jobs-with-rating", methods=["GET"])
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
        {"title": job.job.title, "company": job.job.company_name, "salary": job.job.salary, "location": job.job.location, "views": job.job.views, "rating": job.rating, "description": job.job.description,}
        for job in jobsWithRating_response.jobs
    ]
    
    return jsonify({"jobs": jobs}), 200
    
@app.route("/jobs/post/review-posting", methods=["POST"])
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

@app.route("/jobs/search/best-companies", methods=["GET"])
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

@app.route("/jobs/search/jobs-in-biggest-companies", methods=["GET"])
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

@app.route("/jobs/put/review-update", methods=["PUT"])
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

@app.route("/jobs/search/remote", methods=["GET"])
def render_remoteJobs():
    
    company = request.args.get("company", "")
    city = request.args.get("city", "")
    keyword = request.args.get("keyword", "")

    if not company and not city and not keyword:
        return jsonify({"error": "Keyword, city or company are required"}), 400

    remoteJobsRequest = RemoteJobSearchRequest(company=company, city=city, keyword=keyword)
    remoteJobsResponse = job_postings_client.GetRemoteJobs(remoteJobsRequest)
    
    jobs = []
    for job in remoteJobsResponse.jobs:
        jobs.append({
            "id": job.id,
            "company": job.company,
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "remote_allowed": job.remote_allowed
        })
    
    return jsonify({
        "jobs": jobs
    }),200

@app.route('/jobs/search/best-paying-companies', methods=['GET'])
def render_best_paying_companies():
    job_title = request.args.get('title')

    if not job_title:
        return jsonify({"error": "Job title is required"}), 400

    try:

        best_paying_request = BestPayingCompaniesRequest(title=job_title)

        best_paying_response = job_postings_client.GetBestPayingCompanies(best_paying_request)

        companies = []
        for company in best_paying_response.companies:
            companies.append({
                "company_name": company.company_name,
                "average_salary": company.average_salary
            })

        return jsonify({
            "best_paying_companies": companies
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error fetching best paying companies: {str(e)}"}), 500


@app.route('/jobs/delete/review-deletion', methods=['DELETE'])
def render_delete_job_review():

    review_id = request.args.get('review_id')

    if not review_id:
        return jsonify({"error": "Review id is required"}), 400

    try:

        delete_review_request = DeleteReviewRequest(review_id=review_id)

        delete_response= job_reviews_client.DeleteReview(delete_review_request)

        delete_response1 = []
        delete_response1.append({
            "success": delete_response.success,
            "message": delete_response.message
        })


        return jsonify({
            "Response": delete_response1
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error deleting review: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
