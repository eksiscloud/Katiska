#!/usr/bin/env python3
from pathlib import Path
import yaml
import json
import requests
import tempfile
import shutil
from datetime import date

API_URL = "https://zenodo.org/api/deposit/depositions"

# Lue token kotihakemistosta
with open(Path.home() / ".zenodo_token") as f:
    TOKEN = f.read().strip()

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
}

YAML_DIR = Path.home() / "katiska-heritage/podcastit/yaml/kaffepaussin_aika"
PROCESSED_DIR = Path.home() / "katiska-heritage/podcastit/zenodo_meta"

def upload_to_zenodo(file_path):
    print(f"\n📄 Käsitellään: {file_path.name}")

    with open(file_path, "r", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)

    audio_url = metadata.get("audio_url")
    if not audio_url:
        print("⚠️ audio_url puuttuu, ohitetaan...")
        return

    print(f"🎧 Ladataan audio {audio_url}...")
    tmp_dir = tempfile.mkdtemp()
    local_audio = Path(tmp_dir) / Path(audio_url).name
    try:
        r = requests.get(audio_url, stream=True)
        with open(local_audio, "wb") as f:
            shutil.copyfileobj(r.raw, f)
    except Exception as e:
        print(f"⚠️ Audion lataus epäonnistui: {e}")
        return

    print("📄 Luodaan uusi julkaisu...")
    r = requests.post(API_URL, headers=HEADERS, json={})
    if r.status_code != 201:
        print(f"⚠️ Julkaisun luonti epäonnistui: {r.status_code} {r.text}")
        return

    deposition = r.json()
    deposition_id = deposition["id"]

    print("📤 Ladataan audio Zenodoon...")
    files_url = f"{API_URL}/{deposition_id}/files"
    with open(local_audio, "rb") as fp:
        r = requests.post(files_url, headers={"Authorization": f"Bearer {TOKEN}"}, files={"file": fp})
    if r.status_code != 201:
        print(f"⚠️ Audion siirto epäonnistui: {r.status_code} {r.text}")
        return

    print("📝 Päivitetään metadata...")
    payload = {
        "metadata": {
            "title": metadata.get("title"),
            "upload_type": "video",
            "publication_date": metadata["publication_date"].isoformat() if isinstance(metadata["publication_date"], date) else metadata["publication_date"],
            "description": metadata.get("description"),
            "creators": [{"name": metadata.get("author", "Jakke Lehtonen")}],
            "language": metadata.get("language", "fi"),
            "license": metadata.get("license", "cc-by-nc-sa-4.0"),
            "keywords": metadata.get("keywords", []),
            "resource_type": "video",
            "communities": [{"identifier": "katiska"}],
        }
    }

    r = requests.put(f"{API_URL}/{deposition_id}", headers=HEADERS, json=payload)
    if r.status_code != 200:
        print(f"⚠️ Metadata-lähetys epäonnistui tiedostolle {file_path.name}")
        print(f"↳ Zenodon vastaus: {r.status_code} {r.text}")
        return

    print("🚀 Julkaistaan...")
    r = requests.post(f"{API_URL}/{deposition_id}/actions/publish", headers=HEADERS)
    if r.status_code != 202:
        print(f"⚠️ Julkaisu epäonnistui tiedostolle {file_path.name}")
        print(f"↳ Zenodon vastaus: {r.status_code} {r.text}")
        return

    final_doi = r.json().get("doi")
    if final_doi:
        metadata["zenodo_doi"] = final_doi
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, allow_unicode=True)
        print(f"✅ DOI lisätty YAML-tiedostoon: {final_doi}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file_path), str(PROCESSED_DIR / file_path.name))
    print(f"📦 Siirretty kansioon: {PROCESSED_DIR}")

    shutil.rmtree(tmp_dir)

for file in YAML_DIR.glob("*.md"):
    upload_to_zenodo(file)
