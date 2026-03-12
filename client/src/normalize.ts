import { LeaderboardPayload, LeaderboardPlayer, SkillMods } from './types';

/** Raw shape coming from either the Python ETL (snake_case) or a pre-normalized payload (camelCase). */
type LeaderboardJsonRow = {
  account?: unknown;
  character?: unknown;
  class_name?: unknown;
  className?: unknown;
  stance?: unknown;
  build_score?: unknown;
  buildScore?: unknown;
  rupture_level?: unknown;
  ruptureLevel?: unknown;
  seen_minutes_estimate?: unknown;
  seenMinutesEstimate?: unknown;
  seen_time_per_rupture?: unknown;
  seenTimePerRupture?: unknown;
  dungeons?: unknown;
  dungeon_first_seen?: unknown;
  dungeonFirstSeen?: unknown;
  zone?: unknown;
  last_seen_at?: unknown;
  lastSeenAt?: unknown;
  variant_history?: unknown;
  variantHistory?: unknown;
  skill_name?: unknown;
  skillName?: unknown;
  skill_modifier_count?: unknown;
  skillModifierCount?: unknown;
  skill_mods?: unknown;
  skillMods?: unknown;
};

export function asNumber(value: unknown, fallback = 0): number {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

export function asString(value: unknown, fallback = 'unknown'): string {
  if (typeof value !== 'string') {
    return fallback;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : fallback;
}

export function asBoolean(value: unknown): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value > 0;
  if (typeof value === 'string') {
    const lower = value.toLowerCase();
    return lower === 'true' || lower === '1' || lower === 'yes';
  }
  return false;
}

function normalizeSkillMods(value: unknown): SkillMods {
  if (!value || typeof value !== 'object') return {};
  const mods = value as Record<string, unknown>;
  return {
    goblet: asString(mods.goblet, ''),
    weapon: asString(mods.weapon, ''),
    horn: asString(mods.horn, ''),
    belt: asString(mods.belt, ''),
    trinket: asString(mods.trinket, ''),
  };
}

function normalizeStance(value: unknown): string {
  const raw = asString(value, '').toLowerCase();
  if (!raw) return 'unknown';

  const normalized = raw.replace(/[^a-z0-9]+/g, ' ').trim();
  const compact = normalized.replace(/\s+/g, '');

  if (normalized === 'bow') return 'bow';
  if (normalized === 'wand') return 'wand';
  if (normalized === 'maul' || normalized === 'polearm' || normalized === 'pole arm') return 'maul';
  if (normalized === 'spear') return 'spear';
  if (normalized === 'scythe') return 'scythe';
  if (normalized === 'fists' || normalized === 'fist' || normalized === 'common' || normalized === 'unarmed') return 'fists';

  if (
    normalized === 'sword' ||
    normalized === 'dual' ||
    normalized === 'dual wield' ||
    normalized === 'dualwield' ||
    normalized === '1h' ||
    normalized === '1 h' ||
    normalized === 'one hand' ||
    normalized === 'one handed' ||
    compact === 'onehand' ||
    compact === 'onehanded'
  ) {
    return 'sword';
  }

  if (
    normalized === 'axe' ||
    normalized === '2h' ||
    normalized === '2 h' ||
    normalized === 'two hand' ||
    normalized === 'two handed' ||
    compact === 'twohand' ||
    compact === 'twohanded'
  ) {
    return 'axe';
  }

  return 'unknown';
}

function normalizeVariantHistory(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === 'string');
}

function normalizeDungeons(value: unknown): Record<string, number> {
  if (!value || typeof value !== 'object') return {};
  const result: Record<string, number> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    const count = asNumber(v, 0);
    if (count > 0) result[k] = count;
  }
  return result;
}

function normalizeDungeonFirstSeen(value: unknown): Record<string, string> {
  if (!value || typeof value !== 'object') return {};
  const result: Record<string, string> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (typeof v === 'string' && v.length > 0) result[k] = v;
  }
  return result;
}

export function normalizeRows(rows: unknown[]): LeaderboardPlayer[] {
  return rows
    .map((row): LeaderboardPlayer | null => {
      if (!row || typeof row !== 'object') return null;
      const data = row as LeaderboardJsonRow;
      return {
        account: asString(data.account),
        character: asString(data.character),
        className: asString(data.className ?? data.class_name),
        stance: normalizeStance(data.stance),
        buildScore: asNumber(data.buildScore ?? data.build_score),
        ruptureLevel: asNumber(data.ruptureLevel ?? data.rupture_level),
        seenMinutesEstimate: asNumber(data.seenMinutesEstimate ?? data.seen_minutes_estimate),
        seenTimePerRupture: asNumber(data.seenTimePerRupture ?? data.seen_time_per_rupture),
        dungeons: normalizeDungeons(data.dungeons),
        dungeonFirstSeen: normalizeDungeonFirstSeen(data.dungeonFirstSeen ?? data.dungeon_first_seen),
        zone: asString(data.zone, ''),
        lastSeenAt: asString(data.lastSeenAt ?? data.last_seen_at, ''),
        variantHistory: normalizeVariantHistory(data.variantHistory ?? data.variant_history),
        skillName: asString(data.skillName ?? data.skill_name, ''),
        skillModifierCount: asNumber(data.skillModifierCount ?? data.skill_modifier_count),
        skillMods: normalizeSkillMods(data.skillMods ?? data.skill_mods),
      };
    })
    .filter((row): row is LeaderboardPlayer => row !== null);
}

export function isPayloadWithVariants(value: unknown): value is LeaderboardPayload {
  return Boolean(value && typeof value === 'object' && 'variants' in (value as Record<string, unknown>));
}
