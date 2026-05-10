# app/ai_assistant.py
import os
import json
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from .models import Item, Customer, Invoice
from . import db

ai = Blueprint('ai', __name__)

# System prompt for the AI Business Assistant
SYSTEM_PROMPT = """You are an AI Business Assistant integrated into an Inventory Management System.

This system uses the Groq API for fast and accurate AI responses.

Your role is to help business owners understand their business performance, inventory status, and financial health using REAL data provided at runtime.

-----------------------------------
🚨 STRICT DATA RULE (VERY IMPORTANT):
-----------------------------------

- You MUST ONLY use the data provided in the input JSON.
- NEVER generate, assume, or use mock/fake/sample data.
- If required data is missing, incomplete, or unclear:
  → Ask the user for the missing data.
  → Do NOT guess or estimate values.

-----------------------------------
🎯 CORE RESPONSIBILITIES:
-----------------------------------

1. Answer user queries related to:
   - Sales
   - Profit & Loss
   - Inventory stock
   - Product performance
   - Business trends
   - Low stock alerts
   - Revenue insights

2. Perform accurate calculations ONLY using given data.

3. Provide insights, not just raw numbers.

4. Keep responses:
   - Clear
   - Structured
   - Business-friendly
   - Actionable

-----------------------------------
🧠 BUSINESS LOGIC:
-----------------------------------

Use the following formulas:

1. Revenue:
   revenue = selling_price × quantity_sold

2. Profit:
   profit = (selling_price - cost_price) × quantity_sold

3. Profit Margin:
   profit_margin (%) = (profit / revenue) × 100

4. Inventory Health:
   - Low stock: stock < 20
   - Overstock: stock > 200
   - Fast moving: sold > 50
   - Dead stock: sold = 0

-----------------------------------
📈 BUSINESS HEALTH ANALYSIS:
-----------------------------------

Always classify business health into:

- 🟢 GOOD
- 🟡 AVERAGE
- 🔴 POOR

Based ONLY on real computed values:
- Total profit
- Sales performance
- Stock movement

-----------------------------------
📌 RESPONSE FORMAT:
-----------------------------------

Always structure your response like:

1. 📊 Summary
2. 💰 Financial Insights
3. 📦 Inventory Insights
4. 🚨 Issues (if any)
5. 💡 Recommendations

-----------------------------------
⚠️ IMPORTANT RULES:
-----------------------------------

- Do NOT hallucinate or fabricate any numbers.
- Do NOT assume missing values.
- If data is missing → clearly say:
  "I need more data to answer this accurately."
- Always show calculated values clearly.
- Keep answers concise but insightful.
- Use markdown formatting for better readability.
- Use emojis sparingly for visual appeal.

-----------------------------------
🎯 TONE:
-----------------------------------

Professional, smart, and helpful like a business analyst.
"""


def get_business_data():
    """Collect real business data from the database to provide context to the AI."""
    try:
        # Inventory data
        items = Item.query.all()
        products_data = []
        for item in items:
            products_data.append({
                "name": item.name,
                "sku": item.sku,
                "stock": item.quantity,
                "price": item.price,
                "total_value": item.value
            })

        # Customer data
        customers = Customer.query.all()
        customers_data = []
        for customer in customers:
            customers_data.append({
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone or "N/A",
                "total_invoices": len(customer.invoices) if customer.invoices else 0
            })

        # Invoice data
        invoices = Invoice.query.all()
        invoices_data = []
        for invoice in invoices:
            invoices_data.append({
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name if invoice.customer else "Unknown",
                "total_amount": invoice.total_amount,
                "status": invoice.status,
                "created_at": invoice.created_at.strftime('%Y-%m-%d %H:%M') if invoice.created_at else "N/A"
            })

        # Summary metrics
        total_items = len(items)
        total_inventory_value = sum(item.value for item in items)
        low_stock_items = [item.name for item in items if item.quantity <= 10]
        overstock_items = [item.name for item in items if item.quantity > 200]
        total_customers = len(customers)
        total_invoices = len(invoices)
        paid_invoices = sum(1 for inv in invoices if inv.status == 'paid')
        pending_invoices = sum(1 for inv in invoices if inv.status == 'pending')
        cancelled_invoices = sum(1 for inv in invoices if inv.status == 'cancelled')
        total_revenue = sum(inv.total_amount for inv in invoices if inv.status == 'paid')
        pending_revenue = sum(inv.total_amount for inv in invoices if inv.status == 'pending')

        business_data = {
            "summary": {
                "total_products": total_items,
                "total_inventory_value": round(total_inventory_value, 2),
                "total_customers": total_customers,
                "total_invoices": total_invoices,
                "paid_invoices": paid_invoices,
                "pending_invoices": pending_invoices,
                "cancelled_invoices": cancelled_invoices,
                "total_revenue_from_paid": round(total_revenue, 2),
                "pending_revenue": round(pending_revenue, 2)
            },
            "products": products_data,
            "customers": customers_data,
            "invoices": invoices_data,
            "alerts": {
                "low_stock_items": low_stock_items,
                "overstock_items": overstock_items
            }
        }

        return business_data
    except Exception as e:
        return {"error": f"Failed to fetch business data: {str(e)}"}


def query_groq(user_message, business_data, conversation_history=None):
    """Send a query to the Groq API with business context."""
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Re-read .env to pick up any changes
    
    api_key = os.getenv('GROQ_API_KEY')

    if not api_key or api_key == 'your-groq-api-key-here':
        return "⚠️ **Groq API Key not configured.**\n\nPlease add your Groq API key to the `.env` file:\n```\nGROQ_API_KEY=your-api-key-here\n```\nGet a free API key at [console.groq.com](https://console.groq.com)"

    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        # Build the messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Here is the current REAL business data from the database:\n```json\n{json.dumps(business_data, indent=2)}\n```\nUse ONLY this data to answer queries. Do NOT make up any numbers."}
        ]

        # Add conversation history if available
        if conversation_history:
            for msg in conversation_history:
                messages.append(msg)

        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        # Call Groq API
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2048,
            top_p=0.9,
        )

        return chat_completion.choices[0].message.content

    except ImportError:
        return " **Groq package not installed.**\n\nRun:\n```\npip install groq\n```"
    except Exception as e:
        return f" **Error communicating with AI:**\n\n{str(e)}"


@ai.route('/ai-assistant')
@login_required
def ai_assistant():
    """Render the AI Assistant chat page."""
    return render_template('ai_assistant.html')


@ai.route('/ai-assistant/chat', methods=['POST'])
@login_required
def ai_chat():
    """Handle AI chat messages via AJAX."""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    conversation_history = data.get('history', [])

    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    # Get real business data from the database
    business_data = get_business_data()

    # Query the AI
    ai_response = query_groq(user_message, business_data, conversation_history)

    return jsonify({
        "response": ai_response,
        "data_snapshot": business_data.get("summary", {})
    })
