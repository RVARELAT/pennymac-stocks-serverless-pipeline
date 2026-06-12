import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "https://7c199o6ef5.execute-api.us-west-2.amazonaws.com/movers";

function App() {
  const [movers, setMovers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function fetchMovers() {
      try {
        const response = await fetch(API_URL);

        if (!response.ok) {
          throw new Error("Failed to load stock mover data.");
        }

        const data = await response.json();
        setMovers(data.movers || []);
      } catch (error) {
        setErrorMessage(error.message);
      } finally {
        setLoading(false);
      }
    }

    fetchMovers();
  }, []);

  const latestMover = movers[0];

  return (
    <main className="page">
      <section className="hero">
        <h1>Serverless Stock Mover Dashboard</h1>
        <p className="subtitle">
          Tracks a daily stock watchlist, calculates the largest price mover,
          stores the result in DynamoDB, and displays the history through a
          serverless API.
        </p>
      </section>

      {loading && <p className="status">Loading stock mover data...</p>}

      {errorMessage && <p className="error">{errorMessage}</p>}

      {!loading && !errorMessage && latestMover && (
        <>
          <section className="card featured-card">
            <div>
              <p className="label">Latest Top Mover</p>
              <h2>{latestMover.ticker}</h2>
              <p className="date">{latestMover.date}</p>
            </div>

            <div
              className={
                latestMover.percent_change >= 0
                  ? "change positive"
                  : "change negative"
              }
            >
              {latestMover.percent_change >= 0 ? "+" : ""}
              {latestMover.percent_change}%
            </div>

            <div>
              <p className="label">Close Price</p>
              <p className="price">${latestMover.close_price}</p>
            </div>
          </section>

          <section className="card">
            <div className="section-header">
              <div>
                <p className="label">History</p>
                <h2>Recent Movers</h2>
              </div>
              <p className="count">{movers.length} record(s)</p>
            </div>

            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Ticker</th>
                  <th>Percent Change</th>
                  <th>Close Price</th>
                </tr>
              </thead>
              <tbody>
                {movers.map((mover) => (
                  <tr key={`${mover.date}-${mover.ticker}`}>
                    <td>{mover.date}</td>
                    <td className="ticker">{mover.ticker}</td>
                    <td
                      className={
                        mover.percent_change >= 0 ? "positive" : "negative"
                      }
                    >
                      {mover.percent_change >= 0 ? "+" : ""}
                      {mover.percent_change}%
                    </td>
                    <td>${mover.close_price}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}

      {!loading && !errorMessage && movers.length === 0 && (
        <p className="status">No mover data found yet.</p>
      )}
    </main>
  );
}

export default App;