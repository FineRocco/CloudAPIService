import random, os
from concurrent import futures
import logging

import grpc
import data_access_pb2
import jobpostings_pb2
import jobpostings_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import JobPostingsRequestWithTitle, JobPostingsRequest, CompaniesRequest
from data_access_pb2_grpc import DataAccessServiceStub
from jobpostings_pb2 import (
    AverageSalaryResponse, JobPostingsForLargestCompaniesResponse
)

# Set up logging.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

data_access_host = os.getenv("DATAACCESSHOST", "data-access")

job_postings_channel = grpc.insecure_channel(f"{data_access_host}:50051", options=[
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
    ('grpc.max_receive_message_length', 10 * 1024 * 1024)
])
data_access_client = DataAccessServiceStub(job_postings_channel)

class JobPostingService(jobpostings_pb2_grpc.JobPostingServiceServicer):
    def AverageSalary(self, request, context):
        
        jobPostingRequest = JobPostingsRequestWithTitle(title=request.title)

        jobPostingsResponse = data_access_client.GetJobPostings(jobPostingRequest)

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

    def GetJobPostingsForLargestCompanies(self, request, context):
        logger.debug("GetJobPostingsForLargestCompanies called")

        # Step 1: Retrieve companies with employees.
        companies_request = data_access_pb2.CompaniesRequest()  # No fields needed.
        logger.debug("Sending CompaniesRequest to get companies with employees")
        companies_response = data_access_client.GetCompaniesWithEmployees(companies_request)
        companies = companies_response.company  # A list of Company messages.
        logger.debug("Retrieved %d companies", len(companies))
        
        if not companies:
            logger.debug("No companies found in GetCompaniesWithEmployees; returning empty response")
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
        
        logger.debug("Top %d unique companies (by employee_count): %s", 
                    len(top_companies), [c.company_id for c in top_companies])
        
        # Step 3: For each top company, retrieve job postings in batches.
        all_job_postings = []
        limit = 30000  # Adjust this limit as needed.
        for company in top_companies:
            offset = 0
            company_id = company.company_id
            logger.debug("Starting batch retrieval for company_id: %s", company_id)
            while True:
                logger.debug("Preparing paginated request for company_id %s with limit %d and offset %d", company_id, limit, offset)
                # Create a paginated request including a filter by company_id.
                paginatedRequest = data_access_pb2.JobPostingsRequest(
                    company_id=company_id,
                    limit=limit,
                    offset=offset
                )
                logger.debug("Sending paginated request for company_id %s", company_id)
                jobPostingsResponse = data_access_client.GetJobPostingsForLargestCompanies(paginatedRequest)
                logger.debug("Received paginated response for company_id %s, offset %d", company_id, offset)
                
                batch_jobs = jobPostingsResponse.job
                logger.debug("Retrieved %d job postings for company_id %s at offset %d", len(batch_jobs), company_id, offset)
                
                if not batch_jobs:
                    logger.debug("No more job postings for company_id %s at offset %d; breaking loop", company_id, offset)
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

                logger.debug("Accumulated %d job postings so far", len(all_job_postings))
                
                if len(batch_jobs) < limit:
                    logger.debug("Batch size (%d) is less than limit (%d) for company_id %s; ending batch retrieval", len(batch_jobs), limit, company_id)
                    break
                
                offset += limit
                logger.debug("Incremented offset to %d for company_id %s", offset, company_id)

        logger.debug("Total job postings retrieved for top companies: %d", len(all_job_postings))
        
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