// src/api.ts
import axios from "axios";

const API_BASE = "http://localhost:8000";

export const askQuestion = async (groupId: string, question: string) => {
  const res = await axios.post(`${API_BASE}/ask`, {
    group_id: groupId,
    question,
  });
  return res.data;
};

export const ingestDocument = async (clientId: string, content: string) => {
  const res = await axios.post(`${API_BASE}/ingest`, {
    client_id: clientId,
    content,
  });
  return res.data;
};