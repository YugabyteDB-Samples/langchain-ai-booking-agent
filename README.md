# LangChain AI Agent with YugabyteDB

## Local YugabyteDB deployment

1. Create a directory to store data locally.

   ```
   rm -rf ~/yb_docker_data
   mkdir ~/yb_docker_data
   ```

2. Create a Docker network.

   ```
   docker network create custom-network
   ```

3. Deploy a 3-node cluster to this network.

   ```
   docker run -d --name yugabytedb-node1 --net custom-network \
       -p 15433:15433 -p 7001:7000 -p 9001:9000 -p 5433:5433 \
       -v ~/yb_docker_data/node1:/home/yugabyte/yb_data --restart unless-stopped \
       yugabytedb/yugabyte:2.20.0.2-b1-aarch64 \
       bin/yugabyted start \
       --cloud_location=aws.us-east-1.us-east-1a \
       --fault_tolerance=region \
       --base_dir=/home/yugabyte/yb_data --background=false

   docker run -d --name yugabytedb-node2 --net custom-network \
       -p 15434:15433 -p 7002:7000 -p 9002:9000 -p 5434:5433 \
       -v ~/yb_docker_data/node2:/home/yugabyte/yb_data --restart unless-stopped \
       yugabytedb/yugabyte:2.20.0.2-b1-aarch64 \
       bin/yugabyted start --join=yugabytedb-node1 \
       --cloud_location=aws.us-central-1.us-central-1a \
       --fault_tolerance=region \
       --base_dir=/home/yugabyte/yb_data --background=false

   docker run -d --name yugabytedb-node3 --net custom-network \
       -p 15435:15433 -p 7003:7000 -p 9003:9000 -p 5435:5433 \
       -v ~/yb_docker_data/node3:/home/yugabyte/yb_data --restart unless-stopped \
       yugabytedb/yugabyte:2.20.0.2-b1-aarch64 \
       bin/yugabyted start --join=yugabytedb-node1 \
       --cloud_location=aws.us-west-1.us-west-1a \
       --fault_tolerance=region \
       --base_dir=/home/yugabyte/yb_data --background=false
   ```

## Adding data

1. Copy SQL files to Docker container.

   ```
   docker cp {project-root-directory}/sql/. yugabytedb-node1:/home/sql/
   ```

2. Load the schema and seed data with `schema.sql` and `data.sql`.

   ```
   docker exec -it yugabytedb-node1 bin/ysqlsh -h yugabytedb-node1 -f /home/sql/schema.sql
   docker exec -it yugabytedb-node1 bin/ysqlsh -h yugabytedb-node1 -f /home/sql/data.sql

   ```

3. Load the Airbnb dataset to the cluster (note, it can take a minute to load the data):
   ```
   docker exec -it yugabytedb-node1 bin/ysqlsh -h yugabytedb-node1 \
       -c "\copy airbnb_listings from /home/sql/airbnb_listings_with_embeddings.csv with DELIMITER '^' CSV"
   ```

## Running Backend Services

The backend consists of 2 Flask servers, one (`app.py`) for accepting chat messages from the UI to interact with an A.I. agent, and another (`api.py`) for communication betweeen the agent and the database.

1. Install application dependencies in a virtual environment.

```
cd {project-root-directory}/python-server/
python3 -m venv agent-application-env
source agent-application-env/bin/activate
pip install -r requirements.txt
# NOTE: Users with M1 Mac machines should use requirements-m1.txt instead:
# pip install -r requirements-m1.txt
```

2. Create an [OpenAI API Key](https://platform.openai.com/api-keys) and store it's value in a secure location. This will be used to connect the application to the LLM to generate SQL queries and an appropriate response from the database.

3. (Optional) Create a [Tavily API Key](https://docs.tavily.com/docs/gpt-researcher/getting-started) if you'd like to include search engine functionality in the A.I. agent.

4. Configure the application environment variables in {project_directory/.env.example} and include them in the same directory in a file named `.env`.

5. Run the application services in seperate terminal windows.

```
python app.py
* Running on http://127.0.0.1:3000
```

```
python api.py
* Running on http://127.0.0.1:8000
```

## Running UI

Install project dependencies and run the UI:

```
cd {project-root-directory}/langchain-agent-ui
npm install
npm run dev
```

By default, the UI will run on http://localhost:5173/ and proxies HTTP requests to http://localhost:3000 in `vite.config.js`.
