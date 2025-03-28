import os
import grpc
from flask import Flask,jsonify , request
from jobpostings_pb2_grpc import JobPostingServiceStub
from jobreviews_pb2_grpc import JobReviewServiceStub
from jobreviews_pb2 import BestCityRequest
from jobpostings_pb2 import JobAddRequest

app = Flask(__name__)

jobpostings_host = os.getenv("JOBPOSTINSHOST", "job-postings")
jobpostings_channel = grpc.insecure_channel(f"{jobpostings_host}:50051")
job_postings_client = JobPostingServiceStub(jobpostings_channel)

# Conectar ao serviço de Job Reviews (para pegar as melhores cidades)
jobreviews_host = os.getenv("JOBREVIEWSHOST", "job-reviews")
jobreviews_channel = grpc.insecure_channel(f"{jobreviews_host}:50051")
job_reviews_client = JobReviewServiceStub(jobreviews_channel)


@app.route("/location", methods=["GET"])
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
    
    
@app.route("/AddJob", methods=["POST"])
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
    
if __name__ == "__main__":
    app.run(debug=True)
    
