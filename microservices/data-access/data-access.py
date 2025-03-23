#!/usr/bin/env python3
import psycopg2
import psycopg2.extras

class DataAccess:
    def __init__(self, host="localhost", port=5432, database="mydatabase", user="myuser", password="mypassword"):
        self.conn_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
    
    def _get_connection(self):
        """Create and return a new database connection."""
        return psycopg2.connect(**self.conn_params)
    
    def fetch_jobs(self):
        """Fetch all rows from the jobs table."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM jobs LIMIT 1;")
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()
    
    def fetch_reviews(self):
        """Fetch all rows from the reviews table."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM reviews LIMIT 1;")
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()

    def fetch_employee(self):
        """Fetch all rows from the reviews table."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM employee LIMIT 1;")
                rows = cur.fetchall()
                return rows
        finally:
            conn.close()

def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors
    )
    jobpostings_pb2_grpc.add_JobPostingServiceServicer_to_server(
        AverageSalaryService(), server
    )
    """ with open("server.key", "rb") as fp:
        server_key = fp.read()
    with open("server.pem", "rb") as fp:
        server_cert = fp.read()
    with open("ca.pem", "rb") as fp:
        ca_cert = fp.read()

    creds = grpc.ssl_server_credentials(
        [(server_key, server_cert)],
        root_certificates=ca_cert,
        require_client_auth=True,
    )  """
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()




if __name__ == '__main__':
    da = DataAccess()
    serve()