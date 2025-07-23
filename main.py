import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# 🌍 Config des pays autorisés
pays_autorises = {
    "🇺🇸": "USD", "🇯🇵": "JPY", "🇪🇺": "EUR",
    "🇨🇦": "CAD", "🇬🇧": "GBP", "🇨🇭": "CHF",
    "🇦🇺": "AUD", "🇨🇳": "CNY"
}

# 🔄 Map inverse : devise → drapeau
devise_to_flag = {v: k for k, v in pays_autorises.items()}

# 📦 Load .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# 📊 Scraping
def get_filtered_sorted_events():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=fr")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://fr.investing.com/economic-calendar/")

    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        ).click()
    except:
        pass

    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.js-event-item"))
    )
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.js-event-item")
    events = []

    for row in rows:
        try:
            currency = row.find_element(By.CLASS_NAME, "left.flagCur.noWrap").text.strip()
            if currency not in devise_to_flag:
                continue
            heure = row.find_element(By.CLASS_NAME, "first.left.time").text.strip()
            event = row.find_element(By.CLASS_NAME, "event").text.strip()
            actuel = row.find_element(By.CLASS_NAME, "act").text.strip()
            prevu = row.find_element(By.CLASS_NAME, "fore").text.strip()
            precedent = row.find_element(By.CLASS_NAME, "prev").text.strip()
            events.append({
                "heure": heure,
                "devise": currency,
                "événement": event,
                "actuel": actuel,
                "prévu": prevu,
                "précédent": precedent
            })
        except:
            continue
    driver.quit()

    def safe_time_parse(h):
        try:
            return datetime.strptime(h, "%H:%M")
        except ValueError:
            return datetime.max

    return sorted(events, key=lambda x: safe_time_parse(x["heure"]))

# 🧾 Format propre
def format_events(events):
    today = datetime.now().strftime("%A %d %B %Y")
    lines = [f"📊 **Annonces économiques importantes du {today}**\n"]
    if not events:
        lines.append("❗ Aucune annonce importante trouvée aujourd’hui.")
    else:
        for e in events:
            flag = devise_to_flag.get(e["devise"], "")
            lines.append(
                f"🕐 {e['heure']} | {flag} {e['devise']}\n"
                f"📌 {e['événement']}\n"
                f"📊 Actuel: {e['actuel']} | Prévu: {e['prévu']} | Précédent: {e['précédent']}\n"
            )
    return "\n".join(lines)

# 📤 Split Discord 2000 char limit
def split_message(msg, max_len=2000):
    parts = []
    while len(msg) > max_len:
        split_idx = msg.rfind('\n', 0, max_len)
        if split_idx == -1:
            split_idx = max_len
        parts.append(msg[:split_idx])
        msg = msg[split_idx:].lstrip()
    parts.append(msg)
    return parts

# 🤖 Discord bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    try:
        events = get_filtered_sorted_events()
        msg = format_events(events)

        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(msg)

        channel = bot.get_channel(CHANNEL_ID)
        for part in split_message(msg):
            await channel.send(part)

        print("✅ Message envoyé sur Discord.")
    except Exception as e:
        print(f"❌ Erreur Discord : {e}")
    await bot.close()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
