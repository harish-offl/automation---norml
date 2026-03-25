"use strict";

// In-memory store — resets on cold start (Vercel serverless)
// For persistence use a DB like PlanetScale or Upstash Redis
let _state = { total: 0, sent: 0, failed: 0, skipped: 0, lastRun: null };

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();

  if (req.method === "POST") {
    // Update state after a campaign run
    let body = req.body;
    if (!body) {
      try {
        const chunks = [];
        for await (const chunk of req) chunks.push(chunk);
        body = JSON.parse(Buffer.concat(chunks).toString());
      } catch (_) { body = {}; }
    }
    _state = {
      total:   body.total   || 0,
      sent:    body.sent    || 0,
      failed:  body.failed  || 0,
      skipped: body.skipped || 0,
      lastRun: new Date().toISOString(),
    };
    return res.status(200).json({ success: true, state: _state });
  }

  // GET — return current stats
  return res.status(200).json({
    success:    true,
    status:     _state.lastRun ? "finished" : "idle",
    total:      _state.total,
    sent:       _state.sent,
    failed:     _state.failed,
    skipped:    _state.skipped,
    openRate:   _state.sent > 0 ? "tracking not enabled" : "0%",
    clickRate:  _state.sent > 0 ? "tracking not enabled" : "0%",
    lastRun:    _state.lastRun,
  });
};
