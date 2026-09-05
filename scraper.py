import requests
import re
import json
from datetime import datetime
from itertools import cycle

SOURCE_URL = "https://www.livekora.vip/"
JSON_FILE_PATH = "JOOD-TV.json"
LINK_PATTERN = r'https?://(?:www\.)?(?:binsport|bsport)\.[^"\'/\s]+/[^"\'/\s]+'

# ✅ تم تعديل اسم القسم هنا ليطابق ما في ملفك بالضبط
TARGET_CATEGORY_NAME = "بين سبورت روابط خارجيه"  

def get_binsport_links():
    try:
        response = requests.get(SOURCE_URL, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        links = re.findall(LINK_PATTERN, response.text)
        unique_links = list(dict.fromkeys(links))
        print(f"✅ تم جلب {len(unique_links)} رابطاً من بين سبورت.")
        return unique_links
    except Exception as e:
        print(f"❌ فشل جلب الروابط: {e}")
        return []

def update_urls_only(file_path, new_links):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        target_category = None
        for category in data.get("categories", []):
            if category.get("name") == TARGET_CATEGORY_NAME:
                target_category = category
                break

        if not target_category:
            print(f"⚠️ القسم '{TARGET_CATEGORY_NAME}' غير موجود في الملف.")
            print("📌 تحقق من اسم القسم في ملف JSON واضبطه في السكربت.")
            return False

        all_channels = []
        if "sub_categories" in target_category:
            for sub in target_category["sub_categories"]:
                all_channels.extend(sub.get("channels", []))
        elif "channels" in target_category:
            all_channels = target_category.get("channels", [])

        if not all_channels:
            print(f"⚠️ لا توجد قنوات في القسم '{TARGET_CATEGORY_NAME}'.")
            return False

        print(f"📊 عدد القنوات الموجودة: {len(all_channels)}")

        if not new_links:
            print("⚠️ لا توجد روابط جديدة متاحة. تم إلغاء التحديث لحماية الروابط القديمة.")
            return True

        link_pool = cycle(new_links)
        updated = 0
        for channel in all_channels:
            try:
                channel["url"] = next(link_pool)
                updated += 1
            except StopIteration:
                break

        data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ تم تحديث {updated} قناة في قسم '{TARGET_CATEGORY_NAME}'.")
        return True

    except Exception as e:
        print(f"❌ فشل التحديث: {e}")
        return False

if __name__ == "__main__":
    print("🔄 جاري تحديث روابط بين سبورت...")
    links = get_binsport_links()
    update_urls_only(JSON_FILE_PATH, links)
