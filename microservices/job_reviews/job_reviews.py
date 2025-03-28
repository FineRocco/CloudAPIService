import random, os
from concurrent import futures

import grpc
import jobreviews_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import JobReviewRequestWithTitleAndCity, CreateReviewRequest, Review
from data_access_pb2_grpc import DataAccessServiceStub
from jobreviews_pb2 import (
    JobReview,
    JobWithRating,
    CalculateRatingResponse,
    CreateReviewResponse
)

data_access_host = os.getenv("DATAACCESSHOST", "data-access")

job_reviews_channel = grpc.insecure_channel(f"{data_access_host}:50051")
data_access_client = DataAccessServiceStub(job_reviews_channel)

class JobReviewService(jobreviews_pb2_grpc.JobReviewServiceServicer):
    def CalculateRating(self, request, context):
        
        jobsWithRating = []
        
        for job in request.jobs:
            jobReviewRequest = JobReviewRequestWithTitleAndCity(title=job.title, city=job.location)
            jobReviewResponse = data_access_client.GetJobReviewsWithTitleAndCity(jobReviewRequest)
            
            jobRatingTotal = 0.0
            count = 0
            for jobReview in jobReviewResponse.review:
                total = 0
                howMany = 0
                if(jobReview.work_life_balance != 0):
                    total += int(jobReview.work_life_balance)
                    howMany += 1
                if(jobReview.culture_values != 0):
                    total += int(jobReview.culture_values)
                    howMany += 1                    
                if(jobReview.diversity_inclusion != 0):
                    total += int(jobReview.diversity_inclusion)
                    howMany += 1
                if(jobReview.career_opp != 0):
                    total += int(jobReview.career_opp)
                    howMany += 1
                if(jobReview.comp_benefits != 0):
                    total += int(jobReview.comp_benefits)
                    howMany += 1
                if(jobReview.senior_mgmt != 0):
                    total += int(jobReview.senior_mgmt)
                    howMany += 1
                if(howMany > 0):
                    jobRatingTotal += (total/howMany)
                    count +=1
            overall_rating = jobRatingTotal / count if count > 0 else 0
            
            jobWithRating = JobWithRating(
                rating=int(overall_rating),  # Assuming the rating is an integer
                job= JobReview (
                    id=str(job.id), 
                    title=str(job.title),
                    company_name=str(job.company_name),
                    description=str(job.description),
                    location=str(job.location),
                    views=int(job.views)
                )
            )
            
            jobsWithRating.append(jobWithRating)
            
        return CalculateRatingResponse(rating=jobsWithRating)
    
    def CreateReview(self, request, context):
        
        review =  Review(
            firm=request.review.firm if request.review.firm else "",  # Default to empty string if not provided
            job_title=request.review.job_title if request.review.job_title else "",
            current=request.review.current if request.review.current else "",
            location=request.review.location if request.review.location else "",
            overall_rating=request.review.overall_rating if request.review.overall_rating != 0 else 0,
            work_life_balance=request.review.work_life_balance if request.review.work_life_balance != 0 else 0.0,
            culture_values=request.review.culture_values if request.review.culture_values != 0 else 0.0,
            diversity_inclusion=request.review.diversity_inclusion if request.review.diversity_inclusion != 0 else 0.0,
            career_opp=request.review.career_opp if request.review.career_opp != 0 else 0.0,
            comp_benefits=request.review.comp_benefits if request.review.comp_benefits != 0 else 0.0,
            senior_mgmt=request.review.senior_mgmt if request.review.senior_mgmt != 0 else 0.0,
            recommend=request.review.recommend if request.review.recommend else "",
            ceo_approv=request.review.ceo_approv if request.review.ceo_approv else "",
            outlook=request.review.outlook if request.review.outlook else "",
            headline=request.review.headline if request.review.headline else "",
            pros=request.review.pros if request.review.pros else "",
            cons=request.review.cons if request.review.cons else ""
        )
        
        createReviewRequest = CreateReviewRequest(review=review)
        createReviewResponse = data_access_client.CreateReview(createReviewRequest)
        
        return CreateReviewResponse(success=createReviewResponse.success)
        
        

def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    jobreviews_pb2_grpc.add_JobReviewServiceServicer_to_server(
        JobReviewService(), server
    )

    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()