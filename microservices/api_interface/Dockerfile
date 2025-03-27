FROM python:3.13

WORKDIR /app

COPY api_interface/templates /app/api_interface/templates/
COPY api_interface/requirements.txt /app/api_interface/
COPY api_interface/api_interface.py /app/api_interface/
COPY job_postings/protobuf /app/protobuf
COPY job_reviews/protobuf /app/protobuf
#Maybe not necessary
COPY api_interface/protobuf /app/protobuf  

WORKDIR /app/api_interface
RUN pip install --no-cache-dir -r requirements.txt
#Maybe not necessary
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/api-interface.proto
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/jobpostings.proto
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/jobreviews.proto


EXPOSE 8082

ENV FLASK_APP=api_interface.py
ENTRYPOINT [ "flask", "run", "--host=0.0.0.0", "--port=8082"]