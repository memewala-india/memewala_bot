import aiohttp
import os
import json
import random

CACHE_FILE = "templates_cache.json"
TEMPLATES_DIR = "templates"

CURATED_IDS = [
    "181913649",
    "87743020",
    "112126428",
    "247375501",
    "131087935",
    "222403160",
    "217743513",
    "97984",
    "61579",
    "102156234",
    "155067746",
    "124822590",
    "61520",
    "61544",
    "100777631",
    "93895088",
    "180190441",
    "91538330",
    "129242436",
    "123999232",
    "119139145",
    "252600596",
    "163573",
    "110163934",
    "259237855",
]


async def fetch_templates():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
            if cached:
                print(f"✅ Загружено из кэша: {len(cached)} шаблонов")
                return cached
    
    result = []
    local_files = [
        f for f in os.listdir(TEMPLATES_DIR)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
    
    if local_files:
        print(f"📂 Найдены локальные файлы: {len(local_files)}")
        for filename in local_files:
            file_path = os.path.join(TEMPLATES_DIR, filename)
            name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
            result.append({
                "id": os.path.splitext(filename)[0],
                "name": name,
                "file_path": file_path,
                "width": 800,
                "height": 800,
            })
    
    print("📥 Загрузка шаблонов из Imgflip...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.imgflip.com/get_memes") as resp:
            data = await resp.json()
    
    memes_by_id = {m["id"]: m for m in data["data"]["memes"]}
    existing_ids = {t["id"] for t in result}
    
    async with aiohttp.ClientSession() as session:
        for meme_id in CURATED_IDS:
            if meme_id in existing_ids:
                continue
            
            meme = memes_by_id.get(meme_id)
            if not meme:
                continue
            
            file_path = f"{TEMPLATES_DIR}/{meme_id}.jpg"
            
            if not os.path.exists(file_path):
                try:
                    async with session.get(meme["url"]) as img_resp:
                        if img_resp.status == 200:
                            content = await img_resp.read()
                            with open(file_path, "wb") as f:
                                f.write(content)
                except Exception as e:
                    print(f"  ❌ {meme['name']}: {e}")
                    continue
            
            result.append({
                "id": meme_id,
                "name": meme["name"],
                "file_path": file_path,
                "width": meme["width"],
                "height": meme["height"],
            })
            print(f"  ✅ {meme['name']}")
    
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Всего шаблонов: {len(result)}")
    return result


def get_random_template(templates):
    return random.choice(templates) if templates else None