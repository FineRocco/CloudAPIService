import os

import grpc
from flask import Flask, request, jsonify
from jobpostings_pb2 import AverageSalaryRequest, JobsWithRatingRequest
from jobpostings_pb2_grpc import JobPostingServiceStub
from jobreviews_pb2 import (
    CreateReviewRequest,
    ReviewinJob
)
from jobreviews_pb2_grpc import JobReviewServiceStub

app = Flask(__name__)

jobpostings_host = os.getenv("JOBPOSTINSHOST", "job-postings")
jobpostings_channel = grpc.insecure_channel(f"{jobpostings_host}:50051")
job_postings_client = JobPostingServiceStub(jobpostings_channel)

jobreviews_host = os.getenv("JOBREVIEWHOST", "job-reviews")
job_reviews_channel = grpc.insecure_channel(f"{jobreviews_host}:50051")
job_reviews_client = JobReviewServiceStub(job_reviews_channel)

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