import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

SOURCE_URL = "https://www.livekora.vip/"
JSON_FILE_PATH = "JOOD-TV.json"
TARGET_CATEGORY_NAME = "بين سبورت روابط خارجيه"

async def extract_m3u8_links():
    """استخراج روابط M3U8 من الموقع باستخدام متصفح حقيقي"""
    async with async_playwright() as p:
        # تشغيل متصفح Chrome (بدون واجهة)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("🌐 جاري تحميل الصفحة الرئيسية...")
        await page.goto(SOURCE_URL, timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        # 1. استخراج جميع روابط المباريات (التي تحتوي على /match/)
        match_links = await page.eval_on_selector_all(
            'a[href*="/match/"]', 
            'els => els.map(el => el.href)'
        )
        
        # إزالة التكرارات
        match_links = list(dict.fromkeys(match_links))
        print(f"✅ تم العثور على {len(match_links)} مباراة.")
        
        all_m3u8_links = []
        
        # 2. الدخول إلى كل صفحة مباراة لاستخراج M3U8
        for idx, match_url in enumerate(match_links[:10], 1):  # حدد 10 مباريات فقط لتوفير الوقت
            try:
                print(f"   🔍 جاري فحص المباراة {idx}/{len(match_links[:10])}: {match_url}")
                await page.goto(match_url, timeout=60000)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)  # انتظار تحميل المشغل
                
                # البحث عن روابط M3U8 داخل الصفحة (في iframes أو في كود JavaScript)
                m3u8_found = []
                
                # محاولة استخراج من عناصر الفيديو أو المصادر
                sources = await page.eval_on_selector_all(
                    'video source, iframe[src*="m3u8"], [src*=".m3u8"]',
                    'els => els.map(el => el.src || el.getAttribute("src"))'
                )
                m3u8_found.extend([s for s in sources if s and (".m3u8" in s or ".ts" in s)])
                
                # محاولة استخراج من كود JavaScript (باستخدام Regex على محتوى الصفحة)
                page_content = await page.content()
                js_links = re.findall(r'https?://[^"\']+\.m3u8[^"\']*', page_content)
                m3u8_found.extend(js_links)
                
                # إزالة التكرارات
                m3u8_found = list(dict.fromkeys(m3u8_found))
                
                if m3u8_found:
                    print(f"      ✅ تم العثور على {len(m3u8_found)} رابط بث.")
                    all_m3u8_links.extend(m3u8_found)
                else:
                    print(f"      ⚠️ لم يتم العثور على رابط بث في هذه المباراة.")
                    
            except Exception as e:
                print(f"      ❌ فشل في معالجة المباراة: {e}")
        
        await browser.close()
        
        # إزالة التكرارات من القائمة النهائية
        final_links = list(dict.fromkeys(all_m3u8_links))
        print(f"\n✅ تم استخراج {len(final_links)} رابط M3U8 فريد.")
        return final_links

def update_json(file_path, new_links):
    """تحديث ملف JSON بروابط M3U8 الجديدة"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # البحث عن القسم المستهدف
        target_category = None
        for category in data.get("categories", []):
            if category.get("name") == TARGET_CATEGORY_NAME:
                target_category = category
                break
        
        if not target_category:
            print(f"❌ القسم '{TARGET_CATEGORY_NAME}' غير موجود.")
            return False
        
        # جمع جميع القنوات في هذا القسم
        all_channels = []
        if "sub_categories" in target_category:
            for sub in target_category["sub_categories"]:
                all_channels.extend(sub.get("channels", []))
        elif "channels" in target_category:
            all_channels = target_category.get("channels", [])
        
        if not all_channels:
            print("❌ لا توجد قنوات في هذا القسم.")
            return False
        
        # إذا لم توجد روابط جديدة، نحافظ على القديمة
        if not new_links:
            print("⚠️ لا توجد روابط M3U8 جديدة. تم الحفاظ على الروابط القديمة.")
            return True
        
        # توزيع الروابط الجديدة على القنوات (بشكل دائري)
        from itertools import cycle
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
        
        print(f"✅ تم تحديث {updated} قناة بروابط M3U8.")
        return True
        
    except Exception as e:
        print(f"❌ فشل تحديث الملف: {e}")
        return False

async def main():
    print("🔄 جاري استخراج روابط M3U8...")
    links = await extract_m3u8_links()
    if links:
        update_json(JSON_FILE_PATH, links)
    else:
        print("⚠️ لم يتم العثور على روابط M3U8.")

if __name__ == "__main__":
    asyncio.run(main())
