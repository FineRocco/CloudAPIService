import random, os
from concurrent import futures


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
        if not request.title or not request.company_name or not request.description or not request.location or request.normalized_salary is None:
            return JobAddResponse(
                message="Invalid request: missing required fields.",
                status=400
            )

        job_request = PostJobRequest(
            title=request.title,
            normalized_salary=request.normalized_salary,
            company_name=request.company_name,
            description=request.description,
            location=request.location
        )
        try:
            job_response = data_access_client.PostJobInDB(job_request)
        except Exception as e:
            return JobAddResponse(
                message=f"Error calling DataAccessService: {e}",
                status=500
            )
        
        # Verificar se a inserção/atualização foi bem-sucedida
        if job_response.status == 200:
            return JobAddResponse(
                message="Job added successfully",
                status=201  # Success code (201 - Created)
            )
        else:
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
