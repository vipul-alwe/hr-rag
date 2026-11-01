import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import "../styles/rag-data-manager.css";

const API_BASE = "http://localhost:8000";

const CLIENT_GROUP_MAP: Record<string, string> = {
  "11111111-1111-1111-1111-111111111111": "test_group_1",
  "33333333-3333-3333-3333-333333333333": "test_group_2",
};

const POLICY_SUGGESTIONS = [
  "Code of Conduct",
  "POSH",
  "Leave Policy",
  "Travel Policy",
  "Attendance Policy",
  "Gratuity Policy",
  "Sandwich Leave Policy",
  "Onboarding Policy",
  "General",
];

type Doc = {
  id: string;
  client_id?: string;
  content?: string;
  text?: string;
  body?: string;
  policy_name?: string;
  section_title?: string;
  [k: string]: any;
};

export default function RagDataManager() {
  const [clientId, setClientId] = useState<string>(
    Object.keys(CLIENT_GROUP_MAP)[0]
  );
  const [activeTab, setActiveTab] = useState<string>("all");
  const [documents, setDocuments] = useState<Doc[]>([]);

  // text ingest
  const [docContent, setDocContent] = useState<string>("");
  const [policyName, setPolicyName] = useState<string>("");
  const [sectionTitle, setSectionTitle] = useState<string>("");

  // file upload
  const [file, setFile] = useState<File | null>(null);
  const [filePolicyName, setFilePolicyName] = useState<string>("");

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [toast, setToast] = useState<{ msg: string; error?: boolean } | null>(null);

  const showToast = (msg: string, error = false) => {
    setToast({ msg, error });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchDocuments = async (cid: string | "all" = clientId) => {
    try {
      if (cid === "all") {
        const clientIds = Object.keys(CLIENT_GROUP_MAP);
        const results = await Promise.all(
          clientIds.map((id) => axios.get(`${API_BASE}/documents/${id}`))
        );
        const combined = results.flatMap((r, idx) =>
          r.data.map((d: any) => ({ ...d, client_id: clientIds[idx] }))
        );
        setDocuments(combined);
      } else {
        const res = await axios.get(`${API_BASE}/documents/${cid}`);
        const docsWithClient = res.data.map((d: any) => ({
          ...d,
          client_id: cid,
        }));
        setDocuments(docsWithClient);
      }
      setSelectedIds([]);
    } catch (err) {
      showToast("Failed to fetch documents", true);
    }
  };

  useEffect(() => {
    fetchDocuments(activeTab === "all" ? "all" : clientId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId, activeTab]);

  const handleIngest = async () => {
    if (!docContent.trim()) return;
    try {
      setLoading(true);
      await axios.post(`${API_BASE}/ingest`, {
        client_id: clientId,
        content: docContent,
        policy_name: policyName.trim() || null,
        section_title: sectionTitle.trim() || null,
      });
      setDocContent("");
      setPolicyName("");
      setSectionTitle("");
      showToast("Document ingested successfully");
      fetchDocuments(activeTab === "all" ? "all" : clientId);
    } catch (err) {
      showToast("Failed to ingest document", true);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async () => {
    if (!file) return;
    const form = new FormData();
    form.append("client_id", clientId);
    form.append("file", file);
    if (filePolicyName.trim()) {
      form.append("policy_name", filePolicyName.trim());
    }
    try {
      setLoading(true);
      await axios.post(`${API_BASE}/ingest/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFile(null);
      setFilePolicyName("");
      showToast("File uploaded successfully");
      fetchDocuments(activeTab === "all" ? "all" : clientId);
    } catch (err) {
      showToast("Failed to upload file", true);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await axios.delete(`${API_BASE}/documents/${id}`);
      showToast("Document deleted");
      fetchDocuments(activeTab === "all" ? "all" : clientId);
    } catch (err) {
      showToast("Failed to delete document", true);
    }
  };

  const handleBulkDelete = async () => {
    if (!selectedIds.length) return;
    try {
      await Promise.all(
        selectedIds.map((id) => axios.delete(`${API_BASE}/documents/${id}`))
      );
      setSelectedIds([]);
      showToast(`Deleted ${selectedIds.length} documents`);
      fetchDocuments(activeTab === "all" ? "all" : clientId);
    } catch (err) {
      showToast("Bulk delete failed", true);
    }
  };

  const displayedDocs = documents.filter((d) =>
    activeTab === "all" ? true : d.client_id === activeTab
  );

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = (checked: boolean) => {
    if (checked) setSelectedIds(displayedDocs.map((d) => d.id));
    else setSelectedIds([]);
  };

  return (
    <div className="data-manager-wrapper">
      <div className="data-manager">

        {/* Header */}
        <div>
          <Link to="/" className="data-manager-back-button">← Back to Chat</Link>
          <h2>Data Manager</h2>
          <span>{documents.length} docs</span>
        </div>

        {/* Client selector + bulk actions */}
        <div className="data-manager-controls">
          <label>
            Select Client:
            <select value={clientId} onChange={(e) => setClientId(e.target.value)}>
              {Object.keys(CLIENT_GROUP_MAP).map((id) => (
                <option key={id} value={id}>
                  {CLIENT_GROUP_MAP[id]}
                </option>
              ))}
            </select>
          </label>
          <div className="data-manager-actions">
            <button onClick={() => fetchDocuments(activeTab === "all" ? "all" : clientId)}>
              Refresh
            </button>
            <button onClick={handleBulkDelete} disabled={!selectedIds.length}>
              Delete Selected ({selectedIds.length})
            </button>
          </div>
        </div>

        {/* Text ingest */}
        <div className="data-manager-section">
          <h3>Ingest Text</h3>

          <label>Policy Name</label>
          <div>
            {POLICY_SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setPolicyName(policyName === s ? "" : s)}
              >
                {s}
              </button>
            ))}
          </div>
          <input
            placeholder="Or type custom policy name..."
            value={policyName}
            onChange={(e) => setPolicyName(e.target.value)}
          />

          <label>Section Title (optional)</label>
          <input
            placeholder="e.g. Committee Members, Grievance Process"
            value={sectionTitle}
            onChange={(e) => setSectionTitle(e.target.value)}
          />

          <label>Content</label>
          <textarea
            className="data-manager-textarea"
            rows={6}
            value={docContent}
            onChange={(e) => setDocContent(e.target.value)}
            placeholder="Paste policy text here..."
          />

          <button onClick={handleIngest} disabled={loading || !docContent.trim()}>
            {loading ? "Uploading..." : "Upload Text"}
          </button>
        </div>

        {/* File upload */}
        <div className="data-manager-section">
          <h3>Upload File</h3>

          <label>Policy Name (optional)</label>
          <div>
            {POLICY_SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setFilePolicyName(filePolicyName === s ? "" : s)}
              >
                {s}
              </button>
            ))}
          </div>
          <input
            placeholder="Or type custom policy name..."
            value={filePolicyName}
            onChange={(e) => setFilePolicyName(e.target.value)}
          />

          <label>File</label>
          <input
            type="file"
            className="data-manager-file-input"
            accept=".txt,.pdf,.docx,.pptx"
            onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
          />
          {file && (
            <p>{file.name} ({(file.size / 1024).toFixed(1)} KB)</p>
          )}

          <button onClick={handleFileUpload} disabled={!file || loading}>
            {loading ? "Uploading..." : "Upload File"}
          </button>
        </div>

        {/* Documents table */}
        <div>
          <div className="data-manager-tabs">
            <button
              className={`data-manager-tab ${activeTab === "all" ? "active" : ""}`}
              onClick={() => { setActiveTab("all"); fetchDocuments("all"); }}
            >
              All
            </button>
            {Object.keys(CLIENT_GROUP_MAP).map((id) => (
              <button
                key={id}
                className={`data-manager-tab ${activeTab === id ? "active" : ""}`}
                onClick={() => { setActiveTab(id); setClientId(id); fetchDocuments(id); }}
              >
                {CLIENT_GROUP_MAP[id]}
              </button>
            ))}
          </div>

          <table className="data-manager-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    className="data-manager-checkbox"
                    checked={
                      displayedDocs.length > 0 &&
                      selectedIds.length === displayedDocs.length
                    }
                    onChange={(e) => toggleSelectAll(e.target.checked)}
                  />
                </th>
                <th>ID</th>
                <th>Client</th>
                <th>Policy</th>
                <th>Section</th>
                <th>Content</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {displayedDocs.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    <input
                      type="checkbox"
                      className="data-manager-checkbox"
                      checked={selectedIds.includes(doc.id)}
                      onChange={() => toggleSelect(doc.id)}
                    />
                  </td>
                  <td className="data-manager-doc-id">{doc.id?.slice(0, 8) ?? "—"}</td>
                  <td>{CLIENT_GROUP_MAP[doc.client_id ?? ""] ?? doc.client_id ?? "—"}</td>
                  <td>{doc.policy_name ?? "—"}</td>
                  <td>{doc.section_title ?? "—"}</td>
                  <td className="data-manager-doc-content">
                    {doc.content ?? doc.text ?? doc.body ?? JSON.stringify(doc)}
                  </td>
                  <td>
                    <button onClick={() => handleDelete(doc.id)}>Delete</button>
                  </td>
                </tr>
              ))}
              {displayedDocs.length === 0 && (
                <tr>
                  <td colSpan={7} className="data-manager-empty">
                    No documents found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {toast && <div>{toast.msg}</div>}

      </div>
    </div>
  );
}