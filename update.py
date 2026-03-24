"""
غرفة الحرب — محدِّث تلقائي كل ساعة
War Room Auto-Updater — runs every hour via GitHub Actions
بحث واحد/تشغيل = 24 بحث/يوم × 30 = 720 بحث/شهر (ضمن الـ 1,000 مجاني)
"""

import os
import json
import hashlib
import requests
from datetime import datetime

# ── الإعدادات ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TAVILY_API_KEY    = os.environ["TAVILY_API_KEY"]
NETLIFY_SITE_ID   = os.environ["NETLIFY_SITE_ID"]
NETLIFY_TOKEN     = os.environ["NETLIFY_TOKEN"]

# بحث واحد شامل بدل عدة بحوث — يوفر الحصة المجانية
SEARCH_QUERY = (
    "Iran US war latest update ceasefire deal negotiations "
    "oil prices Bitcoin S&P markets Hormuz today"
)

# ── 1. جلب الأخبار من Tavily (بحث واحد فقط) ─────────────────────────────
def fetch_news():
    print("🔍 جلب الأخبار (بحث واحد — خطة مجانية)...")
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": SEARCH_QUERY,
                "search_depth": "advanced",  # advanced يعوّض قلة عدد البحوث
                "max_results": 8,
                "include_answer": True,
                "include_raw_content": False,
            },
            timeout=20,
        )
        data = r.json()
        results = []
        if data.get("answer"):
            results.append(f"[ملخص]\n{data['answer']}")
        for item in data.get("results", []):
            results.append(
                f"• {item.get('title','')}\n  {item.get('content','')[:400]}"
            )
        print(f"  ✅ {len(results)} نتيجة")
        return "\n\n".join(results)
    except Exception as e:
        print(f"  ⚠️ خطأ في البحث: {e}")
        return ""

# ── 2. قراءة آخر HTML ─────────────────────────────────────────────────────
def read_current_html():
    path = "index.html"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# ── 3. توليد HTML محدَّث بـ Claude ────────────────────────────────────────
def generate_updated_html(news: str, current_html: str) -> str:
    print("🤖 تحديث الداشبورد بـ Claude...")

    now_ar = datetime.utcnow().strftime("%H:%M UTC · %d/%m/%Y")

    prompt = f"""أنت محرر داشبورد "غرفة الحرب" — لوحة استخبارات الحرب الإيرانية الأمريكية.

الوقت الحالي: {now_ar}

=== آخر الأخبار (من Tavily) ===
{news}

=== الداشبورد الحالي (HTML كامل) ===
{current_html[:15000]}

مهمتك:
1. حدِّث الأخبار والأرقام في الداشبورد بناءً على آخر المستجدات أعلاه
2. حدِّث التوقيت في الـ header ليعكس الوقت الحالي: {now_ar}
3. إذا كان هناك خبر عاجل جديد = أضف Breaking Banner أحمر في الأعلى
4. حدِّث أسعار الأسواق (BTC، نفط، ذهب، S&P) بالأرقام الجديدة إذا وجدت
5. حافظ على نفس CSS والتصميم تماماً — فقط حدِّث المحتوى النصي والأرقام
6. حدِّث العد التنازلي (أيام متبقية) بشكل صحيح

أعطِ HTML الكامل المحدَّث فقط — بدون أي شرح أو markdown code blocks.
ابدأ مباشرة بـ <!DOCTYPE html>"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    data = r.json()
    if "content" in data and data["content"]:
        html = data["content"][0]["text"].strip()
        # إزالة code fences لو وُجدت
        if html.startswith("```"):
            html = html.split("```", 2)[1]
            if html.startswith("html"):
                html = html[4:]
        if html.endswith("```"):
            html = html[:-3]
        return html.strip()
    else:
        print(f"  ❌ خطأ من Claude: {data}")
        return current_html  # أبقِ الداشبورد القديم لو فشل

# ── 4. حفظ الملف ─────────────────────────────────────────────────────────
def save_html(html: str):
    os.makedirs("docs", exist_ok=True)
   with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("💾 تم حفظ الملف في docs/index.html")

# ── 5. نشر على Netlify ────────────────────────────────────────────────────
def deploy_to_netlify():
    print("🚀 رفع على Netlify...")
    try:
        with open("docs/index.html", "rb") as f:
            file_bytes = f.read()

        sha1 = hashlib.sha1(file_bytes).hexdigest()

        headers = {
            "Authorization": f"Bearer {NETLIFY_TOKEN}",
            "Content-Type": "application/json",
        }

        # خطوة 1: أنشئ deploy
        r = requests.post(
            f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys",
            headers=headers,
            json={"files": {"/index.html": sha1}},
            timeout=30,
        )
        deploy = r.json()
        deploy_id = deploy.get("id")
        required  = deploy.get("required", [])

        if not deploy_id:
            print(f"  ❌ خطأ Netlify: {deploy}")
            return

        # خطوة 2: رفع الملف إذا مطلوب
        if sha1 in required:
            r2 = requests.put(
                f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/index.html",
                headers={
                    "Authorization": f"Bearer {NETLIFY_TOKEN}",
                    "Content-Type": "text/html",
                },
                data=file_bytes,
                timeout=60,
            )
            if r2.status_code not in (200, 201, 204):
                print(f"  ⚠️ رفع الملف: {r2.status_code}")

        print(f"  ✅ نُشر بنجاح! Deploy ID: {deploy_id}")

    except Exception as e:
        print(f"  ❌ خطأ في النشر: {e}")

# ── الرئيسي ────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"⚔️  War Room Updater — {datetime.utcnow().strftime('%H:%M UTC')}")
    print(f"📊  كل ساعة = 24 بحث/يوم × 30 = 720 بحث/شهر")
    print(f"{'='*50}\n")

    news         = fetch_news()
    current_html = read_current_html()
    new_html     = generate_updated_html(news, current_html)
    save_html(new_html)
    deploy_to_netlify()

    print("\n✅ اكتمل التحديث!\n")

if __name__ == "__main__":
    main()
