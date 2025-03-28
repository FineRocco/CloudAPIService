import random, os
from concurrent import futures

import grpc
import jobreviews_pb2_grpc
import jobreviews_pb2
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from data_access_pb2 import JobReviewsRequest, UpdateJobReviewRequest
from data_access_pb2_grpc import DataAccessServiceStub
from jobreviews_pb2 import BestCompaniesResponse, UpdateJobReviewResponse

data_access_host = os.getenv("DATAACCESSHOST", "data-access")
job_reviews_channel = grpc.insecure_channel(f"{data_access_host}:50051", options=[
    ('grpc.max_send_message_length', 10 * 1024 * 1024),
    ('grpc.max_receive_message_length', 10 * 1024 * 1024)
])
data_access_client = DataAccessServiceStub(job_reviews_channel)

class JobReviewService(jobreviews_pb2_grpc.JobReviewServiceServicer):
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