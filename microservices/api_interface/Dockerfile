FROM python:3.13

WORKDIR /app/api_interface

COPY api_interface/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api_interface/ .

COPY job_postings/jobpostings_pb2.py .
COPY job_postings/jobpostings_pb2_grpc.py .

EXPOSE 8082

ENV FLASK_APP=api_interface.py
ENTRYPOINT [ "flask", "run", "--host=0.0.0.0"]