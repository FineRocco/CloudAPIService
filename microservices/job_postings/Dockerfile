FROM python:3.13

WORKDIR /app

COPY microservices/job_postings/requirements.txt /app/job_postings/
COPY microservices/job_postings/job_postings.py /app/job_postings/
COPY microservices/job_postings/protobuf/jobpostings.proto /app/protobuf/
COPY microservices/job_reviews/protobuf/jobreviews.proto /app/protobuf/
COPY microservices/data_access/protobuf/data-access.proto /app/protobuf/

WORKDIR /app/job_postings
RUN mkdir -p ./protobuf
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m grpc_tools.protoc -I../protobuf --python_out=. --grpc_python_out=. ../protobuf/jobpostings.proto
RUN python -m grpc_tools.protoc -I../protobuf --python_out=. --grpc_python_out=. ../protobuf/jobreviews.proto
RUN python -m grpc_tools.protoc -I../protobuf --python_out=. --grpc_python_out=. ../protobuf/data-access.proto

EXPOSE 8081

CMD ["python", "job_postings.py"]
