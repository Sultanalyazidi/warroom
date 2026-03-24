"""
غرفة الحرب — محدِّث تلقائي كل ساعة
يحافظ على التصميم الأصلي ويحدث المحتوى فقط
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

def read_template():
    # يقرأ الـ template الأصلي دائماً
    if os.path.exists("template.html"):
        with open("template.html", "r", encoding="utf-8") as f:
            return f.read()
    elif os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return ""

def generate_updated_html(news, template):
    print("🤖 تحديث بـ Claude...")
    now_ar = datetime.utcnow().strftime("%H:%M UTC · %d/%m/%Y")

    prompt = f"""أنت محرر HTML متخصص. لديك داشبورد HTML ومهمتك تحديث النصوص والأرقام فقط.

الوقت الحالي: {now_ar}

=== آخر الأخبار ===
{news}

=== قواعد صارمة جداً — يجب اتباعها حرفياً ===
1. احتفظ بكل CSS كما هو — لا تحذف ولا تضيف أي style أو class
2. احتفظ بنفس هيكل HTML تماماً — نفس الـ divs ونفس الـ classes
3. غيّر فقط النصوص داخل العناصر الموجودة بناءً على الأخبار الجديدة
4. غيّر التاريخ والوقت في الـ header إلى: {now_ar}
5. غيّر أسعار الأسواق (BTC، نفط، ذهب، S&P) بالأرقام الجديدة إذا وجدت في الأخبار
6. إذا كان هناك خبر عاجل — غيّر نص الـ Breaking Banner الموجود فقط
7. لا تُنشئ sections جديدة أو تحذف sections موجودة
8. الناتج يجب أن يبدأ بـ <!DOCTYPE html> وينتهي بـ </html>

=== الداشبورد (لا تغير هيكله) ===
{template[:15000]}

أعطِ HTML الكامل فقط بدون أي شرح."""

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
        return template

def save_html(html):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("💾 تم حفظ index.html")

def main():
    print(f"\n{'='*50}")
    print(f"⚔️  War Room — {datetime.utcnow().strftime('%H:%M UTC')}")
    print(f"{'='*50}\n")
    news     = fetch_news()
    template = read_template()
    new_html = generate_updated_html(news, template)
    save_html(new_html)
    print("\n✅ اكتمل!\n")

if __name__ == "__main__":
    main()
