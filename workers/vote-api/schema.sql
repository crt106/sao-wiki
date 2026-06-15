CREATE TABLE IF NOT EXISTS vote_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  poll_id TEXT NOT NULL,
  hero_slug TEXT NOT NULL,
  voter_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (poll_id, hero_slug, voter_hash)
);

CREATE TABLE IF NOT EXISTS vote_totals (
  poll_id TEXT NOT NULL,
  hero_slug TEXT NOT NULL,
  votes INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (poll_id, hero_slug)
);

CREATE INDEX IF NOT EXISTS idx_vote_totals_poll_votes
ON vote_totals (poll_id, votes DESC);
