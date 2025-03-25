FROM python:3.13

WORKDIR /app/job_postings

COPY job_postings/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY job_postings/ .

COPY data_access/data_access_pb2.py .
COPY data_access/data_access_pb2_grpc.py .

EXPOSE 8081

CMD ["python", "job_postings.py"]
