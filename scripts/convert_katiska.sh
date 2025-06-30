#!/bin/bash

# NVM täytynee olla käytössä, kunnes aptin versio joskus pävittyy
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Asetukset
EXPORT_DIR="/root/wordpress-export-to-markdown/katiska_export"
STATE_FILE="$EXPORT_DIR/.last_export_date"
TODAY=$(date +%Y-%m-%d)

# Tarkista, onko tilatiedosto olemassa
if [ -f "$STATE_FILE" ]; then
    START_DATE=$(cat "$STATE_FILE")
else
    echo "❗ Ensimmäinen ajo, käytetään oletuspäivää 1993-01-01"
    START_DATE="1993-01-01"
fi

# Luo vientihakemisto, jos ei ole olemassa
mkdir -p "$EXPORT_DIR"

# Aja vienti
echo "📦 Viedään artikkelit ajalta $START_DATE → $TODAY..."
wp --allow-root --path=/var/www/backend/html export --post_type=post \
          --dir="$EXPORT_DIR" \
          --start_date="$START_DATE" \
          --end_date="$TODAY"

# Etsitään uudet WXR/XML-tiedostot
echo "🔍 Haetaan WXR-tiedostot konversiota varten..."
cd "$EXPORT_DIR" || exit 1
FILES=$(find . -maxdepth 1 -type f -name "*.xml")

if [ -z "$FILES" ]; then
    echo "🚫 Ei uusia XML-tiedostoja löydetty."
else
    for file in $FILES; do
        echo "📝 Muunnetaan $file Markdown-muotoon..."
        nvm use 20 >/dev/null
        npx wordpress-export-to-markdown --input "$file" --output ./markdown 
    done
fi

echo "🧹 Poistetaan kaikki XML-tiedostot..."
rm -f $EXPORT_DIR/*.xml

# Päivitä tilatiedosto
echo "$TODAY" > "$STATE_FILE"
echo "✅ Vienti ja muunnos valmis. Päivitetty uusi lähtöpäivä: $TODAY"
