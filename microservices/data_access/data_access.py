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

class DataAccess:
    def __init__(self, host="localhost", port=5432, database="mydatabase", user="myuser", password="mypassword"):
        self.conn_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
    
    def _get_connection(self):
        """Create and return a new database connection."""
        return psycopg2.connect(**self.conn_params)
    
    def fetch_jobs(self):
        """Fetch all rows from the jobs table."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM jobs LIMIT 1;")
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()
    
    def fetch_jobs_by_title(self, title):
        """Fetch all rows from the jobs table with a certain title."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE title = %s;", (title,))
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()
        
    
    def fetch_reviews(self):
        """Fetch all rows from the reviews table."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM reviews LIMIT 1;")
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()

    def fetch_employee(self):
        """Fetch all rows from the reviews table."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM employee LIMIT 1;")
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()
            
class GetAverageSalary(data_access_pb2_grpc.DataAccessServiceServicer):
    def GetAverageSalary(self, request, context):
        da = DataAccess()
            
        jobs = da.fetch_jobs_by_title(request.title)
            
        if jobs:
            avg_salary = sum(job["med_salary"] for job in jobs if job["med_salary"] is not None) / len(jobs)
        else:
            avg_salary = 0
            
        return AverageSalaryResponse(salary=avg_salary)
        
def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    data_access_pb2_grpc.add_DataAccessServiceServicer_to_server(
        GetAverageSalary(), server
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