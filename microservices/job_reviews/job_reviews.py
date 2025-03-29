import random, os
from concurrent import futures
import grpc
import jobreviews_pb2_grpc
import jobreviews_pb2
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import JobReviewRequestWithTitleAndCity, CreateReviewRequest, Review, JobReviewsRequest, UpdateJobReviewRequest
from data_access_pb2_grpc import DataAccessServiceStub
from jobreviews_pb2 import (
    JobReview,
    JobWithRating,
    CalculateRatingResponse,
    CreateReviewResponse,
    BestCompaniesResponse,
    UpdateJobReviewResponse,
    BestRatingCity,
    BestCityResponse
)

data_access_host = os.getenv("DATAACCESSHOST", "data-access")
job_reviews_channel = grpc.insecure_channel(f"{data_access_host}:50051", options=[
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
    ('grpc.max_receive_message_length', 10 * 1024 * 1024)
])
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
        
        
    def GetBestCompanies(self, request, context):
        # Retrieve reviews in batches.
        all_reviews = []
        offset = 0
        limit = 42000  # Adjust this limit as needed.
        while True:
            paginatedRequest = JobReviewsRequest(
                limit=limit,
                offset=offset
            )
            jobReviewsResponse = data_access_client.GetJobReviewsForCompanyReview(paginatedRequest)
            batch_reviews = jobReviewsResponse.review
            if not batch_reviews:
                break
            all_reviews.extend(batch_reviews)
            if len(batch_reviews) < limit:
                break
            offset += limit

        # Debug 1: No reviews found.
        if not all_reviews:
            debug_company = jobreviews_pb2.CompanyReview(
                firm="DEBUG: NO REVIEWS FOUND",
                overall_rating=-100,
                work_life_balance=0.0,
                culture_values=0.0,
                diversity_inclusion=0.0,
                career_opp=0.0
            )
            return BestCompaniesResponse(companyReview=[debug_company])

        # Group reviews by firm.
        firm_reviews = {}
        for r in all_reviews:
            firm = r.firm
            if firm not in firm_reviews:
                firm_reviews[firm] = []
            firm_reviews[firm].append(r)

        # Debug 2: No firm grouping occurred.
        if not firm_reviews:
            debug_company = jobreviews_pb2.CompanyReview(
                firm="DEBUG: NO FIRM GROUPING",
                overall_rating=-101,
                work_life_balance=0.0,
                culture_values=0.0,
                diversity_inclusion=0.0,
                career_opp=0.0
            )
            return BestCompaniesResponse(companyReview=[debug_company])

        # For each firm, compute the average for each rating type.
        # The five ratings are: overall_rating, work_life_balance, culture_values, diversity_inclusion, career_opp.
        company_reviews = []  # Will store tuples of (overall_avg, CompanyReview)
        for firm, reviews_list in firm_reviews.items():
            count = len(reviews_list)
            total_overall = 0
            total_wlb = 0.0
            total_culture = 0.0
            total_diversity = 0.0
            total_career = 0.0

            for r in reviews_list:
                total_overall += r.overall_rating
                total_wlb += r.work_life_balance
                total_culture += r.culture_values
                total_diversity += r.diversity_inclusion
                total_career += r.career_opp

            avg_overall = total_overall / count
            avg_wlb = total_wlb / count
            avg_culture = total_culture / count
            avg_diversity = total_diversity / count
            avg_career = total_career / count

            # Compute an overall average across all five ratings (for sorting).
            overall_avg = (avg_overall + avg_wlb + avg_culture + avg_diversity + avg_career) / 5.0

            # Create a CompanyReview message.
            company_review = jobreviews_pb2.CompanyReview(
                firm=firm,
                overall_rating=int(round(avg_overall)),
                work_life_balance=avg_wlb,
                culture_values=avg_culture,
                diversity_inclusion=avg_diversity,
                career_opp=avg_career
            )
            company_reviews.append((overall_avg, company_review))

        # Debug 3: No companies computed.
        if not company_reviews:
            debug_company = jobreviews_pb2.CompanyReview(
                firm="DEBUG: NO COMPANY REVIEWS COMPUTED",
                overall_rating=-102,
                work_life_balance=0.0,
                culture_values=0.0,
                diversity_inclusion=0.0,
                career_opp=0.0
            )
            return BestCompaniesResponse(companyReview=[debug_company])

        # Sort the companies by overall average (descending) and pick the top 5.
        company_reviews.sort(key=lambda x: (x[0], x[1].firm), reverse=True)
        top_companies = [cr for _, cr in company_reviews[:5]]

        # Debug 4: Top companies list is empty.
        if not top_companies:
            debug_company = jobreviews_pb2.CompanyReview(
                firm="DEBUG: TOP COMPANIES EMPTY",
                overall_rating=-103,
                work_life_balance=0.0,
                culture_values=0.0,
                diversity_inclusion=0.0,
                career_opp=0.0
            )
            return BestCompaniesResponse(companyReview=[debug_company])

        return BestCompaniesResponse(companyReview=top_companies)

    def UpdateJobReview(self, request, context):
        # Create the update request message from the incoming request.
        update_req = UpdateJobReviewRequest(
            id=request.id,
            current_status=request.current_status,
            rating=request.rating,
            headline=request.headline
        )
        
        # Delegate the update to the data access client.
        update_resp = data_access_client.UpdateJobReview(update_req)
        
        return update_resp
    def BestCity(self, request, context):
        
        all_reviews = []
        offset = 0
        limit = 7000
        
        while True:
            paginatedRequest = JobReviewsRequest(
                limit=limit,
                offset=offset
            )
            jobReviewsResponse = data_access_client.GetJobReviewsForLocationReview(paginatedRequest)
            batch_reviews = jobReviewsResponse.review
            if not batch_reviews:
                break
            all_reviews.extend(batch_reviews)
            if len(batch_reviews) < limit:
                break
            offset += limit

        if all_reviews:
            # Create a dictionary to store the sum of ratings by city
            city_reviews = {}

            for review in all_reviews:
                city = review.location

                # Initialize the city in the dictionary if it doesn't exist
                if city not in city_reviews:
                    city_reviews[city] = {
                        "total_rating": 0,
                        "count": 0
                    }

                # Sum the ratings for each city
                city_reviews[city]["total_rating"] += (
                    review.overall_rating +
                    review.work_life_balance +
                    review.culture_values +
                    review.diversity_inclusion +
                    review.career_opp +
                    review.comp_benefits +
                    review.senior_mgmt
                )
                city_reviews[city]["count"] += 7 

            # Calculate the average for each city
            cities_with_avg = []
            for city, data in city_reviews.items():
                average_rating = data["total_rating"] / data["count"] if data["count"] > 0 else 0.0
                bestRatingCity = BestRatingCity(
                    city=city,
                    average_rating=average_rating
                )
                cities_with_avg.append(bestRatingCity)

            # Sort the cities by average rating (in descending order) and take the top 10
            top_10_cities = sorted(cities_with_avg, key=lambda x: x.average_rating, reverse=True)[:10]

            
            return BestCityResponse(city=top_10_cities)
        else:
            
            return BestCityResponse(city=[])

        
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
