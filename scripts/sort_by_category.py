import os
import shutil
import yaml

INPUT_DIR = "/root/wordpress-export-to-markdown/katiska_export/markdown/posts"
OUTPUT_DIR = "/root/wordpress-export-to-markdown/katiska_export/markdown/categorized"

# Luodaan ulostulokansio, jos sitä ei ole
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Käydään kaikki tiedostot läpi
for filename in os.listdir(INPUT_DIR):
    if not filename.endswith(".md"):
        continue

    filepath = os.path.join(INPUT_DIR, filename)

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if lines[0].strip() != "---":
        print(f"⚠️ Ei front matteria: {filename}")
        continue

    # Poimi front matter
    end_idx = lines[1:].index("---\n") + 1
    yaml_content = "".join(lines[1:end_idx])
    try:
        front = yaml.safe_load(yaml_content)
    except Exception as e:
        print(f"❌ YAML-virhe {filename}: {e}")
        continue

    categories = front.get("categories", [])
    if not categories:
        category = "Uncategorized"
    else:
        category = categories[0].strip().replace(" ", "_")

    dest_dir = os.path.join(OUTPUT_DIR, category)
    os.makedirs(dest_dir, exist_ok=True)

    shutil.copy(filepath, os.path.join(dest_dir, filename))
    print(f"✅ {filename} → {category}/")

print("\n🟢 Valmis. Tiedostot on järjestetty kansioon 'categorized/'.")
