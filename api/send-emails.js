"use strict";
const nodemailer = require("nodemailer");

function buildTransporter() {
  const user = process.env.EMAIL_USER;
  const pass = process.env.EMAIL_PASS;
  if (!user || !pass) throw new Error("EMAIL_USER or EMAIL_PASS not set in Vercel environment variables.");
  return nodemailer.createTransport({
    host:   process.env.SMTP_HOST || "smtp.gmail.com",
    port:   Number(process.env.SMTP_PORT) || 587,
    secure: false,
    auth:   { user, pass },
  });
}

function textBody(name, company, niche, agency, sender) {
  return `Hi ${name},\n\nI came across ${company || "your company"} and wanted to reach out about ${niche || "your services"}.\n\nAt ${agency}, we help businesses grow through targeted email outreach and automation.\n\nWould you be open to a quick 15-minute call this week?\n\nBest,\n${sender}\n${agency}`;
}

function htmlBody(name, company, niche, agency, sender) {
  return `<!DOCTYPE html><html><body style="font-family:Inter,sans-serif;background:#0a0f0d;color:#e8f0ec;padding:32px;max-width:560px;margin:0 auto"><div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:32px"><div style="width:40px;height:40px;background:linear-gradient(135deg,#ff6a00,#ff4500);border-radius:8px;display:inline-block;line-height:40px;text-align:center;font-weight:700;color:#fff;margin-bottom:24px">NA</div><p>Hi <strong>${name}</strong>,</p><p style="color:#8fa89a">I came across <strong style="color:#e8f0ec">${company || "your company"}</strong> and wanted to reach out about <strong style="color:#ff6a00">${niche || "your services"}</strong>.</p><p style="color:#8fa89a">At <strong style="color:#e8f0ec">${agency}</strong>, we help businesses grow through targeted email outreach and automation.</p><p style="color:#8fa89a">Would you be open to a quick 15-minute call this week?</p><p style="color:#5a7066">Best,<br><strong style="color:#e8f0ec">${sender}</strong><br>${agency}</p></div></body></html>`;
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  let body = req.body;
  if (!body) {
    try {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      body = JSON.parse(Buffer.concat(chunks).toString());
    } catch (_) { body = {}; }
  }

  const { leads } = body;
  if (!Array.isArray(leads) || !leads.length) {
    return res.status(400).json({ error: "No leads provided. Pass { leads: [...] } in the request body." });
  }

  const senderName = process.env.SENDER_NAME || "NORML Agency";
  const agencyName = process.env.AGENCY_NAME || "NORML Agency";
  const fromAddr   = process.env.EMAIL_USER;

  let transporter;
  try { transporter = buildTransporter(); }
  catch (err) { return res.status(500).json({ error: err.message }); }

  let sent = 0, failed = 0, skipped = 0;
  const errors  = [];
  const results = [];

  for (const lead of leads) {
    const { name = "there", email, company = "", niche = "" } = lead;
    if (!email || !email.includes("@")) {
      skipped++;
      results.push({ email, status: "skipped" });
      continue;
    }
    try {
      await transporter.sendMail({
        from:    `"${senderName}" <${fromAddr}>`,
        to:      email,
        subject: `Quick note for ${company || name}`,
        text:    textBody(name, company, niche, agencyName, senderName),
        html:    htmlBody(name, company, niche, agencyName, senderName),
      });
      sent++;
      results.push({ email, status: "sent" });
    } catch (err) {
      failed++;
      errors.push({ email, error: err.message });
      results.push({ email, status: "failed", error: err.message });
    }
  }

  return res.status(200).json({
    success: true,
    total:   leads.length,
    sent, failed, skipped, errors, results,
  });
};
