// Server-side gate for the real spending data.
//
// The Personal App view POSTs { password } here. We verify it against the
// PERSONAL_PASSCODE env var (server-side — the passcode never ships to the
// browser) and, only on success, stream back the real data from a PRIVATE Vercel
// Blob. The real data therefore never lives at a publicly fetchable URL.
const { get } = require("@vercel/blob");

const BLOB_PATH = "personal/spending.json";

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const passcode = process.env.PERSONAL_PASSCODE;

  // Robust body parse: Vercel usually populates req.body, but fall back to
  // reading the raw stream if it's empty/undefined.
  let body = req.body;
  if (body == null || body === "") {
    try {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const raw = Buffer.concat(chunks).toString("utf8");
      body = raw ? JSON.parse(raw) : {};
    } catch { body = {}; }
  } else if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const supplied = body && body.password;

  if (!passcode) {
    res.status(500).json({ error: "PERSONAL_PASSCODE is not configured" });
    return;
  }
  if (supplied !== passcode) {
    // Temporary diagnostic: whether the request body/password was parsed at all.
    // Reveals nothing about the server-side passcode. Remove after debugging.
    res.status(401).json({
      error: "Incorrect password",
      debug: { passwordReceived: supplied != null && supplied !== "" },
    });
    return;
  }

  try {
    const result = await get(BLOB_PATH, { access: "private" });
    if (!result || !result.stream) {
      res.status(404).json({ error: "No personal data has been uploaded yet" });
      return;
    }
    const text = await new Response(result.stream).text();
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Cache-Control", "no-store, max-age=0");
    res.status(200).send(text);
  } catch (e) {
    res.status(500).json({ error: String((e && e.message) || e) });
  }
};
