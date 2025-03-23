FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN PIP install psycopg2
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 50051

CMD ["python", "job-postings.py"]