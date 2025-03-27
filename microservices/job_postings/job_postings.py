import random, os
from concurrent import futures

import grpc
import jobpostings_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import AverageSalaryRequest, JobsWithRatingRequest
from data_access_pb2_grpc import DataAccessServiceStub
from jobpostings_pb2 import (
    AverageSalaryResponse,
    JobsWithRatingResponse
)

data_access_host = os.getenv("DATAACCESSHOST", "data-access")

job_postings_channel = grpc.insecure_channel(f"{data_access_host}:50051")
data_access_client = DataAccessServiceStub(job_postings_channel)

class JobPostingService(jobpostings_pb2_grpc.JobPostingServiceServicer):
    def AverageSalary(self, request, context):

        averageSalary_request = AverageSalaryRequest(title=request.title)

        averageSalary_response = data_access_client.GetAverageSalary(averageSalary_request)

        return AverageSalaryResponse(averageSalary=averageSalary_response.averageSalary)
    
    def JobsWithRating(self, request, context):
        
        jobs_with_rating_request = JobsWithRatingRequest(title=request.title, city=request.city)
        
        jobs_with_rating_response = data_access_client.GetJobsWihtTitleAndCity(jobs_with_rating_request)
        
        
        


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