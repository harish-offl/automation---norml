"use strict";
const XLSX = require("xlsx");

// Read raw multipart body manually — no temp files, works on Vercel serverless
function getRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", chunk => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

// Parse multipart/form-data boundary and extract the file buffer
function parseMultipart(body, boundary) {
  const boundaryBuf = Buffer.from("--" + boundary);
  const parts = [];
  let start = 0;

  while (start < body.length) {
    const boundaryIdx = body.indexOf(boundaryBuf, start);
    if (boundaryIdx === -1) break;
    const headerStart = boundaryIdx + boundaryBuf.length + 2; // skip \r\n
    const headerEnd = body.indexOf(Buffer.from("\r\n\r\n"), headerStart);
    if (headerEnd === -1) break;
    const header = body.slice(headerStart, headerEnd).toString();
    const dataStart = headerEnd + 4;
    const nextBoundary = body.indexOf(boundaryBuf, dataStart);
    const dataEnd = nextBoundary === -1 ? body.length : nextBoundary - 2; // trim \r\n
    if (header.includes("filename")) {
      parts.push({ header, data: body.slice(dataStart, dataEnd) });
    }
    start = nextBoundary === -1 ? body.length : nextBoundary;
  }
  return parts;
}

function normalizeKey(obj, ...keys) {
  for (const k of keys) {
    const hit = Object.keys(obj).find(key => key.trim().toLowerCase() === k.toLowerCase());
    if (hit && obj[hit]) return String(obj[hit]).trim();
  }
  return null;
}

async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  try {
    const contentType = req.headers["content-type"] || "";
    if (!contentType.includes("multipart/form-data")) {
      return res.status(400).json({ error: "Expected multipart/form-data upload." });
    }

    const boundaryMatch = contentType.match(/boundary=(.+)$/);
    if (!boundaryMatch) return res.status(400).json({ error: "No boundary in content-type." });
    const boundary = boundaryMatch[1].trim();

    // Read entire body into memory — no temp files
    const body = await getRawBody(req);
    const parts = parseMultipart(body, boundary);

    if (!parts.length) return res.status(400).json({ error: "No file found in upload." });

    const fileBuf = parts[0].data;

    // Parse CSV or XLSX directly from buffer
    const wb   = XLSX.read(fileBuf, { type: "buffer" });
    const ws   = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(ws);

    if (!rows.length) return res.status(400).json({ error: "File has no valid rows." });

    const leads = rows.map(row => ({
      name:    normalizeKey(row, "name", "full name", "Full Name") || "there",
      email:   (normalizeKey(row, "email", "email address", "Email") || "").toLowerCase(),
      company: normalizeKey(row, "company", "company name") || "",
      niche:   normalizeKey(row, "niche", "solution", "interest", "service") || "",
    })).filter(l => l.email && l.email.includes("@"));

    if (!leads.length) return res.status(400).json({ error: "No valid email addresses found in file." });

    return res.status(200).json({ success: true, total: leads.length, leads });

  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}

handler.config = { api: { bodyParser: false } };
module.exports = handler;
