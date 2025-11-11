import React, { useState } from "react";

export default function Chatbot() {
  const [input, setInput] = useState("");
  const [chats, setChats] = useState([]);
  const token = localStorage.getItem("token");

  async function sendMessage(e) {
    e.preventDefault();
    if (!input.trim()) return;
    const newChat = [...chats, { sender: "user", text: input }];
    setChats(newChat);
    setInput("");
    try {
      const res = await fetch("http://127.0.0.1:5000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: input }),
      });
      const data = await res.json();
      setChats([...newChat, { sender: "bot", text: data.bot }]);
    } catch {
      setChats([...newChat, { sender: "bot", text: "Error connecting to chatbot." }]);
    }
  }

  return (
    <div style={{ padding: 20 }}>
      <h2>💬 Chatbot</h2>
      <div style={{ border: "1px solid #ccc", height: 300, overflowY: "auto", padding: 10 }}>
        {chats.map((c, i) => (
          <p key={i} style={{ textAlign: c.sender === "user" ? "right" : "left" }}>
            <strong>{c.sender}:</strong> {c.text}
          </p>
        ))}
      </div>
      <form onSubmit={sendMessage}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type message..."
          style={{ width: "80%" }}
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
