import random, os
from concurrent import futures

import grpc
import jobreviews_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
#from data_access_pb2 import AverageSalaryRequest, JobsWithRatingRequest
from data_access_pb2_grpc import DataAccessServiceStub
#from jobreviews_pb2 import (
    #AverageSalaryResponse,
    #JobsWithRatingResponse
#)

data_access_host = os.getenv("DATAACCESSHOST", "data-access")

job_reviews_channel = grpc.insecure_channel(f"{data_access_host}:50051")
data_access_client = DataAccessServiceStub(job_reviews_channel)

class JobReviewService(jobreviews_pb2_grpc.JobReviewServiceServicer):
    def test():
        return None
        
        
        


def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    jobreviews_pb2_grpc.add_JobReviewServiceServicer_to_server(
        JobReviewService(), server
    )

    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()