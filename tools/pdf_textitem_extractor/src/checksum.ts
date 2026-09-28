import { createHash } from "node:crypto";

export function digest(value: string | Uint8Array): string {
  return createHash("sha256").update(value).digest("hex");
}

function project(value: unknown): unknown {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("INVALID_ARGUMENT");
    const buffer = Buffer.alloc(8);
    buffer.writeDoubleBE(value === 0 ? 0 : value);
    return { $f64: buffer.toString("hex") };
  }
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "string") {
    if (!value.isWellFormed()) throw new Error("INVALID_ARGUMENT");
    return value;
  }
  if (Array.isArray(value)) return value.map(project);
  if (typeof value === "object") {
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
      .map(([key, entry]) => [key, project(entry)]));
  }
  throw new Error("INVALID_ARGUMENT");
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(project(value));
}

export function recordHash(value: unknown): string {
  return digest(canonicalJson(value));
}
