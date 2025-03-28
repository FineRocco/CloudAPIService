#!/usr/bin/env python3
import os
import random
from concurrent import futures
import grpc
import psycopg2
import psycopg2.extras

import data_access_pb2_grpc
import data_access_pb2
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import Job, JobForLargestCompany, JobPostingsResponse, JobReviewsResponse, CompaniesResponse, UpdateJobReviewResponse, JobPostingsForLargestCompaniesResponse

DB_CONFIG = {
    "dbname": "mydatabase",
    "user": "myuser",
    "password": "mypassword",
    "host": "postgres_db",  # Docker service name
    "port": "5432"
}

class DataAccessService(data_access_pb2_grpc.DataAccessServiceServicer):
    def GetJobPostings(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute("SELECT * FROM jobs WHERE title = %s", (request.title,))
            rows = cursor.fetchall()

            # Transform rows into Job objects.
            job_postings = [
                Job(
                    job_id=row["job_id"],
                    company=row["company"],
                    title=row["title"],
                    description=row["description"],
                    max_salary=row["max_salary"] or 0.0,
                    pay_period=row["pay_period"],
                    location=row["location"],
                    company_id=row["company_id"] or 0.0,
                    views=row["views"] or 0.0,
                    med_salary=row["med_salary"] or 0.0,
                    min_salary=row["min_salary"] or 0.0,
                    formatted_work_type=row["formatted_work_type"],
                    remote_allowed=row["remote_allowed"],
                    job_posting_url=row["job_posting_url"],
                    aplication_url=row["aplication_url"],
                    application_type=row["application_type"],
                    formatted_experience_level=row["formatted_experience_level"],
                    skills_desc=row["skills_desc"],
                    posting_domain=row["posting_domain"],
                    sponsored=row["sponsored"],
                    work_type=row["work_type"],
                    currency=row["currency"],
                    normalized_salary=row["normalized_salary"] or 0.0,
                    zip_code=row["zip_code"] or 0.0
                )
                for row in rows
            ]
            cursor.close()
            conn.close()

            return JobPostingsResponse(job=job_postings)
        except Exception as e:
            return JobPostingsResponse(job=[])

    def GetJobPostingsForLargestCompanies(self, request, context):
        try:
            # Connect to the database.
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Execute the SQL query.
            query = (
                "SELECT company, title, description, location, company_id, med_salary "
                "FROM jobs WHERE company_id = %s LIMIT %s OFFSET %s"
            )
            params = (request.company_id, request.limit, request.offset)
            cursor.execute(query, params)
            
            # Fetch the results.
            rows = cursor.fetchall()
            
            # Transform rows into JobForLargestCompany objects.
            job_postings = []
            for idx, row in enumerate(rows):
                job_obj = JobForLargestCompany(
                    company=row["company"],
                    title=row["title"],
                    description=row["description"],
                    location=row["location"],
                    company_id=int(row["company_id"]) if row["company_id"] is not None else 0,
                    med_salary=float(row["med_salary"]) if row["med_salary"] is not None else 0.0
                )
                job_postings.append(job_obj)
            
            # Close the cursor and connection.
            cursor.close()
            conn.close()
            
            return JobPostingsForLargestCompaniesResponse(job=job_postings)
        except Exception as e:
            return JobPostingsForLargestCompaniesResponse(job=[])

    def GetCompaniesWithEmployees(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute("SELECT * FROM employee;")
            rows = cursor.fetchall()
            
            company = [
                data_access_pb2.Company(
                    company_id=row["company_id"] if row["company_id"] is not None else 0,
                    employee_count=row["employee_count"] if row["employee_count"] is not None else 0,
                    follower_count=row["follower_count"] if row["follower_count"] is not None else 0,
                )
                for row in rows
            ]
            cursor.close()
            conn.close()
            return CompaniesResponse(company=company)
        except Exception as e:
            return CompaniesResponse(company=[])

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
                data_access_pb2.Review(
                    firm=row["firm"],
                    overall_rating=row["overall_rating"] if row["overall_rating"] is not None else 0,
                    work_life_balance=row["work_life_balance"] if row["work_life_balance"] is not None else 0.0,
                    culture_values=row["culture_values"] if row["culture_values"] is not None else 0.0,
                    diversity_inclusion=row["diversity_inclusion"] if row["diversity_inclusion"] is not None else 0.0,
                    career_opp=row["career_opp"] if row["career_opp"] is not None else 0.0,
                )
                for row in rows
            ]
            cursor.close()
            conn.close()
            return JobReviewsResponse(review=reviews)
        except Exception as e:
            return JobReviewsResponse(review=[])

    def UpdateJobReview(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            update_query = """
                UPDATE reviews
                SET current = %s,
                    overall_rating = %s,
                    headline = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (request.current_status, request.rating, request.headline, request.id))
            conn.commit()
            rowcount = cursor.rowcount
            cursor.close()
            conn.close()
            
            if rowcount == 0:
                return UpdateJobReviewResponse(success=False, message="Review not found")
            else:
                return UpdateJobReviewResponse(success=True, message="Review updated successfully")
        
        except Exception as e:
            return UpdateJobReviewResponse(success=False, message=str(e))

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