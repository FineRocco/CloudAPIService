import random, os
from concurrent import futures

import grpc
import jobreviews_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
#from data_access_pb2 import AverageSalaryRequest, JobsWithRatingRequest
from data_access_pb2_grpc import DataAccessServiceStub
from data_access_pb2 import  JobReviewsRequest
from jobreviews_pb2 import  BestRatingCity, BestCityResponse


data_access_host = os.getenv("DATAACCESSHOST", "data-access")

job_reviews_channel = grpc.insecure_channel(f"{data_access_host}:50051")
data_access_client = DataAccessServiceStub(job_reviews_channel)

class JobReviewService(jobreviews_pb2_grpc.JobReviewServiceServicer):
    def BestCity(self, request, context):
        
        all_reviews = []
        offset = 0
        limit = 7000
        
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

        if all_reviews:
            # Criar um dicionário para armazenar a soma das avaliações por cidad
            city_reviews = {}

            for review in all_reviews:
                city = review.location

                # Inicializa a cidade no dicionário se não existir
                if city not in city_reviews:
                    city_reviews[city] = {
                        "total_rating": 0,
                        "count": 0
                    }

                # Soma as avaliações para cada cidade
                city_reviews[city]["total_rating"] += (
                    review.overall_rating +
                    review.work_life_balance +
                    review.culture_values +
                    review.diversity_inclusion +
                    review.career_opp +
                    review.comp_benefits +
                    review.senior_mgmt
                )
                city_reviews[city]["count"] += 7  # Contando todos os atributos das avaliações

            # Calcular a média para cada cidade
            cities_with_avg = []
            for city, data in city_reviews.items():
                average_rating = data["total_rating"] / data["count"] if data["count"] > 0 else 0.0
                bestRatingCity = BestRatingCity(
                    city=city,
                    average_rating=average_rating
                )
                cities_with_avg.append(bestRatingCity)

            # Ordenar as cidades pela média de avaliações (em ordem decrescente) e pegar as top 10
            
            top_10_cities = sorted(cities_with_avg, key=lambda x: x.average_rating, reverse=True)[:10]

            # Retornar as top 10 cidades
            return BestCityResponse(city=top_10_cities)
        else:
            # Se não houver reviews, retornar uma lista vazia
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
