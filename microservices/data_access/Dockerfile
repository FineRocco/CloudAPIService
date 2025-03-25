FROM python:3.13

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc

COPY data_access/requirements.txt /app/data_access/
COPY data_access/data_access.py /app/data_access/
COPY data_access/protobuf /app/protobuf

WORKDIR /app/data_access
RUN pip install psycopg2
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m grpc_tools.protoc -I ../protobuf --python_out=. \
           --grpc_python_out=. ../protobuf/data-access.proto

EXPOSE 8083

CMD python3 data_access.py