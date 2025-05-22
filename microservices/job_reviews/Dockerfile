FROM python:3.13

WORKDIR /app

COPY microservices/job_reviews/requirements.txt /app/job_reviews/
COPY microservices/job_reviews/job_reviews.py /app/job_reviews/
COPY microservices/job_reviews/protobuf/jobreviews.proto /app/protobuf
COPY microservices/data_access/protobuf/data-access.proto /app/protobuf/

WORKDIR /app/job_reviews
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/jobreviews.proto
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/data-access.proto

EXPOSE 8084

CMD ["python", "job_reviews.py"]