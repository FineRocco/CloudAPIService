import random, os
from concurrent import futures
import logging

# Configuração do logger
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

import grpc
import jobpostings_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import JobPostingsRequestWithTitle, PostJobRequest
from data_access_pb2_grpc import DataAccessServiceStub
from jobpostings_pb2 import (
    AverageSalaryResponse  ,JobAddResponse,
)



data_access_host = os.getenv("DATAACCESSHOST", "data-access")

job_postings_channel = grpc.insecure_channel(f"{data_access_host}:50051")
data_access_client = DataAccessServiceStub(job_postings_channel)

class JobPostingService(jobpostings_pb2_grpc.JobPostingServiceServicer):
    def AverageSalary(self, request, context):
        
        jobPostingRequest = JobPostingsRequestWithTitle(title=request.title)

        jobPostingsResponse = data_access_client.GetJobPostings(jobPostingRequest)

        total = 0
        count = 0
        avg = 0.0

        for job in jobPostingsResponse.job:
            if job.title == request.title:
                total += job.normalized_salary
                count += 1

        if count > 0:
            avg = total / count

        return AverageSalaryResponse(averageSalary=avg)
    
    def AddJob(self, request, context):
        logger.debug("Recebendo requisição para AddJob")
        
        # Validar se todos os campos obrigatórios estão presentes
        if not request.title or not request.company_name or not request.description or not request.location or request.normalized_salary is None:
            logger.warning("Requisição inválida: campos obrigatórios ausentes")
            return JobAddResponse(
                message="Invalid request: missing required fields.",
                status=400
            )
        
        logger.debug(f"Dados recebidos: title={request.title}, company_name={request.company_name}, "
                     f"description={request.description}, location={request.location}, "
                     f"normalized_salary={request.normalized_salary}")
        
        # Criar o PostJobRequest com os dados recebidos
        job_request = PostJobRequest(
            title=request.title,
            normalized_salary=request.normalized_salary,
            company_name=request.company_name,
            description=request.description,
            location=request.location
        )
        logger.debug(f"PostJobRequest criado: {job_request}")
        
        # Chamar o serviço DataAccessService para inserir ou atualizar o trabalho no banco de dados
        try:
            job_response = data_access_client.PostJobInDB(job_request)
            logger.debug(f"Resposta do serviço DataAccessService: {job_response}")
        except Exception as e:
            logger.error(f"Erro ao chamar o serviço DataAccessService: {e}")
            return JobAddResponse(
                message=f"Error calling DataAccessService: {e}",
                status=500
            )
        
        # Verificar se a inserção/atualização foi bem-sucedida
        if job_response.status == 200:
            logger.info("Trabalho adicionado com sucesso")
            return JobAddResponse(
                message="Job added successfully",
                status=201  # Success code (201 - Created)
            )
        else:
            logger.error(f"Erro ao adicionar o trabalho: {job_response.message}")
            return JobAddResponse(
                message=f"Error adding the job: {job_response.message}",
                status=500
            )
        
def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    jobpostings_pb2_grpc.add_JobPostingServiceServicer_to_server(
        JobPostingService(), server
    )

    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
