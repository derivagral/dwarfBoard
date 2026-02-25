import './styles.css';
import { leaderboardPlayers } from './mockData';
import { BossKey, Milestone } from './types';

const milestones: Milestone[] = [18, 30, 36, 75, 100, 125, 200];
const bosses: BossKey[] = ['zul', 'archeon', 'bridge', 'skorch', 'dark'];

function hasCleared(playerRupture: number, milestone: Milestone): boolean {
  return playerRupture >= milestone;
}

export default function App() {
  return (
    <main className="page">
      <header className="header">
        <h1>dwarfBoard Leaderboard</h1>
        <p>
          Base view includes Build, Rupture, and Seen Time / Rupture. Hover over the clears badge for boss and
          milestone detail.
        </p>
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
            {leaderboardPlayers.map((player, idx) => (
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
