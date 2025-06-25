import os
import requests
import yaml
import json
from datetime import datetime
from pathlib import Path

API_URL = "https://zenodo.org/api/deposit/depositions"
ACCESS_TOKEN = os.getenv("ZENODO_TOKEN")

if not ACCESS_TOKEN:
    token_file = Path.home() / ".zenodo_token"
    if token_file.exists():
        ACCESS_TOKEN = token_file.read_text().strip()

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

YAML_DIR = Path.home() / "katiska-heritage/podcastit/yaml/kaffepaussin_aika"
PROCESSED_DIR = Path.home() / "katiska-heritage/podcastit/zenodo_meta"
TMP_AUDIO_DIR = Path("/tmp/katiska_audio")
TMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def upload_to_zenodo(yaml_file):
    with open(yaml_file, "r") as f:
        metadata = yaml.safe_load(f)

    # Luo tyhjä talletus
    r = requests.post(API_URL, headers=HEADERS, json={})
    deposition = r.json()
    deposition_id = deposition["id"]

    # Lataa MP3 Hetzneriltä
    mp3_url = metadata["audio_url"]
    mp3_filename = mp3_url.split("/")[-1]
    local_audio_path = TMP_AUDIO_DIR / mp3_filename

    audio_response = requests.get(mp3_url)
    with open(local_audio_path, "wb") as f:
        f.write(audio_response.content)

    # Liitä MP3 tiedosto talletukseen
    with open(local_audio_path, "rb") as fp:
        requests.post(
            f"{API_URL}/{deposition_id}/files",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            files={"file": (mp3_filename, fp)}
        )

    # Metadata-payload
    metadata_payload = {
        "metadata": {
            "upload_type": "audio",
            "publication_date": str(metadata["publication_date"]),
            "title": metadata["title"],
            "creators": [{"name": metadata["author"]}],
            "description": metadata["description"],
            "language": metadata.get("language", "und"),
            "license": metadata["license"],
            "keywords": metadata.get("keywords", []),
            "related_identifiers": [
                {
                    "identifier": metadata["source_url"],
                    "relation": "isDescribedBy"
                }
            ]
        }
    }

    r = requests.put(f"{API_URL}/{deposition_id}", headers=HEADERS, json=metadata_payload)
    if r.status_code != 200:
        print(f"⚠️ Metadata-lähetys epäonnistui tiedostolle {yaml_file.name}")
        print(f"↳ Zenodon vastaus: {r.status_code} {r.reason}")
        print(json.dumps(r.json(), indent=2))
        return

    doi = r.json()["metadata"]["prereserve_doi"]["doi"]
    print(f"✅ Talletus onnistui: {metadata['title']}")
    print(f"🔗 DOI: https://doi.org/{doi}")

    # Päivitä YAML tiedosto DOI:lla
    metadata["zenodo_doi"] = doi
    with open(yaml_file, "w") as f:
        yaml.safe_dump(metadata, f, sort_keys=False, allow_unicode=True)

    # Siirrä käsitelty tiedosto arkistohakemistoon
    destination = PROCESSED_DIR / yaml_file.name
    yaml_file.rename(destination)

if __name__ == "__main__":
    yaml_files = sorted(YAML_DIR.glob("*.md"))
    for file in yaml_files:
        upload_to_zenodo(file)
