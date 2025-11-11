import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function VerifyOTP() {
  const [otp, setOtp] = useState("");
  const [msg, setMsg] = useState("");
  const navigate = useNavigate();

  async function handleVerify(e) {
    e.preventDefault();
    const otp_token = localStorage.getItem("otp_token");
    if (!otp_token) return setMsg("Missing OTP token.");

    try {
      const res = await fetch("http://127.0.0.1:5000/api/verify_otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ otp, otp_token }),
      });
      const data = await res.json();
      if (res.ok) {
        setMsg("OTP Verified! Redirecting...");
        setTimeout(() => navigate("/login"), 1500);
      } else setMsg(data.error || "Verification failed");
    } catch {
      setMsg("Server error");
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 400, margin: "auto" }}>
      <h2>Verify OTP</h2>
      <form onSubmit={handleVerify}>
        <input value={otp} onChange={(e) => setOtp(e.target.value)} placeholder="Enter OTP" required />
        <button type="submit">Verify</button>
      </form>
      <p>{msg}</p>
    </div>
  );
}
