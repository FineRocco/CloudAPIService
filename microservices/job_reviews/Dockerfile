FROM python:3.13

WORKDIR /app

COPY job_reviews/requirements.txt /app/job_reviews/
COPY job_reviews/job_reviews.py /app/job_reviews/
COPY job_reviews/protobuf /app/protobuf
COPY data_access/protobuf /app/protobuf

WORKDIR /app/job_reviews
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/jobreviews.proto
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/data-access.proto

EXPOSE 8084

CMD ["python", "job_reviews.py"]