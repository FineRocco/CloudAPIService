#!/usr/bin/env python3
import psycopg2
import psycopg2.extras
import random, os
from concurrent import futures
import grpc
import data_access_pb2
import data_access_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import (
    Job, Review, JobReviewsResponse, PostJobResponse
)


DB_CONFIG = {
    "dbname": "mydatabase",
    "user": "myuser",
    "password": "mypassword",
    "host": "postgres_db",  # Docker service name
    "port": "5432"
}
            
class DataAccessService(data_access_pb2_grpc.DataAccessServiceServicer):
    def GetJobReviewsForCompanyReview(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                "SELECT * FROM reviews LIMIT %s OFFSET %s", 
                (request.limit, request.offset)
            )
            rows = cursor.fetchall()
            
            reviews = [
                # Assuming 'Review' is defined in data_access_pb2; adjust import if necessary.
                # If not, you might need to import it similarly to Job.
                # For this example, we're assuming the same module defines Review.
                Review(
                    id=row["id"],
                    firm=row["firm"],
                    job_title=row["job_title"],
                    current=row["current"],
                    location=row["location"],
                    overall_rating=row["overall_rating"] if row["overall_rating"] is not None else 0,
                    work_life_balance=row["work_life_balance"] if row["work_life_balance"] is not None else 0.0,
                    culture_values=row["culture_values"] if row["culture_values"] is not None else 0.0,
                    diversity_inclusion=row["diversity_inclusion"] if row["diversity_inclusion"] is not None else 0.0,
                    career_opp=row["career_opp"] if row["career_opp"] is not None else 0.0,
                    comp_benefits=row["comp_benefits"] if row["comp_benefits"] is not None else 0.0,
                    senior_mgmt=row["senior_mgmt"] if row["senior_mgmt"] is not None else 0.0,
                    recommend=row["recommend"],
                    ceo_approv=row["ceo_approv"],
                    outlook=row["outlook"],
                    headline=row["headline"],
                    pros=row["pros"],
                    cons=row["cons"]
                )
                for row in rows
            ]
            cursor.close()
            conn.close()
            return JobReviewsResponse(review=reviews)
        except Exception as e:
            return JobReviewsResponse(review=[])
        
    def PostJobInDB(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()

            job_id = self.generate_unique_job_id(cursor)

            cursor.execute("""
                INSERT INTO jobs (job_id, title, company, description, location, normalized_salary)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                job_id,
                request.title,
                request.company_name,
                request.description,
                request.location,
                request.normalized_salary,
            ))

            # Commit para persistir as alterações
            conn.commit()

            cursor.close()
            conn.close()

            # Retornar a resposta de sucesso
            return data_access_pb2.PostJobResponse(
                message="Job successfully inserted",
                status=200
            )

        except Exception as e:
            return data_access_pb2.PostJobResponse(
                message=f"Erro ao atualizar ou inserir o trabalho: {e}",
                status=500
            )

    def generate_unique_job_id(self, cursor):
        """Gera um ID único para o trabalho."""
        while True:
            # Gerar um ID aleatório
            new_id = random.randint(1, 999999)  # Exemplo: ID de 4 dígitos
            cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (new_id,))
            if not cursor.fetchone():
                return new_id
        
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
