FROM python:3.13

WORKDIR /app/data_access

COPY data_access/requirements.txt .
COPY data_access/data_access.py .
COPY data_access/data_access_pb2_grpc.py .
COPY data_access/data_access_pb2.py .


RUN pip install psycopg2
RUN pip install -r requirements.txt

EXPOSE 8083

CMD python3 data_access.py