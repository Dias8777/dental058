"""Хранилище: SQLite + файлы на диске. Одна БД на клинику."""
import os
import sqlite3
from datetime import date

DATA_DIR = os.environ.get("DENTAL_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
FILES_DIR = os.path.join(DATA_DIR, "files")
DB_PATH = os.path.join(DATA_DIR, "dental.db")

# Зубная формула по ВОЗ/FDI — как в бланке 058/у
UPPER = ["1.8", "1.7", "1.6", "1.5", "1.4", "1.3", "1.2", "1.1",
         "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"]
LOWER = ["4.8", "4.7", "4.6", "4.5", "4.4", "4.3", "4.2", "4.1",
         "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8"]
ALL_TEETH = UPPER + LOWER

TOOTH_STATES = {
    "":   ("здоров", "#ffffff"),
    "O":  ("зуб отсутствует", "#9e9e9e"),
    "R":  ("корень зуба", "#795548"),
    "C":  ("кариес", "#ff9800"),
    "P":  ("пульпит", "#f44336"),
    "Pt": ("периодонтит", "#b71c1c"),
    "П":  ("пломба", "#2196f3"),
    "A":  ("патология пародонта", "#9c27b0"),
    "K":  ("коронка", "#009688"),
    "И":  ("искусственный зуб", "#607d8b"),
}

CARD_TEXT_FIELDS = [
    ("diagnosis",       "11. Диагноз"),
    ("complaints",      "12. Жалобы"),
    ("past_diseases",   "13. Перенесённые и сопутствующие заболевания"),
    ("disease_history", "14. Развитие настоящего заболевания"),
    ("objective",       "15. Данные объективного исследования, внешний осмотр"),
    ("bite",            "16. Прикус"),
    ("mucosa",          "17. Состояние слизистой оболочки полости рта, дёсен, альвеолярных отростков и нёба"),
    ("xray",            "18. Данные рентгеновских, лабораторных исследований"),
    ("plan",            "20. План обследования, лечения (наименование услуги, лекарственные средства)"),
    ("results",         "21. Результаты лечения (эпикриз)"),
    ("recommendations", "22. Рекомендации"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    iin         TEXT,
    fio         TEXT NOT NULL,
    birth_date  TEXT,
    sex         TEXT,
    nationality TEXT,
    locality    TEXT,
    address     TEXT,
    workplace   TEXT,
    position    TEXT,
    education   TEXT,
    insurance   TEXT,
    phone       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    card_no     TEXT,
    open_date   TEXT,
    diagnosis   TEXT, complaints TEXT, past_diseases TEXT, disease_history TEXT,
    objective   TEXT, bite TEXT, mucosa TEXT, xray TEXT,
    plan        TEXT, results TEXT, recommendations TEXT,
    doctor      TEXT, head_doctor TEXT
);
CREATE TABLE IF NOT EXISTS teeth (
    card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    tooth   TEXT NOT NULL,
    state   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (card_id, tooth)
);
CREATE TABLE IF NOT EXISTS visits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id    INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    visit_date TEXT,
    text       TEXT,
    diagnosis  TEXT,
    doctor     TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    filename    TEXT,
    stored_name TEXT,
    kind        TEXT,
    note        TEXT,
    size        INTEGER,
    uploaded_at TEXT DEFAULT (datetime('now'))
);
"""


def conn():
    os.makedirs(FILES_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init():
    with conn() as c:
        c.executescript(SCHEMA)


def q(sql, args=(), one=False):
    with conn() as c:
        cur = c.execute(sql, args)
        rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def run(sql, args=()):
    with conn() as c:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid


# --- пациенты ---

def list_patients(search=""):
    if search:
        s = f"%{search.strip()}%"
        return q("SELECT * FROM patients WHERE fio LIKE ? OR iin LIKE ? OR phone LIKE ?"
                 " ORDER BY fio", (s, s, s))
    return q("SELECT * FROM patients ORDER BY fio")


def get_patient(pid):
    return q("SELECT * FROM patients WHERE id=?", (pid,), one=True)


def save_patient(pid, d):
    cols = ["iin", "fio", "birth_date", "sex", "nationality", "locality", "address",
            "workplace", "position", "education", "insurance", "phone"]
    vals = [d.get(k) for k in cols]
    if pid:
        run(f"UPDATE patients SET {', '.join(k + '=?' for k in cols)} WHERE id=?", vals + [pid])
        return pid
    return run(f"INSERT INTO patients ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals)


# --- карты ---

def get_or_create_card(pid):
    row = q("SELECT * FROM cards WHERE patient_id=? ORDER BY id LIMIT 1", (pid,), one=True)
    if row:
        return row
    cid = run("INSERT INTO cards (patient_id, card_no, open_date) VALUES (?,?,?)",
              (pid, str(pid), date.today().isoformat()))
    return q("SELECT * FROM cards WHERE id=?", (cid,), one=True)


def save_card(cid, d):
    cols = ["card_no", "open_date"] + [k for k, _ in CARD_TEXT_FIELDS] + ["doctor", "head_doctor"]
    run(f"UPDATE cards SET {', '.join(k + '=?' for k in cols)} WHERE id=?",
        [d.get(k) for k in cols] + [cid])


# --- зубы ---

def get_teeth(cid):
    return {r["tooth"]: r["state"] for r in q("SELECT tooth, state FROM teeth WHERE card_id=?", (cid,))}


def set_tooth(cid, tooth, state):
    run("INSERT INTO teeth (card_id, tooth, state) VALUES (?,?,?)"
        " ON CONFLICT(card_id, tooth) DO UPDATE SET state=excluded.state", (cid, tooth, state))


# --- приёмы ---

def list_visits(cid):
    return q("SELECT * FROM visits WHERE card_id=? ORDER BY visit_date DESC, id DESC", (cid,))


def add_visit(cid, d):
    return run("INSERT INTO visits (card_id, visit_date, text, diagnosis, doctor) VALUES (?,?,?,?,?)",
               (cid, d["visit_date"], d["text"], d["diagnosis"], d["doctor"]))


def delete_visit(vid):
    run("DELETE FROM visits WHERE id=?", (vid,))


# --- файлы ---

def list_files(pid):
    return q("SELECT * FROM files WHERE patient_id=? ORDER BY uploaded_at DESC", (pid,))


def add_file(pid, uploaded, kind, note):
    fid = run("INSERT INTO files (patient_id, filename, stored_name, kind, note, size) VALUES (?,?,?,?,?,?)",
              (pid, uploaded.name, "", kind, note, len(uploaded.getbuffer())))
    stored = f"{pid}_{fid}_{uploaded.name}"
    with open(os.path.join(FILES_DIR, stored), "wb") as f:
        f.write(uploaded.getbuffer())
    run("UPDATE files SET stored_name=? WHERE id=?", (stored, fid))
    return fid


def file_path(row):
    return os.path.join(FILES_DIR, row["stored_name"])


def delete_file(fid):
    row = q("SELECT * FROM files WHERE id=?", (fid,), one=True)
    if row:
        try:
            os.remove(file_path(row))
        except OSError:
            pass
        run("DELETE FROM files WHERE id=?", (fid,))
