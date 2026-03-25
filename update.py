"""
غرفة الحرب — محدِّث تلقائي كل ساعة
المرحلة 1: تحديث الأرقام والوقت بـ regex (لا يمس التصميم)
المرحلة 2: Claude يضيف أقساماً جديدة فقط عند الضرورة القصوى
"""

import os
import re
import json
import requests
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TAVILY_API_KEY    = os.environ["TAVILY_API_KEY"]

# ── جلب الأخبار ────────────────────────────────────────────────────────────
def fetch_data():
    print("🔍 جلب الأخبار والأسواق...")
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": "Iran war ceasefire Bitcoin BTC price oil gold S&P today latest",
                "search_depth": "advanced",
                "max_results": 8,
                "include_answer": True,
            },
            timeout=20,
        )
        data = r.json()
        results = []
        if data.get("answer"):
            results.append(data["answer"])
        for item in data.get("results", [])[:5]:
            results.append(f"• {item.get('title','')}: {item.get('content','')[:300]}")
        print(f"  ✅ {len(results)} نتيجة")
        return "\n\n".join(results)
    except Exception as e:
        print(f"  ⚠️ خطأ: {e}")
        return ""

# ── Claude يستخرج البيانات ─────────────────────────────────────────────────
def extract_data(raw_news):
    print("🤖 استخراج البيانات...")
    now = datetime.utcnow().strftime("%H:%M UTC · %d/%m/%Y")

    prompt = f"""من الأخبار أدناه، استخرج البيانات وأعطني JSON فقط بدون أي نص آخر:

الأخبار:
{raw_news}

الوقت الحالي: {now}

JSON المطلوب (التزم بهذا الشكل حرفياً):
{{
  "time": "{now}",
  "btc_price": "مثال: $71,240",
  "btc_change": "مثال: +3.74%",
  "brent": "مثال: ~$99",
  "wti": "مثال: ~$88",
  "gold": "مثال: $4,352",
  "sp500": "مثال: 6,603",
  "sp500_change": "مثال: +1.2%",
  "breaking_news": "أهم خبر عاجل بجملة واحدة بالعربي — أو null إذا لا يوجد",
  "new_section_needed": false,
  "new_section_html": null
}}

new_section_needed = true فقط إذا حدث تطور دراماتيكي جديد كلياً (مثل: إعلان وقف إطلاق نار، ضربة نووية، صفقة رسمية).
إذا new_section_needed = true، ضع في new_section_html قسم HTML كامل بنفس classes الداشبورد (card, snap, sn, st2).
في الغالب new_section_needed = false."""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    data = r.json()
    if "content" in data and data["content"]:
        text = data["content"][0]["text"].strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return {}

# ── تحديث HTML بـ regex (لا يمس التصميم) ──────────────────────────────────
def update_html(d):
    print("📝 تحديث الداشبورد...")

    # اقرأ الـ template الأصلي دائماً
    src = "template.html" if os.path.exists("template.html") else "index.html"
    with open(src, "r", encoding="utf-8") as f:
        html = f.read()

    if not d:
        return html

    now = d.get("time", datetime.utcnow().strftime("%H:%M UTC · %d/%m/%Y"))

    # 1. تحديث الوقت في الـ header
    html = re.sub(
        r'(آخر تحديث:)[^\n<]*',
        f'\\1 {now}',
        html
    )
    # تحديث أي توقيت UTC موجود
    html = re.sub(
        r'\d{2}:\d{2} UTC · \d{2}/\d{2}/\d{4}',
        now,
        html
    )

    # 2. تحديث BTC
    if d.get("btc_price"):
        html = re.sub(r'\$6[5-9],\d{3}|\$7[0-9],\d{3}|\$8[0-5],\d{3}', d["btc_price"], html)
    if d.get("btc_change"):
        html = re.sub(r'[▲▼]\s*[+-]?\d+\.\d+%(?=.*BTC|.*Bitcoin)', d["btc_change"], html, count=2)

    # 3. تحديث النفط
    if d.get("brent"):
        html = re.sub(r'~\$\d{2,3}(?=.*[Bb]rent|.*BRENT)', d["brent"], html, count=3)
    if d.get("wti"):
        html = re.sub(r'~\$\d{2,3}(?=.*[Ww][Tt][Ii]|.*CRUDE)', d["wti"], html, count=3)

    # 4. تحديث الذهب
    if d.get("gold"):
        html = re.sub(r'\$4,[1-9]\d{2}|\$[35],\d{3}', d["gold"], html, count=3)

    # 5. تحديث S&P
    if d.get("sp500"):
        html = re.sub(r'6,[0-9]{3}(?=.*S&P|.*S&amp;P)', d["sp500"], html, count=3)

    # 6. تحديث Breaking Banner (النص فقط)
    if d.get("breaking_news") and d["breaking_news"] != "null":
        html = re.sub(
            r'(?<=class="brk-title">)[^<]+',
            d["breaking_news"],
            html,
            count=1
        )

    # 7. إضافة section جديد إذا ضروري جداً
    if d.get("new_section_needed") and d.get("new_section_html"):
        # يضاف قبل الـ footer مباشرة
        html = html.replace(
            '<!-- FOOTER -->',
            f'\n  <!-- NEW SECTION -->\n  {d["new_section_html"]}\n\n  <!-- FOOTER -->'
        )
        print("  ✅ تم إضافة section جديد")

    return html

# ── الرئيسي ────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"⚔️  War Room — {datetime.utcnow().strftime('%H:%M UTC')}")
    print(f"{'='*50}\n")

    # أنشئ template.html إذا ما موجود
    if not os.path.exists("template.html") and os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
        with open("template.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ تم إنشاء template.html من index.html الحالي\n")

    raw_news = fetch_data()
    data     = extract_data(raw_news)
    print(f"  البيانات المستخرجة: {json.dumps(data, ensure_ascii=False, indent=2)}\n")
    new_html = update_html(data)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    print("💾 تم حفظ index.html")
    print("\n✅ اكتمل!\n")

if __name__ == "__main__":
    main()
