import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HOST = "servx.pro"
PORT = "80"
USER = "00971552007976"
PASS = "mkX2G5"
BASE = f"http://{HOST}:{PORT}"

MAX_WORKERS = 20  # عدد المسلسلات اللي تُجلب بنفس الوقت

def api(action, extra=""):
    url = f"{BASE}/player_api.php?username={USER}&password={PASS}&action={action}{extra}"
    try:
        r = requests.get(url, timeout=60)
        return r.json()
    except:
        return []

def fetch_series_info(s):
    """يجلب معلومات مسلسل واحد ويرجع القنوات جاهزة"""
    try:
        info = api("get_series_info", f"&series_id={s['series_id']}")
        if not isinstance(info, dict) or "episodes" not in info:
            return None

        channels = []
        order = 0
        seasons = info["episodes"]
        try:
            season_keys = sorted(seasons.keys(), key=lambda x: int(x))
        except:
            season_keys = list(seasons.keys())

        for sn in season_keys:
            eps = seasons[sn]
            try:
                eps = sorted(eps, key=lambda e: int(e.get("episode_num", 0)))
            except:
                pass
            for ep in eps:
                ext = ep.get("container_extension") or "mp4"
                img = ""
                if isinstance(ep.get("info"), dict):
                    img = ep["info"].get("movie_image", "") or ""
                channels.append({
                    "channel_name": f"م{sn} ح{ep.get('episode_num','')}",
                    "url": f"{BASE}/series/{USER}/{PASS}/{ep['id']}.{ext}",
                    "logo_url": img,
                    "drm_id": "",
                    "drm_key": "",
                    "user_agent": "",
                    "referer": "",
                    "order": order
                })
                order += 1

        if not channels:
            return None

        return {
            "sub_category_name": s.get("name", ""),
            "sub_category_logo": s.get("cover", "") or "",
            "channels": channels
        }
    except Exception as e:
        print(f"خطأ في {s.get('name','')}: {e}")
        return None

def build():
    with open("JOOD-TV.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    data["categories"] = [c for c in data["categories"]
                          if c.get("category_name") not in ("أفلام", "مسلسلات")]

    # ========== الأفلام ==========
    print("جلب الأفلام...")
    movies = api("get_vod_streams")
    vod_cats = api("get_vod_categories")
    cat_names = {c["category_id"]: c["category_name"] for c in vod_cats}

    movies_by_cat = {}
    for m in movies:
        cid = str(m.get("category_id", "0"))
        movies_by_cat.setdefault(cid, []).append(m)

    movie_subs = []
    for cid, mlist in movies_by_cat.items():
        channels = []
        for i, m in enumerate(mlist):
            ext = m.get("container_extension") or "mkv"
            channels.append({
                "channel_name": m.get("name", ""),
                "url": f"{BASE}/movie/{USER}/{PASS}/{m['stream_id']}.{ext}",
                "logo_url": m.get("stream_icon", "") or "",
                "drm_id": "",
                "drm_key": "",
                "user_agent": "",
                "referer": "",
                "order": i
            })
        movie_subs.append({
            "sub_category_name": cat_names.get(cid, "أفلام"),
            "sub_category_logo": "",
            "channels": channels
        })

    data["categories"].append({
        "category_name": "أفلام",
        "category_logo": "",
        "sub_categories": movie_subs,
        "image": ""
    })

    # ========== المسلسلات (متوازي) ==========
    print("جلب المسلسلات...")
    series = api("get_series")
    total = len(series)
    print(f"عدد المسلسلات: {total}")

    series_subs = []
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_series_info, s): s for s in series}
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                series_subs.append(result)
            if done % 100 == 0:
                print(f"اكتمل {done}/{total}")

    # ترتيب حسب الاسم
    series_subs.sort(key=lambda x: x.get("sub_category_name", ""))

    data["categories"].append({
        "category_name": "مسلسلات",
        "category_logo": "",
        "sub_categories": series_subs,
        "image": ""
    })

    with open("JOOD-TV.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("تم الحفظ")

if __name__ == "__main__":
    build()
