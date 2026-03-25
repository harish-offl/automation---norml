"use strict";
const formidable = require("formidable");
const XLSX       = require("xlsx");
const fs         = require("fs");

module.exports.config = { api: { bodyParser: false } };

function parseForm(req) {
  return new Promise((resolve, reject) => {
    const form = formidable({ multiples: false, keepExtensions: true, maxFileSize: 10 * 1024 * 1024 });
    form.parse(req, (err, fields, files) => (err ? reject(err) : resolve({ fields, files })));
  });
}

function normalizeKey(obj, ...keys) {
  for (const k of keys) {
    const hit = Object.keys(obj).find(key => key.trim().toLowerCase() === k.toLowerCase());
    if (hit && obj[hit]) return String(obj[hit]).trim();
  }
  return null;
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  let tmpPath = null;
  try {
    const { files } = await parseForm(req);
    const entry = files.file || files.leads || Object.values(files)[0];
    if (!entry) return res.status(400).json({ error: "No file uploaded." });

    const file = Array.isArray(entry) ? entry[0] : entry;
    tmpPath = file.filepath;

    const wb   = XLSX.readFile(tmpPath);
    const ws   = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(ws);
    if (!rows.length) return res.status(400).json({ error: "File has no valid rows." });

    const leads = rows.map(row => ({
      name:    normalizeKey(row, "name", "full name", "Full Name") || "there",
      email:   (normalizeKey(row, "email", "email address", "Email") || "").toLowerCase(),
      company: normalizeKey(row, "company", "company name") || "",
      niche:   normalizeKey(row, "niche", "solution", "interest", "service") || "",
    })).filter(l => l.email && l.email.includes("@"));

    return res.status(200).json({ success: true, total: leads.length, leads });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  } finally {
    if (tmpPath && fs.existsSync(tmpPath)) { try { fs.unlinkSync(tmpPath); } catch (_) {} }
  }
};
