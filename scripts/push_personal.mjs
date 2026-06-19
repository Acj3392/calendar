// Upload the real spending data to a PRIVATE Vercel Blob so the deployed
// /api/personal function can serve it (password-gated). Run after a Monarch
// refresh, or any time, with:  npm run push-personal
//
// Requires BLOB_READ_WRITE_TOKEN in the environment (it's in .env.local locally;
// the daily refresh sources that file before calling this).
import { put } from "@vercel/blob";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const file = fileURLToPath(new URL("../data/spending.json", import.meta.url));
const data = readFileSync(file);

if (!process.env.BLOB_READ_WRITE_TOKEN) {
  console.error("[push_personal] BLOB_READ_WRITE_TOKEN not set — cannot upload.");
  process.exit(1);
}

const blob = await put("personal/spending.json", data, {
  access: "private",
  contentType: "application/json",
  addRandomSuffix: false, // stable path the function reads
  allowOverwrite: true,   // replace the previous day's data
});

console.log(`[push_personal] uploaded ${data.length} bytes → ${blob.pathname} (private)`);
