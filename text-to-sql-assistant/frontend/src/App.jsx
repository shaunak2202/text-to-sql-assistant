import { useEffect, useRef, useState } from "react";
import { askQuestion, fetchSchema, API_BASE_URL } from "./api.js";

const EXAMPLE_QUESTIONS = [
  "how many customers are there",
  "list all products",
  "top 3 products by price",
  "average price of products",
];

function SourceBadge({ source }) {
  const styles =
    source === "openai"
      ? "bg-violet-100 text-violet-800 border-violet-300"
      : source === "rule_based"
      ? "bg-amber-100 text-amber-800 border-amber-300"
      : "bg-gray-100 text-gray-700 border-gray-300";
  const label =
    source === "openai" ? "OpenAI" : source === "rule_based" ? "rule-based fallback" : source;
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${styles}`}>
      {label}
    </span>
  );
}

function ResultTable({ columns, rows }) {
  if (!rows || rows.length === 0) {
    return <p className="text-sm text-gray-500 italic">(no rows)</p>;
  }
  return (
    <div className="overflow-x-auto rounded border border-gray-200">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-left font-semibold text-gray-700">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-gray-800 whitespace-nowrap">
                  {String(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoryEntry({ entry }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium text-gray-900">{entry.question}</p>
        {entry.sql && <SourceBadge source={entry.source} />}
      </div>

      {entry.sql && (
        <pre className="mt-2 overflow-x-auto rounded bg-gray-900 p-2 text-xs text-gray-100">
          {entry.sql}
        </pre>
      )}

      {entry.loading && <p className="mt-2 text-sm text-gray-500">Running...</p>}

      {!entry.loading && entry.networkError && (
        <p className="mt-2 text-sm text-red-600">✗ {entry.networkError}</p>
      )}

      {!entry.loading && !entry.networkError && entry.result && !entry.result.ok && (
        <p className="mt-2 text-sm text-red-600">✗ {entry.result.error}</p>
      )}

      {!entry.loading && entry.result && entry.result.ok && (
        <div className="mt-3">
          <ResultTable columns={entry.result.columns} rows={entry.result.rows} />
          <p className="mt-1 text-xs text-gray-400">
            {entry.result.rows.length} row(s) in {entry.result.elapsed_seconds.toFixed(3)}s
          </p>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [schema, setSchema] = useState(null);
  const [schemaError, setSchemaError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    fetchSchema()
      .then(setSchema)
      .catch((err) =>
        setSchemaError(
          `Couldn't reach the API at ${API_BASE_URL} (${err.message}). ` +
            "Is the backend running? (uvicorn api:app --reload)"
        )
      );
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function runQuestion(q) {
    const trimmed = q.trim();
    if (!trimmed) return;

    const index = history.length;
    setHistory((h) => [...h, { question: trimmed, loading: true }]);
    setQuestion("");

    try {
      const result = await askQuestion(trimmed);
      setHistory((h) => {
        const next = [...h];
        next[index] = {
          question: trimmed,
          loading: false,
          sql: result.sql,
          source: result.source,
          result,
        };
        return next;
      });
    } catch (err) {
      setHistory((h) => {
        const next = [...h];
        next[index] = { question: trimmed, loading: false, networkError: err.message };
        return next;
      });
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    runQuestion(question);
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="border-b border-gray-200 bg-white px-6 py-4 shadow-sm">
        <h1 className="text-xl font-bold text-gray-900">Text-to-SQL Query Assistant</h1>
        <p className="text-sm text-gray-500">
          Ask a question in plain English; it's turned into a validated,
          read-only SQL query and executed against a live database.
        </p>
      </header>

      <div className="mx-auto flex max-w-6xl gap-6 px-6 py-6">
        <aside className="w-64 shrink-0">
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">Schema</h2>
            {schemaError && <p className="text-xs text-red-600">{schemaError}</p>}
            {!schemaError && !schema && <p className="text-xs text-gray-400">Loading…</p>}
            {schema && (
              <ul className="space-y-1 text-sm text-gray-700">
                {schema.tables.map((t) => (
                  <li key={t} className="rounded bg-gray-50 px-2 py-1 font-mono text-xs">
                    {t}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">Try asking</h2>
            <ul className="space-y-1">
              {EXAMPLE_QUESTIONS.map((q) => (
                <li key={q}>
                  <button
                    onClick={() => runQuestion(q)}
                    className="w-full rounded bg-gray-50 px-2 py-1 text-left text-xs text-gray-700 hover:bg-gray-100"
                  >
                    {q}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <main className="flex-1">
          <div className="space-y-3">
            {history.length === 0 && (
              <p className="text-sm text-gray-400">
                No questions yet — ask something below, or click an example on the left.
              </p>
            )}
            {history.map((entry, i) => (
              <HistoryEntry key={i} entry={entry} />
            ))}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="sticky bottom-4 mt-6 flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. how many orders are completed"
              className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 shadow-sm focus:border-blue-400 focus:outline-none"
            />
            <button
              type="submit"
              className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white shadow-sm hover:bg-blue-700"
            >
              Ask
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}
