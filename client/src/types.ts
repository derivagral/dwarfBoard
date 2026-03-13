export type Milestone = 18 | 30 | 36 | 75 | 100 | 125 | 200;

export type LeaderboardVariantKey = 'solo' | 'fellowship' | 'hardcore_solo' | 'hardcore_fellowship';

export interface SkillMods {
  goblet?: string;
  weapon?: string;
  horn?: string;
  belt?: string;
  trinket?: string;
}

export interface LeaderboardPlayer {
  account: string;
  character: string;
  className: string;
  stance: string;
  buildScore: number;
  ruptureLevel: number;
  seenMinutesEstimate: number;
  seenTimePerRupture: number;
  dungeons: Record<string, number>;
  dungeonFirstSeen: Record<string, string>;
  isOnline?: boolean;
  zone?: string;
  lastSeenAt?: string;
  variantHistory?: string[];
  skillName?: string;
  skillModifierCount?: number;
  skillMods?: SkillMods;
}

export interface LeaderboardPayload {
  generatedAt?: string;
  variants: Record<LeaderboardVariantKey, LeaderboardPlayer[]>;
}
