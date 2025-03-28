FROM python:3.13

WORKDIR /app

COPY job_postings/requirements.txt /app/job_postings/
COPY job_postings/job_postings.py /app/job_postings/
COPY job_postings/protobuf /app/protobuf
COPY job_reviews/protobuf /app/protobuf
COPY data_access/protobuf /app/protobuf

WORKDIR /app/job_postings
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/jobpostings.proto
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/data-access.proto
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/jobreviews.proto

EXPOSE 8081

CMD ["python", "job_postings.py"]
