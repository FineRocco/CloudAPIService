import random, os
from concurrent import futures

import grpc
import data_access_pb2
import jobpostings_pb2
import jobpostings_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from jobreviews_pb2 import CalculateRatingRequest, JobReview
from jobreviews_pb2_grpc import JobReviewServiceStub
from data_access_pb2 import JobPostingsRequestWithTitle, JobPostingsRequestWithTitleAndCity, JobPostingsRequest, CompaniesRequest
from data_access_pb2_grpc import DataAccessServiceStub
from jobpostings_pb2 import (
    Job,
    JobWithRating,
    AverageSalaryResponse,
    JobsWithRatingResponse,
    JobPostingsForLargestCompaniesResponse
)



data_access_host = os.getenv("DATAACCESSHOST", "data-access")
job_review_host = os.getenv("JOBREVIEWHOST", "job-reviews")

job_review_posting_channel = grpc.insecure_channel(f"{job_review_host}:50051")

job_postings_channel = grpc.insecure_channel(f"{data_access_host}:50051", options=[
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
    ('grpc.max_receive_message_length', 10 * 1024 * 1024)
])
data_access_client = DataAccessServiceStub(job_postings_channel)
job_review_client = JobReviewServiceStub(job_review_posting_channel)

class JobPostingService(jobpostings_pb2_grpc.JobPostingServiceServicer):
    def AverageSalary(self, request, context):
        
        jobPostingRequest = JobPostingsRequestWithTitle(title=request.title)

        jobPostingsResponse = data_access_client.GetJobPostingsWithTitle(jobPostingRequest)

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

    def JobsWithRating(self, request, context):
        
        jobPostingRequest = JobPostingsRequestWithTitleAndCity(title=request.title,city=request.city)
        
        jobPostingsResponse = data_access_client.GetJobPostingsWithTitleAndCity(jobPostingRequest)
        
        jobToSendToReviews = []
        
        for job in jobPostingsResponse.job:
            job_proto = JobReview(  
                id=str(job.job_id), 
                title=str(job.title),
                company_name=str(job.company),
                description=str(job.description),
                location=str(job.location),
                views=int(job.views)
            )

            
            jobToSendToReviews.append(job_proto)
            
        jobsWithRatings = []
            
        if len(jobToSendToReviews) != 0:
            calculateRatingRequest = CalculateRatingRequest(jobs=jobToSendToReviews)
            
            calculateRatingResponse = job_review_client.CalculateRating(calculateRatingRequest)
            
            for i, job_with_rating in enumerate(calculateRatingResponse.rating):
                jobWithRating = JobWithRating(
                    rating=job_with_rating.rating,  
                    job= Job(
                        id=str(job_with_rating.job.id), 
                        title=str(job_with_rating.job.title),
                        company_name=str(job_with_rating.job.company_name),
                        description=str(job_with_rating.job.description),
                        location=str(job_with_rating.job.location),
                        views=int(job_with_rating.job.views)
                    )
                )
                jobsWithRatings.append(jobWithRating)

        
        return JobsWithRatingResponse(jobs=jobsWithRatings)
        
    def GetJobPostingsForLargestCompanies(self, request, context):
        # Step 1: Retrieve companies with employees.
        companies_request = data_access_pb2.CompaniesRequest()
        companies_response = data_access_client.GetCompaniesWithEmployees(companies_request)
        companies = companies_response.company
        
        if not companies:
            return jobpostings_pb2.JobPostingsForLargestCompaniesResponse(job=[])
        
        # Step 2: Sort companies by employee_count (descending)
        companies.sort(key=lambda c: c.employee_count, reverse=True)
        
        # Step 3: Find top 5 unique companies
        seen_company_ids = set()
        top_companies = []
        
        for company in companies:
            # Skip companies with invalid or zero company_id
            if not company.company_id:
                continue
                
            # If we haven't seen this company before, add it to our top companies
            if company.company_id not in seen_company_ids:
                seen_company_ids.add(company.company_id)
                top_companies.append(company)
                
            # Once we have 5 unique companies, we can stop
            if len(top_companies) == 5:
                break
        
        # Step 3: For each top company, retrieve job postings in batches.
        all_job_postings = []
        limit = 30000  # Adjust this limit as needed.
        for company in top_companies:
            offset = 0
            company_id = company.company_id
            while True:
                # Create a paginated request including a filter by company_id.
                paginatedRequest = data_access_pb2.JobPostingsRequest(
                    company_id=company_id,
                    limit=limit,
                    offset=offset
                )
                jobPostingsResponse = data_access_client.GetJobPostingsForLargestCompanies(paginatedRequest)
                
                batch_jobs = jobPostingsResponse.job
                
                if not batch_jobs:
                    break

                # Convert data_access_pb2.JobForLargestCompany to jobpostings_pb2.JobForLargestCompany
                for job in batch_jobs:
                    # Create a new instance of jobpostings_pb2.JobForLargestCompany
                    job_obj = jobpostings_pb2.JobForLargestCompany(
                        company=job.company,
                        title=job.title,
                        description=job.description,
                        location=job.location,
                        company_id=job.company_id,
                        med_salary=job.med_salary
                    )
                    all_job_postings.append(job_obj)
                
                if len(batch_jobs) < limit:
                    break
                
                offset += limit

        return jobpostings_pb2.JobPostingsForLargestCompaniesResponse(job=all_job_postings)

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