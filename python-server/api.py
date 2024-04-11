from dotenv import load_dotenv
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import time
# Load environment variables from .env file
load_dotenv()

def get_env_vars(*args):
    return [os.getenv(arg) for arg in args]

DB_HOST, DB_NAME, DB_USERNAME, DB_PASSWORD, DB_PORT = get_env_vars('DB_HOST', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD', 'DB_PORT')
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USERNAME,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

def get_embedding(embedding_text: str):
    """this function generates text embeddings to be used in PostgreSQL database queries with pgvector"""
    # startTime = time.time()
    response = embeddings.embed_query(embedding_text)
    # print("Duration getting embeddings: ", time.time() - startTime)
    # print("length of embeddings response: ", len(response))
    # This returns a list of embeddings; we assume one input text for simplicity
    return response

from flask import Flask, jsonify

app = Flask(__name__)

# Define a custom error handler for 404 Not Found errors
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource not found"}), 404

# Define a custom error handler for 500 Internal Server Error
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "An unexpected error occurred"}), 500


def create_airbnb_select_query(filters, embedding):
    query_base = "SELECT listing_id,name,description,price,neighbourhood FROM airbnb_listings"
    query_conditions = []
    params = []

    if(len(filters) > 0):
        for key, value in filters.items():
            # For each key-value pair, add a condition to the list

            if(hasattr(value, "symbol")):
                symbol = value["symbol"]
            else:
                symbol = "="

            if(value['type'] == "text"):
                # notice the double %% used to escape the % character in this case
                # this executes a similarity search on the text using pg_trgm
                query_conditions.append(f"{key} %% %s")
            elif(value['type'] == 'number'):
                query_conditions.append(f"{key} {symbol} %s")
            elif(value['type'] == 'currency'):
                query_conditions.append(f"{key}::MONEY::NUMERIC {symbol} %s")
            elif(value['type'] == 'boolean'):
                query_conditions.append(f"{key} = %s")

            # query_conditions.append(f"{key} = %s")
            params.append(value['value'])
            
        query_base += ' WHERE '
        # Join all conditions with 'AND' and combine with the base query
        query = query_base + ' AND '.join(query_conditions)

    if embedding != None:
        if 'query' in locals(): 
            query += ' ORDER BY '
        else:    
            query = query_base + ' ORDER BY '
        query += 'description_embedding <=> %s::vector'
        params.append(embedding) 

    query += ' LIMIT 5'


    return {"query": query, "params": params}



# Home route
@app.route('/')
def home():
    return "Welcome to the REST Server running on port 8000!"

@app.route('/api/listings', methods=['POST'])
def get_listings():
    data = request.get_json()  # Get data sent in request body
    # Perform operations with the data (this example just returns it)

    # print("this is is the data object in /api/data")
    # print(data)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    embedding = None
    if 'embedding_text' in data: 
        embedding = get_embedding(data["embedding_text"])
    # query = "SELECT name, description from airbnb_listings ORDER BY description_embedding <=> %s::vector LIMIT 5"
    query_and_params = create_airbnb_select_query(data.get("query_params", {}), embedding)
    print("query_and_params: ", query_and_params)
    cur.execute(query_and_params["query"], query_and_params["params"])
    rows = cur.fetchall()
    # Optionally, convert to JSON
    rows_json = json.dumps(rows, default=str)  # `default=str` to handle datetime and other non-serializable types
    print(rows_json)
    cur.close()
    return jsonify({"data": rows_json, "status": "this is the response from the get listings endpoint"})

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if 'start_date' in data and 'end_date' in data:
        query = "INSERT INTO bookings (listing_id, customer_id, start_date, end_date) VALUES(%s, %s, %s, %s) RETURNING *"
        cur.execute(query, [data["listing_id"], data["customer_id"], data["start_date"], data["end_date"]])
    else:
        query = "INSERT INTO bookings (listing_id, customer_id) VALUES(%s, %s) RETURNING *"
        cur.execute(query, [data["listing_id"], data["customer_id"]])
    
    rows = cur.fetchone()
    rows_json = json.dumps(rows, default=str)
    conn.commit()
    cur.close()
    return jsonify({"data": rows_json, "status": "this is the response from the bookings endpoint"})

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    customer_id = request.args.get('customer_id', None, type=int)
    if customer_id is None:
        query = "select booking_id, airbnb_listings.name as listing_name from bookings JOIN airbnb_listings ON bookings.listing_id = airbnb_listings.listing_id;"
    else:
        query = "select booking_id, customer_id, start_date, end_date, airbnb_listings.name as listing_name, airbnb_listings.price as listing_price, airbnb_listings.neighbourhood as listing_neighborhood from bookings JOIN airbnb_listings ON bookings.listing_id = airbnb_listings.listing_id where customer_id = %s;"
        params = [customer_id]

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(query, params)
    rows = cur.fetchall()
    # Optionally, convert to JSON
    rows_json = json.dumps(rows, default=str)  # `default=str` to handle datetime and other non-serializable types
    print(rows_json)
    cur.close()
    return jsonify({"data": rows_json, "status": "this is the response from the get bookings endpoint"})

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    customer_id = request.args.get('customer_id', None, type=int)
    if customer_id is None:
        return {"error": "Missing customer_id query parameter"}, 400
    
    cur = conn.cursor()
    query = "DELETE FROM bookings where booking_id = %s AND customer_id = %s RETURNING booking_id"
    cur.execute(query, [booking_id, customer_id])
    deleted_record = cur.fetchone()
    conn.commit()
    cur.close()
    return jsonify({"data": deleted_record, "status": "this is the response from the delete bookings endpoint"})

if __name__ == '__main__':
    app.run(port=8000, debug=True)