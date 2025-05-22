FROM python:3.13

WORKDIR /app

COPY microservices/api_interface/requirements.txt /app/api_interface/
COPY microservices/api_interface/api_interface.py /app/api_interface/
COPY microservices/job_postings/protobuf/jobpostings.proto /app/protobuf
COPY microservices/job_reviews/protobuf/jobreviews.proto /app/protobuf

WORKDIR /app/api_interface
RUN mkdir -p ./protobuf
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m grpc_tools.protoc -I ./protobuf --python_out=. \
           --grpc_python_out=. ./protobuf/jobpostings.proto
RUN python -m grpc_tools.protoc -I ./protobuf --python_out=. \
           --grpc_python_out=. ./protobuf/jobreviews.proto


EXPOSE 8082

ENV FLASK_APP=api_interface.py
ENTRYPOINT [ "flask", "run", "--host=0.0.0.0", "--port=8082"]