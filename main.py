import os
import requests

# === Funkcja pomocnicza ===
def extract(text, start, end):
    try:
        if end:
            return text.split(start)[1].split(end)[0].strip()
        else:
            return text.split(start)[1].strip()
    except IndexError:
        return ""

# === 1. Wczytaj dane z ENV ===
TICKTICK_SESSION = os.environ["TICKTICK_SESSION"]
TICKTICK_DEVICE = os.environ["TICKTICK_DEVICE"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB = os.environ["NOTION_DATABASE_ID"]
PROJECT_ID = os.environ["TICKTICK_PROJECT_ID"]

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

# === 3. Przetwarzanie zadań ===
for task in tasks:
    tags = task.get("tags", [])
    if not any(tag in ["завершено", "анульовано"] for tag in tags):
        continue

    desc = task.get("description", "")
    title = task.get("title", "Без назви")
    due = task.get("dueDate", None)

    # Parsowanie opisu
    problem = extract(desc, "**Опис проблеми чи поломки:**", "**Контактна інформація:**")
    kontakt = extract(desc, "**Контакт:**", "- **Адреса:**")
    adres = extract(desc, "**Адреса:**", "**Фінанси:**")
    koszt = extract(desc, "**Кошт деталей:**", "- **Прихід:**")
    przychod = extract(desc, "**Прихід:**", "*Дата замовлення:*")
    data_zam = extract(desc, "*Дата замовлення:*", "")

    # === 4. Wyślij do Notion ===
    payload = {
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

    response = requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=payload)

    if response.status_code != 200:
        print(f"❌ Błąd Notion: {response.status_code} {response.text}")
    else:
        print(f"✅ Dodano: {title}")
