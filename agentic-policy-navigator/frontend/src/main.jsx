import React from "react";
import ReactDOM from "react-dom/client";
import PolicyNavigatorApp from "./PolicyNavigatorApp.jsx"; // <— note .jsx
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <PolicyNavigatorApp />
  </React.StrictMode>
);
