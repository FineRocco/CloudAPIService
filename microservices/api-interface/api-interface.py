import os

import grpc
from flask import Flask, render_template, request
from jobpostings_pb2 import AverageSalaryRequest
from jobpostings_pb2_grpc import JobPostingServiceStub

app = Flask(__name__)

jobpostings_host = os.getenv("JOBPOSTINSHOST", "localhost")
getbook_host = os.getenv("GETBOOK_HOST", "localhost")
""" with open("client.key", "rb") as fp:
    client_key = fp.read()
with open("client.pem", "rb") as fp:
    client_cert = fp.read()
with open("ca.pem", "rb") as fp:
    ca_cert = fp.read()
creds = grpc.ssl_channel_credentials(ca_cert, client_key, client_cert) """
jobpostings_channel = grpc.insecure_channel(f"{jobpostings_host}:50051")
job_postings_client = JobPostingServiceStub(jobpostings_channel)

@app.route("/")
def render_homepage():
    averageSalary_request = AverageSalaryRequest(
        title="Marketing Coordinator"
    )
    averageSalary_response = job_postings_client.AverageSalary(
        averageSalary_request
    )
    return render_template(
        "homepage.html",
        recommendations=recommendations_response.recommendations,
    )