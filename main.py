import json
import requests

# === Funkcja pomocnicza do wycinania tekstu między znacznikami ===
def extract(text, start, end):
    try:
        if end:
            return text.split(start)[1].split(end)[0].strip()
        else:
            return text.split(start)[1].strip()
    except IndexError:
        return ""

# === 1. Wczytaj konfigurację z config.json ===
with open("config.json") as f:
    config = json.load(f)

TICKTICK_SESSION = config["ticktick_session"]
TICKTICK_DEVICE = config["ticktick_device"]
NOTION_TOKEN = config["notion_token"]
NOTION_DB = config["notion_database_id"]
PROJECT_ID = config["ticktick_project_id"]

# === 2. Pobierz zadania z TickTick ===
headers = {
    "Cookie": f"t={TICKTICK_SESSION}; deviceId={TICKTICK_DEVICE}",
    "User-Agent": "Mozilla/5.0"
}
url = f"https://api.ticktick.com/api/v2/task?project={PROJECT_ID}&status=all"
res = requests.get(url, headers=headers)

if res.status_code != 200:
    print(f"❌ Błąd TickTick: {res.status_code}")
    exit()

tasks = res.json()

# === 3. Filtrowanie i przetwarzanie zadań ===
for task in tasks:
    tags = task.get("tags", [])
    if not any(tag in ["завершено", "анульовано"] for tag in tags):
        continue  # pomijamy jeśli nie pasuje tag

    desc = task.get("description", "")
    title = task.get("title", "Без назви")
    due = task.get("dueDate", None)

    # Parsowanie danych z pola description
    problem = extract(desc, "**Опис проблеми чи поломки:**", "**Контактна інформація:**")
    kontakt = extract(desc, "**Контакт:**", "- **Адреса:**")
    adres = extract(desc, "**Адреса:**", "**Фінанси:**")
    koszt = extract(desc, "**Кошт деталей:**", "- **Прихід:**")
    przychod = extract(desc, "**Прихід:**", "*Дата замовлення:*")
    data_zam = extract(desc, "*Дата замовлення:*", "")

    # === 4. Tworzenie wpisu w Notion ===
    notion_payload = {
        "parent": { "database_id": NOTION_DB },
        "properties": {
            "Тип, виробник і модель": {"title": [{"text": {"content": title}}]},
            "Крайній візит": {"date": {"start": due}} if due else {},
            "Опис проблеми чи поломки": {"rich_text": [{"text": {"content": problem}}]},
            "Контакт": {"rich_text": [{"text": {"content": kontakt}}]},
            "Адреса": {"rich_text": [{"text": {"content": adres}}]},
            "Кошт деталей": {"rich_text": [{"text": {"content": koszt}}]},
            "Прихід": {"rich_text": [{"text": {"content": przychod}}]},
            "Дата замовлення": {"rich_text": [{"text": {"content": data_zam}}]},
            "Статус": {"multi_select": [{"name": tag} for tag in tags if tag in ["завершено", "анульовано"]]},
            "Походження замовлення": {"multi_select": [{"name": tag} for tag in tags if tag in ["reper24", "телефон"]]}
        }
    }

    notion_headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    notion_res = requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=notion_payload)

    if notion_res.status_code != 200:
        print(f"❌ Błąd Notion ({notion_res.status_code}): {notion_res.text}")
    else:
        print(f"✅ Dodano do Notion: {title}")
