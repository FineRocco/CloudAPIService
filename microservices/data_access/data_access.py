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
    Job, Review, JobPostingsResponse, JobReviewsResponse, CreateReviewResponse
)

DB_CONFIG = {
    "dbname": "mydatabase",
    "user": "myuser",
    "password": "mypassword",
    "host": "postgres_db",  # Docker service name
    "port": "5432"
}
            
class DataAccessService(data_access_pb2_grpc.DataAccessServiceServicer):
    def GetJobPostingsWithTitle(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)  # Permite acessar colunas pelo nome
            cursor.execute("SELECT * FROM jobs WHERE title = %s", (request.title,))
            rows = cursor.fetchall()

            # Transformando os resultados em objetos Job
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
            logger.error(f"Database error: {e}")
            return JobPostingsResponse(job=[])
        
    def GetJobPostingsWithTitleAndCity(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)  # Permite acessar colunas pelo nome
            cursor.execute("SELECT * FROM jobs WHERE title = %s AND location = %s", (request.title,request.city,))
            rows = cursor.fetchall()

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
            print(f"Database error: {e}")
            return JobPostingsResponse(job=[])


    def GetJobReviews(self, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reviews;")
            job_reviews = cursor.fetchone()[0] or 0.0  # Default to 0 if None
            cursor.close()
            conn.close()
            return JobReviewsResponse(review=job_reviews)
        except Exception as e:
            print("Database error:", e)
            return JobReviewsResponse(review=None)
        
    def GetJobReviewsWithTitleAndCity(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)  # Permite acessar colunas pelo nome
            cursor.execute(
                "SELECT * FROM reviews WHERE TRIM(job_title) = %s AND TRIM(location) = %s",
                (request.title, request.city,)
            )
            rows = cursor.fetchall()
            reviews = [
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
            print(f"Database error: {e}")
            return JobReviewsResponse(review=[])
        
    def CreateReview(self, request, context):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()

            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM reviews")
            next_id = cursor.fetchone()[0]

            review_data = {
                "id": next_id,
                "firm": request.review.firm or "",
                "job_title": request.review.job_title or "",
                "current": request.review.current or "",
                "location": request.review.location or "",
                "overall_rating": request.review.overall_rating or None,
                "work_life_balance": request.review.work_life_balance or None,
                "culture_values": request.review.culture_values or None,
                "diversity_inclusion": request.review.diversity_inclusion or None,
                "career_opp": request.review.career_opp or None,
                "comp_benefits": request.review.comp_benefits or None,
                "senior_mgmt": request.review.senior_mgmt or None,
                "recommend": request.review.recommend or "",
                "ceo_approv": request.review.ceo_approv or "",
                "outlook": request.review.outlook or "",
                "headline": request.review.headline or "",
                "pros": request.review.pros or "",
                "cons": request.review.cons or ""
            }

            cursor.execute("""
                INSERT INTO reviews (
                    id, firm, job_title, current, location, overall_rating, 
                    work_life_balance, culture_values, diversity_inclusion, 
                    career_opp, comp_benefits, senior_mgmt, recommend, 
                    ceo_approv, outlook, headline, pros, cons
                ) VALUES (
                    %(id)s, %(firm)s, %(job_title)s, %(current)s, %(location)s, %(overall_rating)s, 
                    %(work_life_balance)s, %(culture_values)s, %(diversity_inclusion)s, 
                    %(career_opp)s, %(comp_benefits)s, %(senior_mgmt)s, %(recommend)s, 
                    %(ceo_approv)s, %(outlook)s, %(headline)s, %(pros)s, %(cons)s
                )
            """, review_data)

            conn.commit()
            cursor.close()
            conn.close()

            return CreateReviewResponse(success="Review added successfully.")
        except Exception as e:
            print(f"Database error: {e}")
            return CreateReviewResponse(success="Failed to add review.")

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