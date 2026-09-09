import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./style.css";

const API = "http://127.0.0.1:8000";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
});

function App() {
  const [stats, setStats] = useState({});
  const [damages, setDamages] = useState([]);
  const [error, setError] = useState("");

  async function loadData() {
    try {
      const [s, d] = await Promise.all([
        fetch(`${API}/api/dashboard/stats`).then(r => r.json()),
        fetch(`${API}/api/damages`).then(r => r.json())
      ]);
      setStats(s);
      setDamages(d);
      setError("");
    } catch {
      setError("Backend is not running. Start FastAPI on port 8000.");
    }
  }

  async function updateStatus(id, status) {
    try {
      await fetch(
        `${API}/api/damages/${id}/status?status=${encodeURIComponent(status)}`,
        { method: "PATCH" }
      );
      loadData();
    } catch {
      setError("Could not update status.");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Road Intelligence</h1>
          <p>AI-powered road damage monitoring dashboard</p>
        </div>
        <div className="live">● LIVE</div>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="cards">
        <Card title="Total Issues" value={stats.total || 0} />
        <Card title="Critical" value={stats.critical || 0} danger />
        <Card title="High" value={stats.high || 0} />
        <Card title="Medium" value={stats.medium || 0} />
        <Card title="Pending Repair" value={stats.pending || 0} />
      </section>

      <section className="content">
        <div className="panel">
          <h2>Damage Location Map</h2>
          <MapContainer center={[28.57, 77.20]} zoom={10} className="map">
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {damages.map(d => (
              <Marker key={d.id} position={[d.latitude, d.longitude]}>
                <Popup>
                  <strong>{d.damage_type.toUpperCase()}</strong>
                  <br />Confidence: {(d.confidence * 100).toFixed(0)}%
                  <br />Severity: {d.severity}
                  <br />Status: {d.status}
                  <br />
                  <button onClick={() => updateStatus(d.id, "Repaired")}>
                    Mark Repaired
                  </button>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>

        <div className="panel">
          <h2>Detected Road Damage</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Confidence</th>
                  <th>Severity</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {damages.map(d => (
                  <tr key={d.id}>
                    <td>#{d.id}</td>
                    <td>{d.damage_type}</td>
                    <td>{(d.confidence * 100).toFixed(0)}%</td>
                    <td>
                      <span className={`badge ${d.severity.toLowerCase()}`}>
                        {d.severity}
                      </span>
                    </td>
                    <td>
                      <select
                        value={d.status}
                        onChange={e => updateStatus(d.id, e.target.value)}
                      >
                        <option>Pending</option>
                        <option>Assigned</option>
                        <option>In Progress</option>
                        <option>Repaired</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

function Card({ title, value, danger }) {
  return (
    <div className={`card ${danger ? "danger" : ""}`}>
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
