-- Create reviews table 
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY,
    firm TEXT,
    job_title TEXT,
    current TEXT,
    location TEXT,
    overall_rating INT,
    work_life_balance FLOAT,
    culture_values FLOAT,
    diversity_inclusion FLOAT,
    career_opp FLOAT,
    comp_benefits FLOAT,
    senior_mgmt FLOAT,
    recommend TEXT,
    ceo_approv TEXT,
    outlook TEXT,
    headline TEXT,
    pros TEXT,
    cons TEXT
);

-- Import data from CSV using PostgreSQL's COPY command
COPY reviews(id, firm, job_title, current, location, overall_rating, 
             work_life_balance, culture_values, diversity_inclusion, 
             career_opp, comp_benefits, senior_mgmt, recommend, 
             ceo_approv, outlook, headline, pros, cons)
FROM '/docker-entrypoint-initdb.d/job_reviews.csv'
DELIMITER ',' CSV HEADER;

-- Create jobs table
CREATE TABLE jobs (
    job_id BIGINT PRIMARY KEY,
    company TEXT,
    title TEXT,
    description TEXT,
    max_salary NUMERIC,
    pay_period TEXT,
    location TEXT,
    company_id FLOAT,
    views FLOAT,
    med_salary NUMERIC,
    min_salary NUMERIC,
    formatted_work_type TEXT,
    remote_allowed BOOLEAN,
    job_posting_url TEXT,
    aplication_url TEXT,
    application_type TEXT,
    formatted_Experience_level TEXT,
    skills_desc TEXT,
    posting_domain TEXT,
    sponsored BOOLEAN,
    work_type TEXT,
    currency TEXT,
    normalized_salary NUMERIC,
    zip_code FLOAT
);

-- Import data from CSV using PostgreSQL's COPY command
COPY jobs(
    job_id,
    company,
    title,
    description,
    max_salary,
    pay_period,
    location,
    company_id,
    views,
    med_salary,
    min_salary,
    formatted_work_type,
    remote_allowed,
    job_posting_url,
    aplication_url,
    application_type,
    formatted_Experience_level,
    skills_desc,
    posting_domain,
    sponsored,
    work_type,
    currency,
    normalized_salary,
    zip_code
)
FROM '/docker-entrypoint-initdb.d/job_postings.csv'
DELIMITER ',' CSV HEADER;

-- Create employee table
CREATE TABLE employee (
    company_id INTEGER,
    employee_count INTEGER,
    follower_count INTEGER
);

-- Import data from CSV using PostgreSQL's COPY command for employee
COPY employee(
    company_id,
    employee_count,
    follower_count
)
FROM '/docker-entrypoint-initdb.d/employee_counts.csv'
DELIMITER ',' CSV HEADER;


