import { z } from "zod";

// The snapshot is written by the Python collector and read here. This schema is the contract between them:
// if the collector's output ever stops matching, the site keeps the last good copy and says so.

export const FactSchema = z.object({
  value: z.string(),
  label: z.string(),
  evidence: z.string(),
  source: z.enum(["text", "title", "feed"]),
  mark: z.string().nullable().optional(),
});

export const PlaceSchema = z.object({ emirate: z.string(), raw: z.string() });

export const KINDS = ["internship", "graduate", "first_job"] as const;
export const FACT_KEYS = ["eligibility", "pay", "duration", "start", "stage", "mode", "deadline"] as const;

export const RoleSchema = z.object({
  id: z.string(),
  slug: z.string(),
  employer: z.string(),
  board: z.string(),
  system: z.string(),
  title: z.string(),
  url: z.string().url().refine((u) => u.startsWith("https://"), "links must be https"),
  places: z.array(PlaceSchema).min(1),
  elsewhere: z.number().int().nonnegative(),
  kind: z.enum(KINDS),
  kind_reason: z.string(),
  fields: z.array(z.string()).min(1),
  skills: z.array(z.string()).default([]),
  facts: z.partialRecord(z.enum(FACT_KEYS), FactSchema),
  department: z.string().nullable().optional(),
  excerpt: z.string(),
  posted_at: z.string().nullable().optional(),
  first_seen: z.string(),
  last_seen: z.string(),
  changed_at: z.string().nullable().optional(),
  status: z.enum(["open", "closed"]),
  closed_at: z.string().nullable().optional(),
});

export const BoardSchema = z.object({
  key: z.string(),
  name: z.string(),
  system: z.string(),
  home: z.string().nullable().optional(),
  ok: z.boolean(),
  checked_at: z.string(),
  last_ok: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
  postings: z.number().int(),
  uae: z.number().int(),
  student: z.number().int(),
});

export const SnapshotSchema = z.object({
  schema_version: z.literal(1),
  rules_version: z.number().int(),
  generated_at: z.string(),
  started_at: z.string(),
  roles: z.array(RoleSchema),
  boards: z.array(BoardSchema),
  not_covered: z.array(z.object({ name: z.string(), reason: z.string() })),
});

export type Fact = z.infer<typeof FactSchema>;
export type Role = z.infer<typeof RoleSchema>;
export type Board = z.infer<typeof BoardSchema>;
export type Snapshot = z.infer<typeof SnapshotSchema>;
export type Kind = (typeof KINDS)[number];
export type FactKey = (typeof FACT_KEYS)[number];
