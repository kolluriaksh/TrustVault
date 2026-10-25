import React from "react";
import { useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

type User = {
  id: number;
  name: string;
  email: string;
};

async function apiRequest(path: string, options: RequestInit = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }

  return data;
}

function App() {
  const [backend, setBackend] = useState("Checking...");
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiRequest("/health")
      .then(() => setBackend("Connected"))
      .catch(() => setBackend("Disconnected"));

    apiRequest("/api/me")
      .then((data) => setUser(data.user))
      .catch(() => setUser(null));
  }, []);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const path = mode === "register" ? "/api/register" : "/api/login";
      const body =
        mode === "register"
          ? { name, email, password }
          : { email, password };

      const data = await apiRequest(path, {
        method: "POST",
        body: JSON.stringify(body),
      });

      setUser(data.user);
      setPassword("");
      setMessage(data.message || "Success!");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    try {
      await apiRequest("/api/logout", { method: "POST" });
      setUser(null);
      setMessage("You have logged out.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Logout failed.");
    }
  }

  return (
    <div className="tv-app">
      <aside className="tv-sidebar">
        <a className="tv-brand" href="#">
          <span className="tv-brand-icon">◈</span>
          <span>TrustVault<small>SECURE WORKSPACE</small></span>
        </a>

        <p className="tv-nav-label">WORKSPACE</p>
        <div className="tv-nav-item active">▦ &nbsp; Overview</div>
        <div className="tv-nav-item">▤ &nbsp; My documents</div>
        <div className="tv-nav-item">♧ &nbsp; Shared with me</div>
        <div className="tv-nav-item">◷ &nbsp; Audit history</div>

        <div className="tv-sidebar-bottom">
          <span className="tv-status-dot" />
          Backend: {backend}
          <p>Secure files. Clear accountability.</p>
        </div>
      </aside>

      <main className="tv-main">
        <header className="tv-topbar">
          <span>TrustVault / Overview</span>
          {user ? (
            <button className="tv-secondary" onClick={handleLogout}>
              Log out
            </button>
          ) : (
            <span className="tv-protected">Protected workspace</span>
          )}
        </header>

        <section className="tv-welcome">
          <div>
            <span className="tv-eyebrow">YOUR DOCUMENT WORKSPACE</span>
            <h1>{user ? `Welcome, ${user.name}` : "Welcome to TrustVault"}</h1>
            <p>
              Keep important files organized and share them only with people
              you trust.
            </p>
          </div>
          <div className="tv-hero-icon">◈</div>
        </section>

        <section className="tv-stats">
          <article className="tv-stat-card">
            <span>MY DOCUMENTS</span>
            <strong>—</strong>
            <small>Document API not connected yet</small>
          </article>
          <article className="tv-stat-card">
            <span>SHARED DOCUMENTS</span>
            <strong>—</strong>
            <small>Sharing API not connected yet</small>
          </article>
          <article className="tv-stat-card">
            <span>BACKEND STATUS</span>
            <strong className={backend === "Connected" ? "tv-green" : ""}>
              {backend}
            </strong>
            <small>Flask API · Port 5000</small>
          </article>
        </section>

        <section className="tv-content-grid">
          <article className="tv-panel">
            <div className="tv-panel-heading">
              <div>
                <h2>My documents</h2>
                <p>Your private document workspace</p>
              </div>
              <span className="tv-lock">▣ Secure storage</span>
            </div>

            <div className="tv-empty-state">
              <div className="tv-file-icon">▤</div>
              <h3>Document storage is next</h3>
              <p>
                Your account can connect to Flask. Next, we need to implement
                secure upload, document listing and download endpoints.
              </p>
            </div>
          </article>

          <article className="tv-panel tv-auth-panel">
            <div className="tv-panel-heading">
              <div>
                <h2>{user ? "Your account" : "Get started"}</h2>
                <p>
                  {user
                    ? "You are signed in"
                    : "Sign in or create a secure account"}
                </p>
              </div>
            </div>

            {user ? (
              <div className="tv-account">
                <div className="tv-avatar">{user.name.charAt(0).toUpperCase()}</div>
                <h3>{user.name}</h3>
                <p>{user.email}</p>
                <span className="tv-account-badge">✓ Authenticated</span>
              </div>
            ) : (
              <>
                <div className="tv-tabs">
                  <button
                    className={mode === "login" ? "selected" : ""}
                    onClick={() => {
                      setMode("login");
                      setMessage("");
                    }}
                  >
                    Login
                  </button>
                  <button
                    className={mode === "register" ? "selected" : ""}
                    onClick={() => {
                      setMode("register");
                      setMessage("");
                    }}
                  >
                    Register
                  </button>
                </div>

                <form onSubmit={handleAuth} className="tv-form">
                  {mode === "register" && (
                    <label>
                      Full name
                      <input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Your name"
                        maxLength={100}
                        required
                      />
                    </label>
                  )}

                  <label>
                    Email address
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      maxLength={255}
                      required
                    />
                  </label>

                  <label>
                    Password
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="At least 8 characters"
                      minLength={mode === "register" ? 8 : undefined}
                      autoComplete={
                        mode === "register" ? "new-password" : "current-password"
                      }
                      required
                    />
                  </label>

                  <button className="tv-primary" type="submit" disabled={loading}>
                    {loading
                      ? "Please wait..."
                      : mode === "register"
                        ? "Create account"
                        : "Sign in"}
                  </button>
                </form>
              </>
            )}

            {message && <p className="tv-message" role="status">{message}</p>}
          </article>
        </section>

        <footer className="tv-footer">
          TrustVault · Secure document sharing · Development environment
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("app")!).render(<App />);
