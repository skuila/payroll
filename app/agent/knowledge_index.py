# agent/knowledge_index.py — Index persistant (PostgreSQL + embeddings) pour apprendre code & fichiers
from __future__ import annotations
import os
import json
from typing import List, Iterable, Dict, Optional
from contextlib import closing

from .openai_client import embed_texts

from config.connection_standard import open_connection, run_select

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent.knowledge_docs (
  id SERIAL PRIMARY KEY,
  path TEXT,
  kind TEXT,             -- 'code','doc','csv','txt','qna'
  title TEXT,
  meta TEXT,             -- JSON (ex: {"language":"py","period":"2024-09"})
  content TEXT,
  embedding TEXT,        -- JSON list of floats
  mtime DOUBLE PRECISION,
  UNIQUE(path, title, kind)
);
CREATE INDEX IF NOT EXISTS idx_docs_kind ON agent.knowledge_docs(kind);
"""


# --------- utils ---------
def _ensure_schema():
    """Crée le schéma PostgreSQL si nécessaire."""
    with closing(open_connection(autocommit=False)) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS agent")
                for stmt in _SCHEMA.strip().split(";"):
                    s = stmt.strip()
                    if s:
                        cur.execute(s)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _chunk(text: str, max_chars: int = 1800, overlap: int = 200) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    out = []
    i = 0
    while i < len(text):
        out.append(text[i : i + max_chars])
        i += max(1, max_chars - overlap)
    return out


# --------- ingestion ---------
_CODE_EXT = {".py", ".sql", ".md", ".txt", ".yml", ".yaml", ".ini", ".cfg"}
_DATA_EXT = {".csv", ".tsv"}


def _kind_for(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in _DATA_EXT:
        return "csv"
    if ext in _CODE_EXT:
        return "code"
    return "doc"


def upsert_path(
    path: str,
    title: Optional[str] = None,
    kind: Optional[str] = None,
    meta: Optional[Dict] = None,
) -> int:
    """Ingestion d'un fichier (code/doc/csv). Retourne nb de chunks indexés."""
    _ensure_schema()
    if not os.path.exists(path) or not os.path.isfile(path):
        return 0
    k = kind or _kind_for(path)
    mtime = os.path.getmtime(path)
    content = _read_file(path)

    # CSV: on ne garde qu’un extrait (en-têtes + 30 premières lignes) pour l’index
    if k == "csv":
        lines = content.splitlines()
        head = lines[:31]
        content = "\n".join(head)

    chunks = _chunk(content)
    if not chunks:
        return 0

    # embeddings
    embs = embed_texts(chunks)  # List[List[float]]

    with closing(open_connection(autocommit=False)) as conn:
        try:
            cnt = 0
            with conn.cursor() as cur:
                for i, (ch, vec) in enumerate(zip(chunks, embs), 1):
                    row_title = title or os.path.basename(path)
                    if len(chunks) > 1:
                        row_title = f"{row_title} [part {i}/{len(chunks)}]"
                    cur.execute(
                        """
                            INSERT INTO agent.knowledge_docs(path, kind, title, meta, content, embedding, mtime) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (path, title, kind) DO UPDATE SET
                                content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding,
                                meta = EXCLUDED.meta,
                                mtime = EXCLUDED.mtime
                        """,
                        (
                            path,
                            k,
                            row_title,
                            json.dumps(meta or {}),
                            ch,
                            json.dumps(vec),
                            mtime,
                        ),
                    )
                    cnt += 1
            conn.commit()
            return cnt
        except Exception:
            conn.rollback()
            raise


def upsert_dir(
    root: str,
    include: Iterable[str] = ("ui", "logic", "agent"),
    exts: Iterable[str] = (
        ".py",
        ".md",
        ".txt",
        ".yml",
        ".yaml",
        ".ini",
        ".cfg",
        ".sql",
        ".csv",
    ),
) -> int:
    """Ingestion récursive des sous-dossiers importants du projet."""
    _ensure_schema()
    root = os.path.abspath(root)
    wanted_dirs = {d.lower() for d in include}
    wanted_exts = {e.lower() for e in exts}
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # ne garder que les dossiers ciblés (si include fourni)
        if not any(
            part.lower() in wanted_dirs
            for part in dirpath.replace("\\", "/").split("/")
        ):
            continue
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in wanted_exts:
                fpath = os.path.join(dirpath, fn)
                try:
                    total += upsert_path(fpath)
                except Exception:
                    pass
    return total


# --------- recherche ---------
def _cosine(a: List[float], b: List[float]) -> float:
    import math

    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a)) or 1.0
    db = math.sqrt(sum(y * y for y in b)) or 1.0
    return num / (da * db)


def search(query: str, top_k: int = 8) -> List[Dict]:
    """Retourne les meilleurs passages : [{title, path, kind, content, score}]"""
    _ensure_schema()
    q_vec = embed_texts([query])[0]
    rows = run_select(
        "SELECT path, kind, title, content, embedding FROM agent.knowledge_docs"
    )

    scored = []
    for path, kind, title, content, emb_json in rows:
        try:
            vec = json.loads(emb_json)
            score = _cosine(q_vec, vec)
            scored.append(
                {
                    "path": path,
                    "kind": kind,
                    "title": title,
                    "content": content,
                    "score": score,
                }
            )
        except Exception:
            continue
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[: max(1, top_k)]
