-- Create the players table for PostgreSQL
-- Note: In Render, the database 'sd_parques' is created automatically
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    games_played INT DEFAULT 0,
    games_won INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_username ON players(username);
CREATE INDEX IF NOT EXISTS idx_win_percentage ON players(games_won, games_played);
