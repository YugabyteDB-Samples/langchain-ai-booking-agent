import { useEffect, useState } from "react";
import "./App.css";
import { TypeAnimation } from "react-type-animation";
import React from "react";
import axios from "axios";
import { useMutation, QueryClient, QueryClientProvider } from "react-query";
import Markdown from "react-markdown";
import { DataGrid } from "@mui/x-data-grid";
import CircularProgress from "@mui/material/CircularProgress";

// Initialize a query client
const queryClient = new QueryClient();

// Function to perform the POST request
const postChat = async (inputVal) => {
  const { data } = await axios.post("http://localhost:3000/api/chat", {
    input_val: inputVal,
  });
  return data;
};

const DataTable = ({ data }) => {
  const [tableColumns, setTableColumns] = useState([]);
  const [tableData, setTableData] = useState([]);
  useEffect(() => {
    if (data) {
      const results = data.results_to_display;
      if (results?.[0]) {
        const columns = Object.keys(results[0]);
        setTableColumns(
          columns.map((col) => {
            if (col === "description") {
              return { field: col, headerName: col, flex: 1 };
            } else {
              return { field: col, headerName: col, width: 200 };
            }
          })
        );
        const parsedResults = results?.map((result) => {
          const resultKeys = Object.keys(result);
          resultKeys.forEach((resultKey) => {
            if (typeof result[resultKey] === "object") {
              result[resultKey] = JSON.stringify(result[resultKey]);
            }
          });

          return result;
        });
        setTableData(parsedResults);
      } else {
        setTableColumns([]);
        setTableData([]);
      }
    }
  }, [data]);
  return (
    <DataGrid
      rows={tableData}
      columns={tableColumns}
      getRowId={() => Math.random()}
      getRowHeight={() => "auto"}
    />
  );
  // return tableData.map((d, i) => {
  //   return <div key={i}>{JSON.stringify(d)}</div>;
  // });
};

const ChatItems = ({ chatItems }) => {
  const len = chatItems.length;
  return chatItems.map((item, i) => {
    if (len - 1 === i && item.type === "ai") {
      return (
        <div key={i} className={`message ${item.type}-message`}>
          <TypeAnimation
            sequence={[item.text]}
            speed={85}
            style={{
              fontSize: "16px",
              whiteSpace: "pre-line",
              textAlign: "left",
            }}
            repeat={0}
            cursor={false}
            key={i}
          />
        </div>
      );
    }
    return (
      <div key={i} className={`message ${item.type}-message`}>
        {item.text}
      </div>
    );
  });
};

const App = () => {
  // State to hold the input value
  const [inputValue, setInputValue] = useState("");
  const [chatItems, setChatItems] = useState([]);
  const [parsedMutationData, setParsedMutationData] = useState({});

  // Function to update the state based on input changes
  const handleChange = (event) => {
    setInputValue(event.target.value);
  };

  // Function to clean output returned in bad format from OpenAI
  const pruneOutput = (output) => {
    const idx = output.indexOf("\n{");
    if (idx === 0) {
      const newOutput = output.slice(2, output.length);
      return pruneOutput(newOutput);
    } else if (idx > -1) {
      return output.slice(0, idx);
    }

    return output;
  };
  const mutation = useMutation(postChat, {
    onSuccess: (data) => {
      if (data?.output) {
        let parsedOutput;
        try {
          // sometimes the agent responds with malformed JSON (a string with 2 JSON objects) and needs to be trimmed
          if (data.output.indexOf("\n{") > -1) {
            const output = pruneOutput(data.output);
            parsedOutput = JSON.parse(output);
            setParsedMutationData(parsedOutput);
            handleNewChatItem(parsedOutput?.summary, "ai");
          } else {
            try {
              parsedOutput = JSON.parse(data.output);
              setParsedMutationData(parsedOutput);
              handleNewChatItem(parsedOutput?.summary, "ai");
            } catch (e) {
              console.log("Cannot parse output: ", e);
              handleNewChatItem(data.output, "ai");
            }
          }
        } catch (e) {
          console.log("Error in parsing output from Agent: ", e);
        }
      }
    },
  });

  function handleTextToSequence(text) {
    // Split the text by newline characters to create an array
    const splitText = text.split("\n");

    // Create an animation sequence with each text followed by a delay
    const animationSequence = splitText.reduce((acc, line) => {
      // Add the line and then a delay to simulate the pause for typing the next line
      acc.push(line, 1000); // Adjust the delay as needed
      return acc;
    }, []);
    return animationSequence;
  }

  const handleNewChatItem = (newChatItem, type) => {
    setChatItems((items) => {
      return [...items, { type, text: newChatItem }];
    });
  };
  const handleSubmit = (e) => {
    e.preventDefault();
    handleNewChatItem(inputValue, "human");
    mutation.mutate(inputValue);
    setInputValue("");
  };

  return (
    <div>
      <header>
        <span className="header-title">YugaTrips</span>
      </header>
      <section>
        <div className="chat-wrapper">
          <h3>Chat History</h3>
          <div className="chat-messages-wrapper">
            <ChatItems chatItems={chatItems} />
          </div>
          <form>
            <input
              type="text"
              value={inputValue}
              onChange={handleChange}
              placeholder="Message A.I. Agent..."
            />
            <div className="chat-button-and-message-wrapper">
              <button onClick={handleSubmit}>Send Request</button>
              {mutation.isLoading && <CircularProgress className="loading" />}
              {mutation.isError ? (
                <p>An error occurred: {mutation.error.message}</p>
              ) : null}
            </div>
          </form>
        </div>
        <div className="data-table-wrapper">
          <h3>Data Table</h3>
          <DataTable data={parsedMutationData} />
        </div>
      </section>
      {/* {currentData.map((d, i) => {
        return <div key={i}>{d}</div>;
      })} */}
    </div>
  );
};

const WrappedApp = () => (
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);

export default WrappedApp;
