"""
غرفة الحرب — محدِّث تلقائي كل ساعة
"""

import os
import hashlib
import requests
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TAVILY_API_KEY    = os.environ["TAVILY_API_KEY"]
NETLIFY_SITE_ID   = os.environ["NETLIFY_SITE_ID"]
NETLIFY_TOKEN     = os.environ["NETLIFY_TOKEN"]

SEARCH_QUERY = (
    "Iran US war latest update ceasefire deal negotiations "
    "oil prices Bitcoin S&P markets Hormuz today"
)

def fetch_news():
    print("🔍 جلب الأخبار...")
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": SEARCH_QUERY,
                "search_depth": "advanced",
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
        print(f"  ⚠️ خطأ: {e}")
        return ""

def read_current_html():
    path = "index.html"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def generate_updated_html(news, current_html):
    print("🤖 تحديث بـ Claude...")
    now_ar = datetime.utcnow().strftime("%H:%M UTC · %d/%m/%Y")
    prompt = f"""أنت محرر داشبورد "غرفة الحرب" — لوحة استخبارات الحرب الإيرانية الأمريكية.

الوقت الحالي: {now_ar}

=== آخر الأخبار ===
{news}

=== الداشبورد الحالي ===
{current_html[:15000]}

مهمتك:
1. حدِّث الأخبار والأرقام بناءً على آخر المستجدات
2. حدِّث التوقيت في الـ header: {now_ar}
3. إذا كان هناك خبر عاجل = أضف Breaking Banner أحمر في الأعلى
4. حدِّث أسعار الأسواق (BTC، نفط، ذهب، S&P) بالأرقام الجديدة
5. حافظ على نفس CSS والتصميم تماماً
6. حدِّث العد التنازلي بشكل صحيح

أعطِ HTML الكامل فقط — بدون أي شرح أو markdown.
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
        if html.startswith("```"):
            html = html.split("```", 2)[1]
            if html.startswith("html"):
                html = html[4:]
        if html.endswith("```"):
            html = html[:-3]
        return html.strip()
    else:
        print(f"  ❌ خطأ Claude: {data}")
        return current_html

def save_html(html):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("💾 تم حفظ index.html")

def deploy_to_netlify():
    print("🚀 رفع على Netlify...")
    try:
        with open("index.html", "rb") as f:
            file_bytes = f.read()
        sha1 = hashlib.sha1(file_bytes).hexdigest()
        headers = {
            "Authorization": f"Bearer {NETLIFY_TOKEN}",
            "Content-Type": "application/json",
        }
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
            print(f"  رفع الملف: {r2.status_code}")
        print(f"  ✅ نُشر! Deploy ID: {deploy_id}")
    except Exception as e:
        print(f"  ❌ خطأ: {e}")

def main():
    print(f"\n{'='*50}")
    print(f"⚔️  War Room — {datetime.utcnow().strftime('%H:%M UTC')}")
    print(f"{'='*50}\n")
    news         = fetch_news()
    current_html = read_current_html()
    new_html     = generate_updated_html(news, current_html)
    save_html(new_html)
    deploy_to_netlify()
    print("\n✅ اكتمل!\n")

if __name__ == "__main__":
    main()
