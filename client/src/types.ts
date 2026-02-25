export type Milestone = 18 | 30 | 36 | 75 | 100 | 125 | 200;

export type BossKey = 'zul' | 'archeon' | 'bridge' | 'skorch' | 'dark';

export interface LeaderboardPlayer {
  account: string;
  character: string;
  className: string;
  stance: string;
  buildScore: number;
  ruptureLevel: number;
  seenMinutesEstimate: number;
  seenTimePerRupture: number;
  firstClears: Partial<Record<BossKey, boolean>>;
}
