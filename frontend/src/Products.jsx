import React, { useEffect, useState } from "react";

export default function Products() {
  const [products, setProducts] = useState([]);
  const [profile, setProfile] = useState(null);
  const [msg, setMsg] = useState("");
  const [chat, setChat] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState([]);

  const token = localStorage.getItem("token"); // store token from login

  // ------------------------------------------------------------
  // Fetch Products
  // ------------------------------------------------------------
  useEffect(() => {
    async function fetchProducts() {
      try {
        const res = await fetch("http://127.0.0.1:5000/api/products");
        const data = await res.json();
        if (Array.isArray(data)) setProducts(data);
        else setMsg("Invalid product response");
      } catch {
        setMsg("Failed to load products");
      }
    }
    fetchProducts();
  }, []);

  // ------------------------------------------------------------
  // Fetch Profile & Orders
  // ------------------------------------------------------------
  useEffect(() => {
    async function fetchProfile() {
      try {
        const res = await fetch("http://127.0.0.1:5000/api/profile", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (data.profile) {
          setProfile(data.profile);
          setOrders(data.orders || []);
        } else setMsg("Failed to fetch profile");
      } catch {
        setMsg("Profile fetch error");
      }
    }
    if (token) fetchProfile();
  }, [token]);

  // ------------------------------------------------------------
  // Send Chat Message
  // ------------------------------------------------------------
  async function sendChat() {
  if (!input.trim()) return;

  const newChat = [...chat, { role: "user", content: input }];
  setChat(newChat);
  setInput("");
  setLoading(true);

  try {
    // Call backend chat endpoint
    const res = await fetch("http://127.0.0.1:5000/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ message: input }),
    });
    const data = await res.json();

    // Append bot reply to chat
    setChat([...newChat, { role: "bot", content: data.bot || "No reply" }]);
  } catch {
    setChat([...newChat, { role: "bot", content: "⚠️ Failed to connect to chatbot" }]);
  }

  setLoading(false);
}


  // ------------------------------------------------------------
  // Place Order
  // ------------------------------------------------------------
  async function placeOrder(product_id) {
    if (!token) {
      alert("Please login to place an order");
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:5000/api/order", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ product_id, quantity: 1 }),
      });

      const data = await res.json();
      if (res.ok) {
        alert(`✅ Order placed! Order ID: ${data.order_id}`);
        // Refresh orders after placing
        setOrders((prev) => [
          ...prev,
          {
            order_id: data.order_id,
            status: "processing",
            items: products.filter((p) => p.product_id === product_id).map((p) => ({ product_id: p.product_id, name: p.name, qty: 1, price: p.price })),
            created_at: new Date().toISOString(),
          },
        ]);
      } else {
        alert(`⚠️ ${data.error || "Failed to place order"}`);
      }
    } catch (err) {
      alert("⚠️ Error connecting to server");
    }
  }

  // ------------------------------------------------------------
  // Render
  // ------------------------------------------------------------
  return (
    <div style={{ fontFamily: "Arial", padding: 20 }}>
      <h2>💬 E-Commerce Dashboard</h2>

      {msg && <p style={{ color: "red" }}>{msg}</p>}

      {/* Profile Section */}
      {profile && (
        <div
          style={{
            border: "1px solid #ccc",
            borderRadius: 10,
            padding: 15,
            marginBottom: 20,
            background: "#f9f9f9",
          }}
        >
          <h3>👤 Profile</h3>
          <p><b>Name:</b> {profile.name}</p>
          <p><b>Email:</b> {profile.email}</p>
          <p><b>Joined:</b> {new Date(profile.created_at).toLocaleString()}</p>
        </div>
      )}

      {/* Product Section */}
      <div>
        <h3>🛒 Products</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 15 }}>
          {products.map((p) => (
            <div
              key={p.product_id}
              style={{
                border: "1px solid #ccc",
                borderRadius: 10,
                padding: 15,
                width: 200,
                background: "#fff",
              }}
            >
              <h4>{p.name}</h4>
              <p>💰 ₹{p.price}</p>
              <button
                onClick={() => placeOrder(p.product_id)}
                style={{
                  background: "#007bff",
                  color: "#fff",
                  border: "none",
                  borderRadius: 5,
                  padding: "6px 10px",
                  cursor: "pointer",
                }}
              >
                Buy
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Orders Section */}
      {orders.length > 0 && (
        <div style={{ marginTop: 30 }}>
          <h3>📦 My Orders</h3>
          {orders.map((o) => (
            <div key={o.order_id} style={{ border: "1px solid #ddd", padding: 10, marginBottom: 10, borderRadius: 5, background: "#fff" }}>
              <p><b>Order ID:</b> {o.order_id}</p>
              <p><b>Status:</b> {o.status}</p>
              <p><b>Date:</b> {new Date(o.created_at).toLocaleString()}</p>
              <ul>
                {o.items.map((item, idx) => (
                  <li key={idx}>{item.name} x {item.qty} - ₹{item.price}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* Chatbot Section */}
      <div
        style={{
          marginTop: 30,
          border: "1px solid #ccc",
          borderRadius: 10,
          padding: 15,
          background: "#f1f1f1",
          width: "100%",
          maxWidth: 500,
        }}
      >
        <h3>🤖 Chatbot Assistant</h3>
        <div
          style={{
            height: 250,
            overflowY: "auto",
            border: "1px solid #ddd",
            borderRadius: 5,
            padding: 10,
            background: "#fff",
          }}
        >
          {chat.map((c, i) => (
            <div
              key={i}
              style={{
                textAlign: c.role === "user" ? "right" : "left",
                marginBottom: 10,
              }}
            >
              <b>{c.role === "user" ? "You" : "Bot"}:</b> {c.content}
            </div>
          ))}
          {loading && <p>⏳ Bot is typing...</p>}
        </div>

        <div style={{ marginTop: 10, display: "flex", gap: 5 }}>
          <input
            type="text"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            style={{ flex: 1, padding: 8 }}
          />
          <button
            onClick={sendChat}
            style={{
              background: "#28a745",
              color: "#fff",
              border: "none",
              borderRadius: 5,
              padding: "8px 12px",
              cursor: "pointer",
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
