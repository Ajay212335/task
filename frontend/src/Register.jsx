import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function handleSubmit(e) {
    e.preventDefault();
    setMessage("Processing...");
    try {
      const res = await fetch("http://127.0.0.1:5000/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem("otp_token", data.otp_token);
        setMessage("OTP sent! Redirecting...");
        setTimeout(() => navigate("/verify"), 1200);
      } else {
        setMessage(data.error || "Error registering");
      }
    } catch {
      setMessage("Server error");
    }
  }

  return (
    <div style={{ padding: "20px", maxWidth: 400, margin: "auto" }}>
      <h2>Register</h2>
      <form onSubmit={handleSubmit}>
        <input name="name" placeholder="Name" onChange={handleChange} required /><br />
        <input name="email" placeholder="Email" type="email" onChange={handleChange} required /><br />
        <input name="password" placeholder="Password" type="password" onChange={handleChange} required /><br />
        <input name="confirm" placeholder="Confirm Password" type="password" onChange={handleChange} required /><br />
        <button type="submit">Submit</button>
      </form>
      <p>{message}</p>
      <p style={{ marginTop: "15px" }}>
        Already have an account? <a href="/login">Login</a>
      </p>
    </div>
  );
}
