# app/inventory_monitor.py
import os
import json
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from .models import Item, StockHistory
from . import db

monitor = Blueprint('monitor', __name__)

# ─────────────────────────────────────────────
#  SYSTEM PROMPT  (exactly as user specified)
# ─────────────────────────────────────────────
MONITOR_SYSTEM_PROMPT = """You are an AI Inventory Monitoring Assistant integrated into an Inventory Management System powered by the Groq API.

Your task is to analyze REAL inventory data and detect:

1. Low stock products
2. Products with decreasing stock trends over time

-----------------------------------
🚨 STRICT DATA RULE:
-----------------------------------

- Use ONLY the provided database data.
- Do NOT generate or assume any values.
- If historical data is missing, clearly say:
  "I need historical stock data to detect stock trends."

-----------------------------------
🧠 DETECTION LOGIC:
-----------------------------------

1. LOW STOCK:
   - If current_stock < 20 → mark as "Low Stock"

2. DECREASING STOCK TREND:
   - If stock values are continuously decreasing in previous_stock
   - OR clear downward pattern
   → mark as "Decreasing Trend"

3. CRITICAL ALERT:
   - If both conditions are true → mark as "Critical"

-----------------------------------
📌 RESPONSE FORMAT:
-----------------------------------

For each affected product:

📦 Product: <name>

- Current Stock: <value>
- Status:
   - Low Stock / Normal
   - Decreasing Trend / Stable

🚨 Alert:
- Clearly state: "Stock is continuously decreasing based on database records."

💡 Recommendation:
- Restock immediately (if critical)
- Monitor closely (if decreasing)

-----------------------------------
⚠️ IMPORTANT RULES:
-----------------------------------

- Do NOT analyze products without sufficient data.
- Do NOT guess trends.
- Always base trend detection on actual historical values.
- Keep response short, clear, and alert-focused.
- Use markdown formatting.

-----------------------------------
🎯 OUTPUT STYLE:
-----------------------------------

Professional, alert-based, and actionable (like a real inventory monitoring system).
End your response with a single line overall summary like:
**Overall Status: X products need attention.**
"""


def get_inventory_monitor_data():
    """
    Collect real stock data + history for every item.
    Returns the structured JSON the AI prompt expects.
    """
    items = Item.query.all()
    products = []

    for item in items:
        history_records = (
            StockHistory.query
            .filter_by(item_id=item.id)
            .order_by(StockHistory.recorded_at.asc())
            .all()
        )

        # Previous snapshots excluding the current (already in item.quantity)
        previous_stock = [h.quantity for h in history_records]

        products.append({
            "name": item.name,
            "sku": item.sku,
            "current_stock": item.quantity,
            "previous_stock": previous_stock,   # Full history from DB
            "price": item.price,
            "total_value": item.value
        })

    return {
        "total_products": len(products),
        "products": products
    }


def _detect_trend_locally(previous_stock):
    """
    Quick local check: is this a strictly/mostly decreasing series?
    Used to pre-classify before sending to AI.
    """
    if len(previous_stock) < 2:
        return "insufficient_data"
    decreases = sum(
        1 for i in range(1, len(previous_stock))
        if previous_stock[i] < previous_stock[i - 1]
    )
    ratio = decreases / (len(previous_stock) - 1)
    if ratio >= 0.7:
        return "decreasing"
    elif ratio <= 0.3:
        return "increasing"
    return "mixed"


def build_monitor_summary(data):
    """
    Build a quick summary dict so the UI can show stats without waiting for AI.
    """
    products = data.get("products", [])
    low_stock = [p for p in products if p["current_stock"] < 20]
    critical = [
        p for p in low_stock
        if _detect_trend_locally(p["previous_stock"]) == "decreasing"
    ]
    decreasing = [
        p for p in products
        if p["current_stock"] >= 20
        and _detect_trend_locally(p["previous_stock"]) == "decreasing"
    ]
    return {
        "total": len(products),
        "low_stock_count": len(low_stock),
        "critical_count": len(critical),
        "decreasing_count": len(decreasing),
        "ok_count": len(products) - len(low_stock) - len(decreasing),
    }


def run_ai_monitor(inventory_data):
    """Call Groq with the monitoring system prompt + real DB data."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or api_key == "your-groq-api-key-here":
        return (
            "⚠️ **Groq API Key not configured.**\n\n"
            "Add `GROQ_API_KEY=your-key` to your `.env` file and restart the server.\n"
            "Get a free key at [console.groq.com](https://console.groq.com)"
        )

    if not inventory_data.get("products"):
        return "📦 No inventory items found. Add products first to enable monitoring."

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        user_content = (
            "Analyze the following REAL inventory data from my database.\n"
            "Detect low stock and decreasing trends. Provide structured alerts.\n\n"
            f"```json\n{json.dumps(inventory_data, indent=2)}\n```"
        )

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": MONITOR_SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=3000,
        )
        return response.choices[0].message.content

    except ImportError:
        return "⚠️ `groq` package not installed. Run: `pip install groq`"
    except Exception as exc:
        return f"⚠️ **AI Error:** {exc}"


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@monitor.route("/inventory-monitor")
@login_required
def inventory_monitor():
    """Render the monitoring dashboard (data loaded via AJAX)."""
    return render_template("inventory_monitor.html")


@monitor.route("/inventory-monitor/analyze", methods=["POST"])
@login_required
def analyze():
    """AJAX endpoint: fetch DB data → call Groq → return results."""
    inventory_data = get_inventory_monitor_data()
    summary        = build_monitor_summary(inventory_data)
    ai_analysis    = run_ai_monitor(inventory_data)

    return jsonify({
        "summary":       summary,
        "ai_analysis":   ai_analysis,
        "raw_data":      inventory_data,
    })
