FROM python

WORKDIR /app

COPY requirements.txt .
COPY data-access.py .
COPY data_access_pb2_grpc.py .
COPY data_access_pb2.py .


RUN pip install psycopg2
RUN pip install -r requirements.txt

EXPOSE 8083

CMD python3 data-access.py