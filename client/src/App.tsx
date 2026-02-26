import { useEffect, useMemo, useState } from 'react';

import './styles.css';
import { leaderboardPlayers as mockPlayers } from './mockData';
import {
  BossKey,
  LeaderboardPayload,
  LeaderboardPlayer,
  LeaderboardVariantKey,
  Milestone,
  SkillMods,
} from './types';

const milestones: Milestone[] = [18, 30, 36, 75, 100, 125, 200];
const bosses: BossKey[] = ['zul', 'archeon', 'bridge', 'skorch', 'dark'];
const variants: Array<{ key: LeaderboardVariantKey; label: string }> = [
  { key: 'solo', label: 'Solo' },
  { key: 'fellowship', label: 'Fellowship' },
  { key: 'hardcore_solo', label: 'Hardcore Solo' },
  { key: 'hardcore_fellowship', label: 'Hardcore Fellowship' },
];

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
  first_clear_zul?: unknown;
  first_clear_archeon?: unknown;
  first_clear_bridge?: unknown;
  first_clear_skorch?: unknown;
  first_clear_dark?: unknown;
  firstClears?: Partial<Record<BossKey, boolean>>;
  skill_name?: unknown;
  skillName?: unknown;
  skill_modifier_count?: unknown;
  skillModifierCount?: unknown;
  skill_mods?: unknown;
  skillMods?: unknown;
};

