import { z } from "zod";
import { isAbsolute } from "node:path";
import { recordHash } from "./checksum.js";

export const resultOptions = {
  include_marked_content: true, disable_normalization: false, use_system_fonts: false,
  disable_font_face: true, use_worker_fetch: false, verbosity: 0,
} as const;
export const identity = {
  contract_schema_version: "1.1", extractor_version: "1.1.0", pdfjs_version: "6.2.108",
  normalization_version: "textitem-norm-2", options_hash: recordHash(resultOptions),
};

const boundedText = (maximum: number) => z.string().max(maximum).refine(value => value.isWellFormed());
const finite = z.number().finite();
export const textItemSchema = z.object({
  item_index: z.number().int().nonnegative(), source_array_index: z.number().int().nonnegative(),
  text: boundedText(20000), direction: z.enum(["ltr", "rtl", "ttb"]),
  transform: z.tuple([finite, finite, finite, finite, finite, finite]),
  width: finite.nonnegative(), height: finite.nonnegative(), font_name: boundedText(256).nullable(), has_eol: z.boolean(),
}).strict();
export const styleSchema = z.object({
  font_family: boundedText(256), ascent: finite.nullable(), descent: finite.nullable(), vertical: z.boolean(),
}).strict();

export const configSchema = z.object({
  contract_schema_version: z.literal("1.1"),
  include_marked_content: z.literal(true), disable_normalization: z.literal(false),
  use_system_fonts: z.literal(false), disable_font_face: z.literal(true),
  use_worker_fetch: z.literal(false), verbosity: z.literal(0),
  max_pages: z.number().int().min(1).max(500),
  max_items_per_page: z.number().int().min(1).max(50000),
  max_item_characters: z.number().int().min(1).max(20000),
  max_file_bytes: z.number().int().positive().max(1024 ** 3),
  max_line_bytes: z.number().int().positive().max(128 * 1024 ** 2),
  max_output_bytes: z.number().int().positive().max(1024 ** 3),
}).strict();
export type Config = z.infer<typeof configSchema>;

export const argumentSchema = z.object({
  "--input": z.string().refine(isAbsolute).refine(value => value.toLowerCase().endsWith(".pdf")),
  "--expected-sha256": z.string().regex(/^[a-f0-9]{64}$/),
  "--request-id": boundedText(128).min(1),
  "--options-file": z.string().refine(isAbsolute),
}).strict();
export type Arguments = z.infer<typeof argumentSchema>;
