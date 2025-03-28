import os
import logging
import grpc
from flask import Flask,jsonify , request
from jobpostings_pb2 import AverageSalaryRequest
from jobpostings_pb2_grpc import JobPostingServiceStub
from jobreviews_pb2_grpc import JobReviewServiceStub
from jobreviews_pb2 import BestCityRequest
from jobpostings_pb2 import JobAddRequest

app = Flask(__name__)

# Configuração do logger
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
    
    return jsonify({
        "cities": [city for city in cities_response.city]
    }),200
    
    
@app.route("/AddJob", methods=["POST"])
def render_AddJob():
    logger.debug("Recebendo requisição para /AddJob")
    
    # Obter os dados do corpo da requisição (JSON)
    data = request.get_json()
    logger.debug(f"Dados recebidos: {data}")

    # Validar se todos os campos obrigatórios estão presentes
    if not data or not all(key in data for key in ["title", "normalized_salary", "company_name", "description", "location"]):
        logger.warning("Requisição inválida: campos obrigatórios ausentes")
        return jsonify({
            "message": "Invalid request: missing required fields.",
            "status": 400
        }), 400

    # Criar o JobAddRequest com os dados recebidos
    try:
        job_request = JobAddRequest(
            title=data["title"],
            normalized_salary=data["normalized_salary"],
            company_name=data["company_name"],
            description=data["description"],
            location=data["location"]
        )
        logger.debug(f"JobAddRequest criado: {job_request}")
    except Exception as e:
        logger.error(f"Erro ao criar JobAddRequest: {e}")
        return jsonify({
            "message": f"Error creating JobAddRequest: {e}",
            "status": 500
        }), 500

    # Chamar o serviço gRPC para adicionar o trabalho
    try:
        job_response = job_postings_client.AddJob(job_request)
        logger.debug(f"Resposta do serviço gRPC: {job_response}")
    except Exception as e:
        logger.error(f"Erro ao chamar o serviço gRPC: {e}")
        return jsonify({
            "message": f"Error calling gRPC service: {e}",
            "status": 500
        }), 500

    # Retornar a resposta
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
    
