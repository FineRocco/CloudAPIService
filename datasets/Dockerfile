# Use the official PostgreSQL image as the base
FROM postgres:16

# Copy the initialization script and CSV data into the
# /docker-entrypoint-initdb.d/ directory.
# Files in this directory are executed alphabetically when the container
# starts and finds an empty data directory.
COPY init.sql /docker-entrypoint-initdb.d/
COPY job_postings.csv /docker-entrypoint-initdb.d/
COPY job_reviews.csv /docker-entrypoint-initdb.d/
COPY employee_counts.csv /docker-entrypoint-initdb.d/

# The default PostgreSQL entrypoint will handle the rest
# (creating the DB, user, and running the scripts)