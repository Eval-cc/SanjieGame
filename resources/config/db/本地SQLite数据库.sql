--# 系统表
CREATE TABLE IF NOT EXISTS system_settings
                               (
                                   key
                                   TEXT
                                   PRIMARY
                                   KEY,
                                   value
                                   TEXT
                               )
--# 账号表
CREATE TABLE IF NOT EXISTS accounts
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   username
                                   TEXT
                                   UNIQUE
                                   NOT
                                   NULL,
                                   password
                                   TEXT
                                   NOT
                                   NULL,
                                   login_time
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP,
                                   latest_time
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP,
                                   is_lock
                                   INTEGER
                                   DEFAULT
                                   0 -- 0:正常, 1:锁定
                               )

--# 角色表
CREATE TABLE IF NOT EXISTS fso
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   account_id
                                   INTEGER
                                   NOT
                                   NULL, -- 归属于哪个账号
                                   avatar
                                   TEXT,
                                   name
                                   TEXT,
                                   scene_id
                                   TEXT,
                                   sx
                                   REAL,
                                   sy
                                   REAL,
                                   healthy
                                   INTEGER,
                                   mana
                                   INTEGER,
                                   attack
                                   INTEGER,
                                   defense
                                   INTEGER,
                                   attack_speed
                                   INTEGER,
                                   anim_model
                                   TEXT,
                                   items
                                   TEXT,
                                   FOREIGN
                                   KEY
                               (
                                   account_id
                               ) REFERENCES accounts
                               (
                                   id
                               )
                                   )