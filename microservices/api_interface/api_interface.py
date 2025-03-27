import os

import grpc
from flask import Flask, render_template, request
from jobpostings_pb2 import AverageSalaryRequest
from jobpostings_pb2_grpc import JobPostingServiceStub
from jobreviews_pb2_grpc import JobReviewServiceStub
from jobreviews_pb2 import BestCityRequest

app = Flask(__name__)

jobpostings_host = os.getenv("JOBPOSTINSHOST", "job-postings")
jobpostings_channel = grpc.insecure_channel(f"{jobpostings_host}:50051")
job_postings_client = JobPostingServiceStub(jobpostings_channel)

# Conectar ao serviço de Job Reviews (para pegar as melhores cidades)
jobreviews_host = os.getenv("JOBREVIEWSHOST", "job-reviews")
jobreviews_channel = grpc.insecure_channel(f"{jobreviews_host}:50051")
job_reviews_client = JobReviewServiceStub(jobreviews_channel)

@app.route("/")
def render_homepage():


    averageSalary_request = AverageSalaryRequest(
        title="Marketing Coordinator"
    )

    averageSalary_response = job_postings_client.AverageSalary(
        averageSalary_request
    )
    
    return render_template(
        "homepage.html",
        averageSalary_response=averageSalary_response.averageSalary
    )
    
@app.route("/location")
def render_location():
    cities_request = BestCityRequest()
    cities_response = job_reviews_client.BestCity(cities_request)
    
    return render_template(
        "location.html",
        cities=cities_response.city
    )
    
if __name__ == "__main__":
    app.run(debug=True)
    