function asNumber(value: unknown, fallback = 0): number {
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function asString(value: unknown, fallback = 'unknown'): string {
  if (typeof value !== 'string') {
    return fallback;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : fallback;
}

function asBoolean(value: unknown): boolean {
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

function normalizeRows(rows: unknown[]): LeaderboardPlayer[] {
  return rows
    .map((row): LeaderboardPlayer | null => {
      if (!row || typeof row !== 'object') return null;
      const data = row as LeaderboardJsonRow;
      return {
        account: asString(data.account),
        character: asString(data.character),
        className: asString(data.className ?? data.class_name),
        stance: asString(data.stance),
        buildScore: asNumber(data.buildScore ?? data.build_score),
        ruptureLevel: asNumber(data.ruptureLevel ?? data.rupture_level),
        seenMinutesEstimate: asNumber(data.seenMinutesEstimate ?? data.seen_minutes_estimate),
        seenTimePerRupture: asNumber(data.seenTimePerRupture ?? data.seen_time_per_rupture),
        firstClears: {
          zul: asBoolean(data.firstClears?.zul ?? data.first_clear_zul),
          archeon: asBoolean(data.firstClears?.archeon ?? data.first_clear_archeon),
          bridge: asBoolean(data.firstClears?.bridge ?? data.first_clear_bridge),
          skorch: asBoolean(data.firstClears?.skorch ?? data.first_clear_skorch),
          dark: asBoolean(data.firstClears?.dark ?? data.first_clear_dark),
        },
        skillName: asString(data.skillName ?? data.skill_name, ''),
        skillModifierCount: asNumber(data.skillModifierCount ?? data.skill_modifier_count),
        skillMods: normalizeSkillMods(data.skillMods ?? data.skill_mods),
      };
    })
    .filter((row): row is LeaderboardPlayer => row !== null);
}

function hasCleared(playerRupture: number, milestone: Milestone): boolean {
  return playerRupture >= milestone;
}

function isPayloadWithVariants(value: unknown): value is LeaderboardPayload {
  return Boolean(value && typeof value === 'object' && 'variants' in (value as Record<string, unknown>));
}

function buildTooltipText(player: LeaderboardPlayer): string {
  const lines = ['Boss first clears:'];
  for (const boss of bosses) lines.push(`- ${boss}: ${player.firstClears[boss] ? 'yes' : 'no'}`);
  lines.push('', 'Rupture milestones:');
  for (const m of milestones) lines.push(`- r${m}: ${hasCleared(player.ruptureLevel, m) ? 'cleared' : 'pending'}`);
  return lines.join('\n');
}

function buildSkillSummary(player: LeaderboardPlayer): string {
  if (!player.skillName) return `${player.buildScore}`;
  if ((player.skillModifierCount ?? 0) <= 0) return `${player.buildScore} • ${player.skillName}`;
  return `${player.buildScore} • ${player.skillName} (${player.skillModifierCount}/5)`;
}

export default function App() {
  const [variant, setVariant] = useState<LeaderboardVariantKey>('solo');
  const [variantRows, setVariantRows] = useState<Record<LeaderboardVariantKey, LeaderboardPlayer[]>>({
    solo: mockPlayers,
    fellowship: [],
    hardcore_solo: [],
    hardcore_fellowship: [],
  });
  const [loadFailed, setLoadFailed] = useState(false);
  const [openClearsKey, setOpenClearsKey] = useState<string | null>(null);
  const [openBuildKey, setOpenBuildKey] = useState<string | null>(null);

  useEffect(() => {
    async function loadLeaderboard(): Promise<void> {
      try {
        const response = await fetch('./leaderboard.json', { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();

        if (Array.isArray(payload)) {
          const normalized = normalizeRows(payload);
          if (normalized.length === 0) throw new Error('empty leaderboard payload');
          setVariantRows({ solo: normalized, fellowship: [], hardcore_solo: [], hardcore_fellowship: [] });
          setLoadFailed(false);
          return;
        }

        if (!isPayloadWithVariants(payload)) throw new Error('unexpected leaderboard payload shape');

        const normalizedVariants: Record<LeaderboardVariantKey, LeaderboardPlayer[]> = {
          solo: normalizeRows(payload.variants.solo ?? []),
          fellowship: normalizeRows(payload.variants.fellowship ?? []),
          hardcore_solo: normalizeRows(payload.variants.hardcore_solo ?? []),
          hardcore_fellowship: normalizeRows(payload.variants.hardcore_fellowship ?? []),
        };
        if (!Object.values(normalizedVariants).some((rows) => rows.length > 0)) {
          throw new Error('empty leaderboard variants payload');
        }

        setVariantRows(normalizedVariants);
        setVariant((current) => (normalizedVariants[current].length ? current : 'solo'));
        setLoadFailed(false);
      } catch {
        setVariantRows({ solo: mockPlayers, fellowship: [], hardcore_solo: [], hardcore_fellowship: [] });
        setVariant('solo');
        setLoadFailed(true);
      }
    }

    void loadLeaderboard();
  }, []);

  const players = variantRows[variant] ?? [];
  const sourceLabel = useMemo(() => {
    if (loadFailed) return `Using bundled fallback data (${players.length} rows).`;
    return `Loaded generated leaderboard snapshot (${players.length} rows in ${variant.replace('_', ' ')}).`;
  }, [loadFailed, players.length, variant]);

  return (
    <main className="page">
      <header className="header">
        <h1>dwarfBoard Leaderboard</h1>
        <p>Base view includes Build, Rupture, and Seen Time / Rupture. Click clears/build badges for details.</p>
        <p className="subtle">{sourceLabel}</p>
      </header>

      <section className="variantTabs" aria-label="Leaderboard type">
        {variants.map(({ key, label }) => (
          <button
            key={key}
            className={`variantTab ${variant === key ? 'active' : ''}`}
            onClick={() => {
              setVariant(key);
              setOpenClearsKey(null);
              setOpenBuildKey(null);
            }}
            disabled={(variantRows[key] ?? []).length === 0}
            type="button"
          >
            {label}
          </button>
        ))}
      </section>

      <section>
        <table className="leaderboard">
          <thead>
            <tr>
              <th>#</th>
              <th>Account</th>
              <th>Character</th>
              <th>Class</th>
              <th>Build</th>
              <th>Rupture</th>
              <th>Seen Time / Rupture</th>
              <th>Clears</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player, idx) => {
              const rowKey = `${player.account}-${player.character}`;
              const skillMods = player.skillMods ?? {};
              return (
                <tr key={rowKey}>
                  <td>{idx + 1}</td>
                  <td>{player.account}</td>
                  <td>{player.character}</td>
                  <td>{player.className}</td>
                  <td>
                    <button
                      className="badge"
                      type="button"
                      onClick={() => setOpenBuildKey(openBuildKey === rowKey ? null : rowKey)}
                      title="Build details"
                    >
                      {buildSkillSummary(player)}
                    </button>
                    {openBuildKey === rowKey && (
                      <div className="inlineTooltip">
                        <strong>Modifiers</strong>
                        <ul>
                          {Object.entries(skillMods).map(([slot, value]) => (
                            <li key={slot}>
                              <span>{slot}:</span> {value || 'n/a'}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </td>
                  <td>{player.ruptureLevel}</td>
                  <td>
                    {player.seenTimePerRupture}m
                    <span className="subtle"> ({player.seenMinutesEstimate}m total)</span>
                  </td>
                  <td>
                    <button
                      className="badge"
                      type="button"
                      onClick={() => setOpenClearsKey(openClearsKey === rowKey ? null : rowKey)}
                      title={buildTooltipText(player)}
                    >
                      Details
                    </button>
                    {openClearsKey === rowKey && (
                      <div className="inlineTooltip">
                        <strong>Boss first clears</strong>
                        <ul>
                          {bosses.map((boss) => (
                            <li key={boss}>
                              <span>{boss}:</span> {player.firstClears[boss] ? 'yes' : 'no'}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </main>
  );
}
