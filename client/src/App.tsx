import { useEffect, useMemo, useState } from 'react';

import './styles.css';
import { leaderboardPlayers as mockPlayers } from './mockData';
import { isPayloadWithVariants, normalizeRows } from './normalize';
import { LeaderboardPlayer, LeaderboardVariantKey, Milestone } from './types';

const milestones: Milestone[] = [18, 30, 36, 75, 100, 125, 200];
const variants: Array<{ key: LeaderboardVariantKey; label: string }> = [
  { key: 'solo', label: 'Solo' },
  { key: 'fellowship', label: 'Fellowship' },
  { key: 'hardcore_solo', label: 'Hardcore Solo' },
  { key: 'hardcore_fellowship', label: 'Hardcore Fellowship' },
];

function hasCleared(playerRupture: number, milestone: Milestone): boolean {
  return playerRupture >= milestone;
}

/** Return dungeon entries sorted by first-completion timestamp (earliest first). */
function sortedDungeons(player: LeaderboardPlayer): Array<[string, number]> {
  return Object.entries(player.dungeons).sort((a, b) => {
    const tsA = player.dungeonFirstSeen[a[0]] ?? '';
    const tsB = player.dungeonFirstSeen[b[0]] ?? '';
    if (tsA !== tsB) return tsA < tsB ? -1 : 1;
    return a[0].localeCompare(b[0]);
  });
}

/** Title-case a lowercase dungeon name (e.g. "dark drythus" → "Dark Drythus"). */
function dungeonDisplayName(name: string): string {
  return name.replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildTooltipText(player: LeaderboardPlayer): string {
  const lines = ['Dungeon clears (by first completion):'];
  for (const [name, count] of sortedDungeons(player)) {
    lines.push(`- ${dungeonDisplayName(name)}: ${count}`);
  }
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
              <th>Stance</th>
              <th>Zone</th>
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
              const dungeonEntries = sortedDungeons(player);
              return (
                <tr key={rowKey}>
                  <td>{idx + 1}</td>
                  <td>
                    {player.account}
                    {player.variantHistory && player.variantHistory.length > 1 && (
                      <span className="badge subtle" title={`Also seen in: ${player.variantHistory.filter((v) => v !== variant).join(', ')}`}>
                        {' '}ex-{player.variantHistory.find((v) => v !== variant)}
                      </span>
                    )}
                  </td>
                  <td>
                    {player.character}
                    {player.isOnline && <span className="online-dot" title="Online now" />}
                  </td>
                  <td>{player.stance}</td>
                  <td>{player.zone || '-'}</td>
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
                      {dungeonEntries.length} dungeon{dungeonEntries.length !== 1 ? 's' : ''}
                    </button>
                    {openClearsKey === rowKey && (
                      <div className="inlineTooltip">
                        <strong>Dungeon clears (first completion order)</strong>
                        <ul>
                          {dungeonEntries.map(([name, count]) => (
                            <li key={name}>
                              <span>{dungeonDisplayName(name)}:</span> {count}
                            </li>
                          ))}
                        </ul>
                        {dungeonEntries.length === 0 && <p className="subtle">No dungeon clears recorded</p>}
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
