from dotenv import load_dotenv
import requests
import json
import os
from datetime import datetime
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import StructuredTool
from langchain_core.tools import ToolException

from langchain import hub
# Load environment variables from .env file
load_dotenv()

# Used to print different styles to the terminal
from colorama import Fore, Back, Style, init
# Initialize Colorama
init()

def get_env_vars(*args):
    return [os.getenv(arg) for arg in args]

DB_HOST, DB_NAME, DB_USERNAME, DB_PASSWORD, DB_PORT, TAVILY_API_KEY = get_env_vars('DB_HOST', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD', 'DB_PORT', 'TAVILY_API_KEY')

# only needed if using the imported prompt
# from langchain import hub

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools.base import StructuredTool
from langchain_community.tools.tavily_search import TavilySearchResults
# from langchain.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def _handle_error(error: ToolException) -> str:
    return (
        "The following errors occurred during tool execution:"
        + error.args[0]
        + "Please try another tool."
    )

def get_listings(data):
    """this function makes an API call to a REST server to search listings.
    """

    # The URL for the API endpoint you want to call
    url = 'http://localhost:8000/api/listings'

    # print("This is the input variable to get_listings", data)

    # Making fa GET request to the Flask API
    response = requests.post(url, json=data)
    print("Data sent to get_listings:\n", data)
    # Checking if the request was successful
    if response.status_code == 200:
        # Getting JSON data from the response
        data = response.json()
        # print("Response from API:", data)
        return data
    else:
        print("Failed to retrieve data from API")

def create_booking(data):
    """this function makes an API call to a REST server to create a booking for a single listing"""
    # The URL for the API endpoint you want to call
    url = 'http://localhost:8000/api/bookings'

    # print("this is the input variable to create_booking", data)

    # Making fa POST request to the Flask API to create booking
    response = requests.post(url, json=data)

    return response.json()

def delete_booking(booking_id, customer_id):
    """this function makes an API call to a REST server to delete a booking"""
    # The URL for the API endpoint you want to call
    base_url = 'http://localhost:8000/api/bookings/{}'
    url = base_url.format(booking_id)

    # print(f"deleting booking with booking_id {booking_id}")

    params = {"customer_id": customer_id}
    # Making fa POST request to the Flask API to create booking
    response = requests.delete(url, params=params)

    # Process the response
    if response.status_code == 200:
        # print("Success:", response.json())
        return response.json()
    elif response.status_code == 404:
        print("Record not found:", response.json())
    else:
        print("Error:", response.json())

    return response.json()

def get_bookings(customer_id):
    """this function makes an API call to a REST server to retrieve bookings for a customer"""
    url="http://localhost:8000/api/bookings"
    params = {"customer_id": customer_id}

    response = requests.get(url, params)
    
    # Process the response
    if response.status_code == 200:
        return response.json()
        # print("Success:", response.json())
    elif response.status_code == 404:
        print("Record not found:", response.json())
    else:
        print("Error:", response.json())

    return response.json()

class GetListingsInput(BaseModel):
    data: object = Field(description="has two keys, 'query_params' and 'embedding_text'")
get_listings_tool = StructuredTool.from_function(
    func=get_listings,
    name="GetListings",
    description="retrieves listings from an API call",
    args_schema=GetListingsInput,
    handle_tool_error=_handle_error
)
class CreateBookingInput(BaseModel):
    data: object = Field(description="has 4 keys,'listing_id' and 'customer_id', 'start_date' and 'end_date'")
create_booking_tool = StructuredTool.from_function(
    func=create_booking,
    name="CreateBooking",
    description="creates a booking for a single listing",
    args_schema=CreateBookingInput,
    handle_tool_error=_handle_error
)

class DeleteBookingInput(BaseModel):
    booking_id: int = Field(description="the id for the listing")
    customer_id: int = Field(description="the id for the customer")
delete_booking_tool = StructuredTool.from_function(
    func=delete_booking,
    name="DeleteBooking",
    description="deletes a booking for a single listing",
    args_schema=DeleteBookingInput,
    handle_tool_error=_handle_error
)

class GetBookingsInput(BaseModel):
    customer_id: int = Field(description="the id for the customer whose bookings will be returned")
get_bookings_tool = StructuredTool.from_function(
    func=get_bookings,
    name="GetBookings",
    description="retrieves bookings for a single user",
    args_schema=GetBookingsInput,
    handle_tool_error=_handle_error
)

tools = [
    get_listings_tool,
    create_booking_tool,
    delete_booking_tool,
    get_bookings_tool,
]

if bool(TAVILY_API_KEY) is True:
    tools.append(TavilySearchResults(max_results=5))

# this is the schema for the database to be add to the system message to add context about columns
schema = """
airbnb_listings (
        listing_id bigint NOT NULL,
        name text,
        neighborhood_overview text,
        transit text,
        host_is_superhost boolean NOT NULL,
        street text NOT NULL,
        neighbourhood text NOT NULL,
        city text,
        state text,
        zipcode varchar(5),
        smart_location text NOT NULL,
        country_code varchar(2) NOT NULL,
        country text NOT NULL,
        latitude DECIMAL(7, 5) NOT NULL,
        longitude DECIMAL(8, 5) NOT NULL,
        property_type varchar(18) NOT NULL,
        room_type varchar(15) NOT NULL,
        accommodates integer NOT NULL,
        bathrooms DECIMAL(3, 1),
        bedrooms integer,
        beds integer,
        bed_type text NOT NULL,
        amenities text NOT NULL,
        square_feet varchar(4),
        price varchar(10) NOT NULL,
        weekly_price varchar(10),
        monthly_price varchar(11),
        security_deposit varchar(10),
        cleaning_fee varchar(8),
        extra_people text NOT NULL,
        minimum_nights integer NOT NULL,
        maximum_nights integer NOT NULL,
        minimum_minimum_nights integer NOT NULL,
        maximum_minimum_nights integer NOT NULL,
        minimum_maximum_nights integer NOT NULL,
        maximum_maximum_nights integer NOT NULL,
        minimum_nights_avg_ntm DECIMAL(11, 2) NOT NULL,
        maximum_nights_avg_ntm DECIMAL(11, 2) NOT NULL,
        calendar_updated text NOT NULL,
        has_availability boolean NOT NULL,
        availability_30 integer NOT NULL,
        availability_60 integer NOT NULL,
        availability_90 integer NOT NULL,
        availability_365 integer NOT NULL,
        calendar_last_scraped timestamp without time zone NOT NULL,
        review_scores_rating integer,
        review_scores_accuracy integer,
        review_scores_cleanliness integer,
        review_scores_checkin integer,
        review_scores_communication integer,
        review_scores_location integer,
        review_scores_value integer,
        is_business_travel_ready boolean NOT NULL,
        cancellation_policy text NOT NULL,
        description_embedding vector (1536),
        PRIMARY KEY (id);
"""
neighborhoods = "Alamo Square,Balboa Terrace,Bayview,Bernal Heights,Chinatown,Civic Center,Cole Valley,Cow Hollow,Crocker Amazon,Daly City,Diamond Heights,Dogpatch,Downtown,Duboce Triangle,Excelsior,Financial District,Fisherman's Wharf,Fisherman's Wharf,Forest Hill,Glen Park,Haight-Ashbury,Hayes Valley,Ingleside,Inner Sunset,Japantown,Lakeshore,Lower Haight,Marina,Mission Bay,Mission District,Mission Terrace,Nob Hill,Noe Valley,North Beach,Oceanview,Outer Sunset,Pacific Heights,Parkside,Portola,Potrero Hill,Presidio,Presidio Heights,Richmond District,Russian Hill,Sea Cliff,SoMa,South Beach,Sunnyside,Telegraph Hill,Tenderloin,The Castro,Twin Peaks,Union Square,Visitacion Valley,West Portal,Western Addition/NOPA"
sample_get_listings_call = """get_listings({'data': {'query_params': {'neighbourhood': {'value': 'Mission Bay', 'type': 'text'},'price': {'value': 200, 'type': 'currency', 'symbol': '<='}}, 'embedding_text': 'place near dining and nightlife.'}})"""
sample_create_booking_call = """create_booking({'data': {listing_id: 123, customer_id: 1, start_date: '2024-01-01', end_date: '2024-01-07'}})"""
sample_output = '{"summary": "Here are the results I found. Can I help you with anything else?", "results_to_display": ARRAY_OF_RESULTS}'
# Get the prompt to use - you can modify this!
# prompt = hub.pull("hwchase17/openai-tools-agent")

formatted_system_message = """
        You are a friendly travel agent, helping users to book accomodations and returing a single JSON object as output. 
        
        This output should be a valid JSON object. This output object has 2 two keys, "summary" and "results_to_display".
        "summary" explains what is being returned in 1 short paragraph, plus any friendly and relevant follow-up text or question.
        "results_to_display" is a list of results, if applicable. I.e. a list of responses returned from the database or a web search result.

        Do not provide text in markdown formatting. I.e. do not include any newline characters. '\n' should never be present in an output.
        Never include more than 1 JSON object in the output. I.e. do not include an additional object with "summary" and "results_to_display" in the output.
        Always return the output in this format:
        {sample_output}

        If a user asks for question that cannot be answered using the database, access the internet to find information about the city and its neighborhoods.

        Make sure that any arguments passed to a function are in the proper format.
        If using the get_listings function, be sure to pass a JSON object with keys "query_params" and "embedding_text". These keys are at the root level of this object. 
        The "embedding_text" key should NEVER be nested inside of the "query_params" object under any circumstances.
        
        "query_params" is an object with key-value pairs representing database columns and their values, to be used in a SQL query.
        Each key in query_params is mapped to an object with a "value" and a "type". 
        If type is "number" or "currency", a third key is added to this object, "symbol".
        
        Type must map to one of the following, based on their defined type in the schema listed below:
        "text", "number", "currency", "boolean"
                   
        Symbol must map to one of the following:
        "=", "<", "<=", ">", ">="

       The text key contains a string which will be used in the REST service to generate text embeddings
        "embedding_text" is a string used to generate text embeddings.
        WHEN CONSTRUCTING THE query_params DICTIONARY, KEYS MUST BE SPELLED EXACTLY HOW THEY ARE SPELLED IN THE SCHEMA BELOW. FOR INSTANCE: "neighbourhood", NOT "neighborhood".

        for instance, get_listings could be called like this:
        {sample_get_listings_call}

        Always use the embedding_text property to search for qualitative information about a listing.

        Only search using the "neighbourhood" column if you are sure that the user is asking to book in this neighborhood.
                   
        The neighbourhood values are as follows. Do not favor one value over another, just respond to the prompt as it is given:
        {neighborhoods}
                   
        If searching for a particular neighborhood, only use these values.
        
        This is the schema for the airbnb_listings table:
        {schema}
               
        Always keep the listing_id as part of the output. This is necessary to create, edit or delete a booking.
                   
        Use the create_booking_tool to create a booking, passing the listing_id, customer_id, start_date and end_date.
        The listing_id has to be a valid listing_id from one of the listings returned from the airbnb_listings table.
        This listing_id will be from one of the listings previously returned by the get_listings function.
        start_date and end_date must be in YYYY-MM-DD format.
        If no start_date and end_date are provided, ask the user what dates they'd like to book.
        Assume that the current customer is ID 1. If you need to get or delete bookings by customer_id, always set the value to 1.
        when getting bookings, always include the dates of the bookings.

        for instance, create_booking could be called like this:
        {sample_create_booking_call}

        Always output a JSON object with "summary" and "results_to_display".

        If a user asks for your functionality, provide a generic description of your abilities based on all of this information under the "summary" property.
        """.format(schema=schema, neighborhoods=neighborhoods, sample_get_listings_call=sample_get_listings_call, sample_create_booking_call=sample_create_booking_call, sample_output=sample_output)

# this is a customization of what is pulled down by hub.pull("hwchase17/openai-tools-agent")
prompt = ChatPromptTemplate.from_messages([ 
    SystemMessage(formatted_system_message),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"), 
    MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

# Choose the LLM that will drive the agent
# Only certain models support this
llm = ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0, model_kwargs={"response_format": {"type": "json_object"}})
# llm = ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0)
# llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)

# Construct the OpenAI Tools agent
agent = create_openai_tools_agent(llm, tools, prompt)

# Create an agent executor by passing in the agent and tools
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, return_intermediate_steps=True)

chat_history = []
NUM_OF_CHAT_MESSAGES_TO_SAVE = 10
def handle_agent_input(input_val):
    chat_history_length = len(chat_history)
    for i in range(0, chat_history_length-NUM_OF_CHAT_MESSAGES_TO_SAVE):
        chat_history.pop(0)

    result = agent_executor.invoke({"input": input_val, "chat_history": chat_history})
    humanInput = result["input"]
    output = result["output"]
    chat_history.append(HumanMessage(content=humanInput))
    chat_history.append(AIMessage(content=output))

    # gets the listing_id from the listings returned in the intermediate_steps
    # storing these in the chat_history makes them accessible in future prompts
    def extract_listing_id(obj):
        # in the case of the get_listings endpoint, results are returned as an array of objects
        return {"listing_id": obj["listing_id"]}
    def extract_booking_id_and_name(obj):
        # in the case of the get_listings endpoint, results are returned as an array of objects
        return {"booking_id": obj["booking_id"], "listing_name": obj["listing_name"]}
    
    try:
        if('intermediate_steps' in result):
            for i in range(0, len(result["intermediate_steps"])):
                if(result["intermediate_steps"][i][0].tool == 'GetListings'):
                    ids = map(extract_listing_id, json.loads(result["intermediate_steps"][i][1]['data']))
                    storedIds = f"These are the corresponding listing IDs for the returned listings: {list(ids)}"
                    chat_history.append(AIMessage(content=storedIds))
                    result["data_to_display"] = result["intermediate_steps"][i][1]['data'];

                if(result["intermediate_steps"][i][0].tool == 'GetBookings'):
                    ids = map(extract_booking_id_and_name, json.loads(result["intermediate_steps"][i][1]['data']))
                    storedIds = f"These are the corresponding booking IDs and listing names for the returned bookings: {list(ids)}"
                    chat_history.append(AIMessage(content=storedIds))
                    result["data_to_display"] = result["intermediate_steps"][i][1]['data']

        return result
    except IndexError:
        print("The requested index does not exist.")
    except:
        print("Error in getting information from intermediate_steps")