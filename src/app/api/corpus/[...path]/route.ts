import { NextRequest, NextResponse } from "next/server";
import path from "path";
import fs from "fs";

/**
 * GET /api/corpus/<subpath>
 *
 * Serves a file from the project's `corpus/` directory. Used by the Practice
 * Hub to render question images and screenshots that live alongside the JSON
 * corpus (800+ PNGs).
 *
 * Path is resolved relative to <cwd>/corpus and then realpath-validated to
 * ensure it cannot escape the corpus root (defense against `..` and symlinks).
 *
 * Examples:
 *   /api/corpus/images/ENGAA-2016-S1-Q6-fig1.png   -> question figure
 *   /api/corpus/images/tmua/TMUA-2017-P2-Q14-optA.png
 *   /api/corpus/esat_screenshots/biology/q01.png
 */

const CORPUS_ROOT = path.resolve(process.cwd(), "corpus");

const MIME: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
};

const ALLOWED_EXT = new Set(Object.keys(MIME));

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await params;

  // Reject obvious traversal early.
  if (segments.some((s) => s === ".." || s === "." || s.includes("\0"))) {
    return NextResponse.json({ error: "Invalid path" }, { status: 400 });
  }

  const rel = segments.join("/");
  const ext = path.extname(rel).toLowerCase();
  if (!ALLOWED_EXT.has(ext)) {
    return NextResponse.json({ error: "Unsupported file type" }, { status: 400 });
  }

  const abs = path.join(CORPUS_ROOT, rel);

  // Realpath resolves symlinks + collapses `..` — if the result is not inside
  // CORPUS_ROOT, refuse.
  let real: string;
  try {
    real = fs.realpathSync(abs);
  } catch {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  if (real !== CORPUS_ROOT && !real.startsWith(CORPUS_ROOT + path.sep)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  let stat: fs.Stats;
  try {
    stat = fs.statSync(real);
  } catch {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  if (!stat.isFile()) {
    return NextResponse.json({ error: "Not a file" }, { status: 404 });
  }

  const body = fs.readFileSync(real);
  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type": MIME[ext],
      "Content-Length": String(body.length),
      "Cache-Control": "public, max-age=86400, immutable",
    },
  });
}
