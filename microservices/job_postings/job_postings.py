import random, os
from concurrent import futures

import grpc
import jobpostings_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from jobreviews_pb2 import CalculateRatingRequest, JobReview
from jobreviews_pb2_grpc import JobReviewServiceStub
from data_access_pb2 import JobPostingsRequestWithTitle, JobPostingsRequestWithTitleAndCity
from data_access_pb2_grpc import DataAccessServiceStub
from jobpostings_pb2 import (
    Job,
    JobWithRating,
    AverageSalaryResponse,
    JobsWithRatingResponse
)

data_access_host = os.getenv("DATAACCESSHOST", "data-access")
job_review_host = os.getenv("JOBREVIEWHOST", "job-reviews")

job_postings_channel = grpc.insecure_channel(f"{data_access_host}:50051")
job_review_posting_channel = grpc.insecure_channel(f"{job_review_host}:50051")

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