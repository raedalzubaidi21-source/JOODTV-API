import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

JSON_FILE_PATH = "JOOD-TV.json"
TARGET_CATEGORY_NAME = "بين سبورت روابط خارجيه"

# قائمة الروابط التي تريد جلب البث منها (ضع هنا روابط القنوات التي تعمل)
# مثال: إذا كان عندك بين سبورت 1،2،3،4
CHANNEL_URLS = [
    "https://pl.koralive1.cc/bein4/",  # أضف باقي الروابط هنا
    # "https://pl.koralive1.cc/bein1/",
    # "https://pl.koralive1.cc/bein2/",
]

async def extract_m3u8_from_page(page, url):
    """الدخول إلى صفحة القناة واستخراج رابط M3U8 من طلبات الشبكة"""
    try:
        print(f"   🌐 فتح: {url}")
        
        m3u8_url = None
        
        # تعريف دالة لمراقبة الطلبات (لتلتقط الـ M3U8)
        def handle_response(response):
            nonlocal m3u8_url
            # نبحث عن أي طلب يحتوي على .m3u8 أو .ts على نطاق R2
            if response.url and (".m3u8" in response.url or ".ts" in response.url):
                # نتأكد أن الطلب جاء من نفس النطاق الذي وجدناه سابقاً
                if "r2.dev" in response.url:
                    m3u8_url = response.url
                    print(f"      ✅ تم العثور على رابط البث: {m3u8_url[:80]}...")
        
        # ربط المراقب بالصفحة
        page.on("response", handle_response)
        
        # الانتقال إلى صفحة القناة
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        # انتظار تحميل المشغل (قد يظهر عبر JavaScript)
        try:
            # ننتظر ظهور أي عنصر فيديو أو إطار
            await page.wait_for_selector('video, iframe, .player, #player', timeout=15000)
        except:
            print("      ⏳ لم يظهر عنصر مشغل واضح، ننتظر قليلاً...")
        
        # الانتظار بضع ثوانٍ للسماح بتحميل روابط البث
        await asyncio.sleep(5)
        
        # محاولة إضافية: البحث في كود الصفحة عن رابط M3U8
        if not m3u8_url:
            content = await page.content()
            # البحث عن أي رابط يحتوي على r2.dev و .m3u8
            found = re.findall(r'https?://[^"\']+r2\.dev[^"\']+\.m3u8[^"\']*', content)
            if found:
                m3u8_url = found[0]
                print(f"      ✅ تم العثور على رابط في النص: {m3u8_url[:80]}...")
        
        # إزالة المراقب
        page.remove_listener("response", handle_response)
        
        return m3u8_url
        
    except Exception as e:
        print(f"      ❌ فشل في معالجة {url}: {e}")
        return None

async def main():
    print("🔄 جاري استخراج روابط M3U8 باستخدام المتصفح...")
    
    async with async_playwright() as p:
        # تشغيل المتصفح مع إعدادات المستخدم الحقيقي
        browser = await p.chromium.launch(headless=True)
        
        # إنشاء سياق متصفح يحاكي المستخدم الحقيقي
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        
        # إضافة رؤوس HTTP مخصصة (Referer مهم جداً)
        await context.set_extra_http_headers({
            "Referer": "https://pl.koralive1.cc/",
            "Accept-Language": "en-US,en;q=0.9",
        })
        
        page = await context.new_page()
        
        all_links = []
        
        # تجربة كل رابط قناة
        for channel_url in CHANNEL_URLS:
            m3u8 = await extract_m3u8_from_page(page, channel_url)
            if m3u8:
                all_links.append(m3u8)
            await asyncio.sleep(1)  # تأخير بسيط بين الصفحات
        
        await browser.close()
        
        # إزالة التكرارات
        final_links = list(dict.fromkeys(all_links))
        print(f"\n✅ تم استخراج {len(final_links)} رابط M3U8 فريد.")
        
        # تحديث ملف JSON
        if final_links:
            try:
                with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # البحث عن القسم المستهدف
                target = None
                for cat in data.get("categories", []):
                    if cat.get("name") == TARGET_CATEGORY_NAME:
                        target = cat
                        break
                
                if not target:
                    print(f"❌ القسم '{TARGET_CATEGORY_NAME}' غير موجود.")
                    return
                
                # جمع القنوات
                channels = []
                if "sub_categories" in target:
                    for sub in target["sub_categories"]:
                        channels.extend(sub.get("channels", []))
                elif "channels" in target:
                    channels = target.get("channels", [])
                
                if not channels:
                    print("❌ القسم فارغ. أضف قنوات يدوياً أولاً.")
                    return
                
                # توزيع الروابط
                from itertools import cycle
                pool = cycle(final_links)
                updated = 0
                for ch in channels:
                    ch["url"] = next(pool)
                    updated += 1
                
                data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ تم تحديث {updated} قناة.")
            except Exception as e:
                print(f"❌ فشل حفظ الملف: {e}")
        else:
            print("⚠️ لم يتم العثور على روابط. تأكد من أن الروابط تعمل وأن البث بدأ.")

if __name__ == "__main__":
    asyncio.run(main())
