#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

import random, os
from concurrent import futures
import grpc
import data_access_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import (
    AverageSalaryResponse
)

DB_CONFIG = {
    "dbname": "mydatabase",
    "user": "myuser",
    "password": "mypassword",
    "host": "postgres_db",  # Docker service name
    "port": "5432"
}
            
class DataAccessService(data_access_pb2_grpc.DataAccessServiceServicer):
    def GetAverageSalary(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT AVG(normalized_salary) FROM jobs WHERE normalized_salary IS NOT NULL AND title = %s",(request.title,))
            avg_salary = cursor.fetchone()[0] or 0.0  # Default to 0 if None
            cursor.close()
            conn.close()
            return AverageSalaryResponse(averageSalary=avg_salary)
        except Exception as e:
            print("Database error:", e)
            return AverageSalaryResponse(averageSalary=0.0)
        
def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    data_access_pb2_grpc.add_DataAccessServiceServicer_to_server(
        DataAccessService(), server
    )

    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()