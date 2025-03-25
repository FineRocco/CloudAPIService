import random, os
from concurrent import futures

import grpc
import jobpostings_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import AverageSalaryRequest
from data_access_pb2_grpc import DataAccessServiceStub
from jobpostings_pb2 import (
    AverageSalaryResponse
)

data_access_host = os.getenv("DATAACCESSHOST", "localhost")
getbook_host = os.getenv("GETBOOK_HOST", "localhost")
""" with open("client.key", "rb") as fp:
    client_key = fp.read()
with open("client.pem", "rb") as fp:
    client_cert = fp.read()
with open("ca.pem", "rb") as fp:
    ca_cert = fp.read()
creds = grpc.ssl_channel_credentials(ca_cert, client_key, client_cert) """
job_postings_channel = grpc.insecure_channel(f"{data_access_host}:50051")
averageSalary_client = DataAccessServiceStub(job_postings_channel)

class AverageSalaryService(jobpostings_pb2_grpc.JobPostingServiceServicer):
    def AverageSalary(self, request, context):
        averageSalary_request = AverageSalaryRequest(request.title)
        averageSalary_response = averageSalary_client.GetAverageSalary(averageSalary_request)
        return AverageSalaryResponse(averageSalary=averageSalary_response.salary)

def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    jobpostings_pb2_grpc.add_JobPostingServiceServicer_to_server(
        AverageSalaryService(), server
    )
    """ with open("server.key", "rb") as fp:
        server_key = fp.read()
    with open("server.pem", "rb") as fp:
        server_cert = fp.read()
    with open("ca.pem", "rb") as fp:
        ca_cert = fp.read()

    creds = grpc.ssl_server_credentials(
        [(server_key, server_cert)],
        root_certificates=ca_cert,
        require_client_auth=True,
    )  """
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()