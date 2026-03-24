"""
غرفة الحرب — محدِّث تلقائي كل ساعة
ينشر على GitHub Pages مباشرة — بدون Netlify
"""

import os
import requests
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TAVILY_API_KEY    = os.environ["TAVILY_API_KEY"]

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
            },
            timeout=20,
        )
        data = r.json()
        results = []
        if data.get("answer"):
            results.append(f"[ملخص]\n{data['answer']}")
        for item in data.get("results", []):
            results.append(f"• {item.get('title','')}\n  {item.get('content','')[:400]}")
        print(f"  ✅ {len(results)} نتيجة")
        return "\n\n".join(results)
    except Exception as e:
        print(f"  ⚠️ خطأ: {e}")
        return ""

def read_current_html():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return ""

def generate_updated_html(news, current_html):
    print("🤖 تحديث بـ Claude...")
    now_ar = datetime.utcnow().strftime("%H:%M UTC · %d/%m/%Y")
    prompt = f"""أنت محرر HTML متخصص. مهمتك تحديث النصوص والأرقام فقط في هذا الداشبورد.

الوقت الحالي: {now_ar}

=== آخر الأخبار ===
{news}

=== قواعد صارمة جداً ===
1. لا تغيّر CSS أبداً — لا تحذف ولا تضيف أي style
2. لا تغيّر هيكل HTML أبداً — لا تحذف ولا تضيف divs أو classes
3. فقط غيّر النصوص داخل العناصر الموجودة
4. فقط غيّر الأرقام (أسعار النفط، BTC، الذهب، S&P)
5. فقط غيّر التاريخ والوقت في الـ header إلى: {now_ar}
6. إذا كان هناك خبر عاجل — غيّر نص الـ Breaking Banner الموجود فقط
7. احتفظ بنفس الداشبورد حرفاً بحرف ما عدا النصوص والأرقام

=== الداشبورد الحالي ===
{current_html[:15000]}

أعطِ HTML الكامل فقط — بدون أي شرح.
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

def main():
    print(f"\n{'='*50}")
    print(f"⚔️  War Room — {datetime.utcnow().strftime('%H:%M UTC')}")
    print(f"{'='*50}\n")
    news         = fetch_news()
    current_html = read_current_html()
    new_html     = generate_updated_html(news, current_html)
    save_html(new_html)
    print("\n✅ اكتمل!\n")

if __name__ == "__main__":
    main()
