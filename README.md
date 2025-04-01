# README

## Download Files
To use this project, you need to download some files. These files are available at the following link:

https://drive.google.com/drive/folders/10ftw6VcKtccCAF1b4SB4rbededgfqXB1?usp=sharing

## Setup
After downloading the files, place them in the `datasets` directory within the project.

## How to Run
To run the project, use the following command:

```sh
docker compose up --build
```

## To test each use case with the following links:

1. Search for remote jobs by city, keyword, or company
```sh
http://localhost:8082/jobs/search/remote
```
2. Search the average salary of a given job
```sh
http://localhost:8082/jobs/search/average-salary
```
3. Search for the best companies
```sh
http://localhost:8082/jobs/search/best-companies
```
4. Search for the best cities
```sh
http://localhost:8082/jobs/search/best-cities
```
5. Search for jobs, filtering by title and city
```sh
http://localhost:8082/jobs/search/jobs-with-rating
```
6. Search for jobs in the companies with the biggest number of employees
```sh
http://localhost:8082/jobs/search/jobs-in-biggest-companies
```
7. Search for companies with the highest average salary for a job title
```sh
http://localhost:8082/jobs/search/best-paying-companies
```
8. Adds a new job to the job posting database.
```sh
http://localhost:8082/jobs/post/job-posting
```
9. Post a new job review
```sh
http://localhost:8082/jobs/post/review-posting
```
10. Update a job review
```sh
http://localhost:8082/jobs/put/review-update
```
11. Delete a job review
```sh
http://localhost:8082/jobs/delete/review-deletion
```

## Observations:

1. The gRPC channels have a default limit of 4Mb capacity per call. Some use cases upgraded it to 10Mb but the data transfering from the microservice "Data-access" to the others is still slow because of datasets's size.
2. The datasets had empty data in some columns, we edited them so it could work in our project.
3. Also we added a primary unique key in the reviews dataset so it could be associated with the other dataset.