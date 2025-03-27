#!/usr/bin/env python3
import os
import random
from concurrent import futures
import grpc
import psycopg2
import psycopg2.extras
import logging

import data_access_pb2_grpc
import data_access_pb2
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import Job, JobPostingsResponse, JobReviewsResponse

# Set up logging for debugging.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "dbname": "mydatabase",
    "user": "myuser",
    "password": "mypassword",
    "host": "postgres_db",  # Docker service name
    "port": "5432"
}

class DataAccessService(data_access_pb2_grpc.DataAccessServiceServicer):
    def GetJobPostings(self, request, context):
        logger.debug("GetJobPostings: Received request for title: %s", request.title)
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            logger.debug("GetJobPostings: Connected to database")
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute("SELECT * FROM jobs WHERE title = %s", (request.title,))
            rows = cursor.fetchall()
            logger.debug("GetJobPostings: Fetched %d rows", len(rows))

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
            logger.debug("GetJobPostings: Constructed %d job postings", len(job_postings))
            cursor.close()
            conn.close()

            return JobPostingsResponse(job=job_postings)
        except Exception as e:
            logger.error("GetJobPostings: Database error: %s", e)
            return JobPostingsResponse(job=[])

    def GetJobReviewsForCompanyReview(self, request, context):
        logger.debug("GetJobReviewsWithFirm: Received request with limit: %d, offset: %d", request.limit, request.offset)
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            logger.debug("GetJobReviewsWithFirm: Connected to database")
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                "SELECT * FROM reviews LIMIT %s OFFSET %s", 
                (request.limit, request.offset)
            )
            rows = cursor.fetchall()
            logger.debug("GetJobReviewsWithFirm: Fetched %d rows", len(rows))
            
            reviews = [
                # Assuming 'Review' is defined in data_access_pb2; adjust import if necessary.
                # If not, you might need to import it similarly to Job.
                # For this example, we're assuming the same module defines Review.
                data_access_pb2.Review(
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
            logger.debug("GetJobReviewsWithFirm: Constructed %d reviews", len(reviews))
            cursor.close()
            conn.close()
            return JobReviewsResponse(review=reviews)
        except Exception as e:
            logger.error("GetJobReviewsWithFirm: Database error: %s", e)
            return JobReviewsResponse(review=[])

def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    data_access_pb2_grpc.add_DataAccessServiceServicer_to_server(
        DataAccessService(), server
    )

    server.add_insecure_port("[::]:50051")
    logger.info("Server starting on [::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
