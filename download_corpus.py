#!/usr/bin/env python3
"""Télécharge les documents listés dans corpus.csv, extrait leur texte
et enregistre la date et l'empreinte SHA-256 de chaque fichier.

Usage :
    pip install -r requirements.txt
    python download_corpus.py            # télécharge ce qui manque
    python download_corpus.py --verify   # vérifie les empreintes déjà enregistrées

IMPORTANT : une seule personne de l'équipe exécute le téléchargement, puis partage
le dossier data/ et le corpus.csv mis à jour avec les autres (en privé).
Les pages de l'OMS changent quand une fiche est mise à jour : deux téléchargements
faits séparément ne donnent pas toujours exactement le même fichier.
"""
import argparse
import csv
import datetime as dt
import hashlib
import pathlib
import sys
import time

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).parent
RAW = ROOT / "data" / "raw"
TEXT = ROOT / "data" / "text"
CSV_PATH = ROOT / "corpus.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (projet pedagogique, recherche documentaire)"}


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines = [ln.strip() for ln in main.get_text("\n").splitlines()]
    return "\n".join(ln for ln in lines if ln)


def read_rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def write_rows(rows, fields):
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    TEXT.mkdir(parents=True, exist_ok=True)
    rows, fields = read_rows()
    failed = []
    for row in rows:
        html_path = RAW / f"{row['doc_id']}.html"
        txt_path = TEXT / f"{row['doc_id']}.txt"
        if html_path.exists() and row["sha256"]:
            continue
        try:
            r = requests.get(row["url"], headers=HEADERS, timeout=30)
            r.raise_for_status()
        except requests.RequestException as exc:
            print(f"ÉCHEC  {row['doc_id']}: {exc}")
            failed.append(row["doc_id"])
            continue
        html_path.write_bytes(r.content)
        r.encoding = r.apparent_encoding if not r.encoding else r.encoding
        txt_path.write_text(extract_text(r.text), encoding="utf-8")
        row["date_telechargement"] = dt.date.today().isoformat()
        row["sha256"] = sha256(html_path)
        row["chemin_html"] = str(html_path.relative_to(ROOT))
        row["chemin_texte"] = str(txt_path.relative_to(ROOT))
        print(f"OK     {row['doc_id']}  ({len(r.content)//1024} Ko)")
        time.sleep(1)  # soyez poli avec le serveur
    write_rows(rows, fields)
    if failed:
        print("\nÀ vérifier (URL absente ou changée) :", ", ".join(failed))
        print("Corrigez l'URL dans corpus.csv puis relancez le script.")


def verify():
    rows, _ = read_rows()
    bad = 0
    for row in rows:
        p = ROOT / row["chemin_html"] if row["chemin_html"] else None
        if not p or not p.exists():
            print(f"MANQUANT  {row['doc_id']}")
            bad += 1
        elif sha256(p) != row["sha256"]:
            print(f"DIFFÉRENT {row['doc_id']}")
            bad += 1
    print("Tout est identique." if bad == 0 else f"{bad} fichier(s) à vérifier.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    verify() if args.verify else download()
