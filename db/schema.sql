-- Offline schema reference (SQLite)
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  display_name TEXT DEFAULT '',
  role TEXT DEFAULT 'agent',
  email TEXT DEFAULT '',
  active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY,
  project_id TEXT DEFAULT 'default',
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  status TEXT DEFAULT 'aktywna',
  source TEXT DEFAULT '',
  budget REAL DEFAULT 0,
  target_leads INTEGER DEFAULT 0,
  current_leads INTEGER DEFAULT 0,
  conversion_rate REAL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY,
  project_id TEXT DEFAULT 'default',
  full_name TEXT DEFAULT '',
  email TEXT DEFAULT '',
  phone TEXT DEFAULT '',
  company TEXT DEFAULT '',
  industry TEXT DEFAULT '',
  voivodeship TEXT DEFAULT '',
  source TEXT DEFAULT '',
  campaign_id INTEGER,
  assigned_to TEXT DEFAULT '',
  stage TEXT DEFAULT 'nowy',
  score REAL DEFAULT 0,
  conversion_probability REAL DEFAULT 0,
  notes TEXT DEFAULT '',
  tags TEXT DEFAULT '',
  follow_up_at TEXT,
  closed_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS offers (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  content TEXT DEFAULT '',
  amount REAL DEFAULT 0,
  status TEXT DEFAULT 'draft',
  generated_offline INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER NOT NULL,
  offer_id INTEGER,
  amount REAL DEFAULT 0,
  status TEXT DEFAULT 'pending',
  method TEXT DEFAULT 'offline_transfer',
  confirmation_code TEXT DEFAULT '',
  log TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(lead_id) REFERENCES leads(id),
  FOREIGN KEY(offer_id) REFERENCES offers(id)
);

CREATE TABLE IF NOT EXISTS automations (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  trigger TEXT DEFAULT '',
  action TEXT DEFAULT '',
  condition_json TEXT DEFAULT '{}',
  enabled INTEGER DEFAULT 1,
  runs INTEGER DEFAULT 0,
  last_run TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY,
  level TEXT DEFAULT 'info',
  module TEXT DEFAULT 'engine',
  message TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  event_type TEXT DEFAULT '',
  payload_json TEXT DEFAULT '{}',
  source TEXT DEFAULT 'offline',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
