import requests
import re
import json
from datetime import datetime
from itertools import cycle

# ================= الإعدادات =================
SOURCE_URL = "https://www.livekora.vip/"
JSON_FILE_PATH = "JOOD-TV.json"  

# يستهدف روابط بين سبورت بكل نطاقاتها (binsport, bsport)
LINK_PATTERN = r'https?://(?:www\.)?(?:binsport|bsport)\.[^"\'/\s]+/[^"\'/\s]+'

# اسم القسم المستهدف كما هو مكتوب في ملف JSON (تأكد من تطابقه)
TARGET_CATEGORY_NAME = "بين سبورت"  
# ============================================

def get_external_links():
    """جلب روابط بين سبورت من الصفحة الرئيسية"""
    try:
        response = requests.get(SOURCE_URL, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        # استخراج جميع الروابط التي تحتوي على binsport أو bsport
        links = re.findall(LINK_PATTERN, response.text)
        # حذف التكرارات مع الحفاظ على الترتيب
        unique_links = list(dict.fromkeys(links))
        
        print(f"✅ تم جلب {len(unique_links)} رابطاً من بين سبورت.")
        return unique_links
    except Exception as e:
        print(f"❌ فشل جلب الروابط: {e}")
        return None

def update_json(file_path, new_links):
    """تحديث ملف JSON مع الاحتفاظ بالروابط القديمة في حال عدم وجود روابط جديدة"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # البحث عن التصنيف المطلوب
        target_category = None
        for category in data.get("categories", []):
            if category.get("name") == TARGET_CATEGORY_NAME:
                target_category = category
                break

        if not target_category:
            print(f"⚠️ لم يتم العثور على تصنيف '{TARGET_CATEGORY_NAME}'")
            return False

        # إذا لم يتم جلب روابط جديدة، نخرج دون تعديل (نحمي الملف من التفرغ)
        if not new_links:
            print("⚠️ لا توجد روابط جديدة متاحة. تم إلغاء التحديث لحماية الروابط القديمة.")
            return True

        # تجهيز توزيع الروابط على القنوات
        link_pool = cycle(new_links)
        total_updated = 0

        # التحديث فقط للقنوات الموجودة تحت هذا التصنيف
        if "sub_categories" in target_category:
            for sub in target_category["sub_categories"]:
                for channel in sub.get("channels", []):
                    try:
                        channel["url"] = next(link_pool)
                        total_updated += 1
                    except StopIteration:
                        break
        elif "channels" in target_category:
            for channel in target_category["channels"]:
                try:
                    channel["url"] = next(link_pool)
                    total_updated += 1
                except StopIteration:
                    break

        # تسجيل وقت آخر تحديث
        data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # حفظ الملف
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ تم تحديث {total_updated} قناة في قسم '{TARGET_CATEGORY_NAME}' بنجاح!")
        return True

    except Exception as e:
        print(f"❌ فشل تحديث الملف: {e}")
        return False

# ================= التشغيل =================
if __name__ == "__main__":
    print("🔄 جاري التحديث التلقائي لقسم بين سبورت...")
    links = get_external_links()
    update_json(JSON_FILE_PATH, links)
