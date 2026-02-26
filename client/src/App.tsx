import { useEffect, useMemo, useState } from 'react';

import './styles.css';
import { leaderboardPlayers as mockPlayers } from './mockData';
import { BossKey, LeaderboardPlayer, Milestone } from './types';

const milestones: Milestone[] = [18, 30, 36, 75, 100, 125, 200];
const bosses: BossKey[] = ['zul', 'archeon', 'bridge', 'skorch', 'dark'];

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
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number') {
    return value > 0;
  }
  if (typeof value === 'string') {
    const lower = value.toLowerCase();
    return lower === 'true' || lower === '1' || lower === 'yes';
  }
  return false;
}

function normalizeRows(rows: unknown[]): LeaderboardPlayer[] {
  return rows
    .map((row): LeaderboardPlayer | null => {
      if (!row || typeof row !== 'object') {
        return null;
      }

      const data = row as LeaderboardJsonRow;
      const account = asString(data.account);
      const character = asString(data.character);

      return {
        account,
        character,
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
      };
    })
    .filter((row): row is LeaderboardPlayer => row !== null);
}

function hasCleared(playerRupture: number, milestone: Milestone): boolean {
  return playerRupture >= milestone;
}

function formatSourceLabel(loadFailed: boolean, playersCount: number): string {
  if (loadFailed) {
    return `Using bundled fallback data (${playersCount} rows).`;
  }
  return `Loaded generated leaderboard snapshot (${playersCount} rows).`;
}

export default function App() {
  const [players, setPlayers] = useState<LeaderboardPlayer[]>(mockPlayers);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    async function loadLeaderboard(): Promise<void> {
      try {
        const response = await fetch('./leaderboard.json', { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const rows = await response.json();
        if (!Array.isArray(rows)) {
          throw new Error('unexpected leaderboard payload shape');
        }
        const normalized = normalizeRows(rows);
        if (normalized.length === 0) {
          throw new Error('empty leaderboard payload');
        }
        setPlayers(normalized);
        setLoadFailed(false);
      } catch {
        setPlayers(mockPlayers);
        setLoadFailed(true);
      }
    }

    void loadLeaderboard();
  }, []);

  const sourceLabel = useMemo(() => formatSourceLabel(loadFailed, players.length), [loadFailed, players.length]);

  return (
    <main className="page">
      <header className="header">
        <h1>dwarfBoard Leaderboard</h1>
        <p>
          Base view includes Build, Rupture, and Seen Time / Rupture. Hover over the clears badge for boss and
          milestone detail.
        </p>
        <p className="subtle">{sourceLabel}</p>
      </header>

      <section className="cards">
        <article className="card">
          <h2>Build</h2>
          <p>Rank by build score and class profile.</p>
        </article>
        <article className="card">
          <h2>Rupture Progress</h2>
          <p>Current rupture level with milestone tracking scaffolded.</p>
        </article>
        <article className="card">
          <h2>Seen Time</h2>
          <p>Estimated via scan cadence (currently hourly, ready for 10m cadence).</p>
        </article>
        <article className="card">
          <h2>First Clears</h2>
          <p>Zul, Archeon, Bridge, Skorch, and Dark bosses included in tooltip details.</p>
        </article>
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
            {players.map((player, idx) => (
              <tr key={`${player.account}-${player.character}`}>
                <td>{idx + 1}</td>
                <td>{player.account}</td>
                <td>{player.character}</td>
                <td>{player.className}</td>
                <td>{player.buildScore}</td>
                <td>{player.ruptureLevel}</td>
                <td>
                  {player.seenTimePerRupture}m
                  <span className="subtle"> ({player.seenMinutesEstimate}m total)</span>
                </td>
                <td>
                  <span
                    className="badge"
                    title={[
                      'Boss first clears:',
                      ...bosses.map((boss) => `- ${boss}: ${player.firstClears[boss] ? 'yes' : 'no'}`),
                      '',
                      'Rupture milestones:',
                      ...milestones.map((m) => `- r${m}: ${hasCleared(player.ruptureLevel, m) ? 'cleared' : 'pending'}`),
                    ].join('\n')}
                  >
                    Hover
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
