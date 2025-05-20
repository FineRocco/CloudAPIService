# Use an official PostgreSQL image as the base
# Using a specific version is recommended over 'latest' for stability
FROM postgres:16

# Set the working directory (optional, but good practice)
WORKDIR /docker-entrypoint-initdb.d/

# Copy the initialization script and CSV data files
# into the directory where PostgreSQL looks for init scripts.
COPY init.sql .
COPY job_reviews.csv .
COPY job_postings.csv .
COPY employee_counts.csv .

# PostgreSQL entrypoint will automatically execute init.sql
# when the database is initialized for the first time.
# The CSV files need to be in this directory for the COPY FROM commands to work.