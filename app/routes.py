# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from .models import Item, Customer, Invoice, StockHistory, Expense
from .forms import ItemForm, ProfileForm
from . import db
from datetime import datetime, timedelta

main = Blueprint('main', __name__)

@main.route('/dashboard')
@login_required
def dashboard():
   
    total_items = Item.query.count()
    low_stock_items = Item.query.filter(Item.quantity <= 10).count()
    
    # Calculate total sales — ONLY paid invoices
    paid_invoices = Invoice.query.filter_by(status='paid').all()
    total_sales = sum(inv.total_amount for inv in paid_invoices)
    
    # Calculate actual metrics
    total_invoices = Invoice.query.count()
    total_customers = Customer.query.count()
    pending_invoices = Invoice.query.filter_by(status='pending').count()
    
    # Get pending invoices with customer details for the Pending Payments widget
    pending_invoices_list = Invoice.query.filter_by(status='pending').order_by(Invoice.created_at.desc()).limit(10).all()

    return render_template('dashboard.html', 
                           total_items=total_items, 
                           total_sales=total_sales,
                           low_stock_items=low_stock_items,
                           total_invoices=total_invoices,
                           total_customers=total_customers,
                           pending_invoices=pending_invoices,
                           pending_invoices_list=pending_invoices_list
                           )

@main.route('/inventory')
@login_required
def inventory():
    items = Item.query.all()  # Fetch all items from database
    return render_template('inventory.html', items=items)


@main.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        item = Item(
            name=form.name.data,
            sku=form.sku.data,
            quantity=form.quantity.data,
            price=form.price.data
        )
        try:
            db.session.add(item)
            db.session.flush()  # Get item.id before commit
            # Record initial stock snapshot
            history = StockHistory(item_id=item.id, quantity=item.quantity)
            db.session.add(history)
            db.session.commit()
            flash('Item added successfully!', 'success')
            return redirect(url_for('main.inventory'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding item. SKU might already exist.', 'error')
    
    return render_template('add_item.html', form=form)


@main.route('/inventory/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = ItemForm(obj=item)
    
    if form.validate_on_submit():
        item.name = form.name.data
        item.sku = form.sku.data
        item.quantity = form.quantity.data
        item.price = form.price.data
        
        try:
            # Record stock snapshot on every update
            history = StockHistory(item_id=item.id, quantity=form.quantity.data)
            db.session.add(history)
            db.session.commit()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('main.inventory'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating item.', 'error')
    
    return render_template('edit_item.html', form=form, item=item)


@main.route('/inventory/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    try:
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting item.', 'error')
    
    return redirect(url_for('main.inventory'))

@main.route('/invoices')
@login_required
def invoices():
    invoices = Invoice.query.all()
    customers = Customer.query.all()
    return render_template('invoices.html', invoices=invoices, customers=customers)


@main.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create_invoice():
    if request.method == 'POST':
        invoice_number = request.form.get('invoice_number')
        customer_id = request.form.get('customer_id')
        total_amount = float(request.form.get('total_amount', 0))
        status = request.form.get('status', 'pending')
        
        if invoice_number and customer_id:
            invoice = Invoice(
                invoice_number=invoice_number,
                customer_id=customer_id,
                total_amount=total_amount,
                status=status
            )
            try:
                db.session.add(invoice)
                db.session.commit()
                flash('Invoice created successfully!', 'success')
                return redirect(url_for('main.invoices'))
            except Exception as e:
                db.session.rollback()
                flash('Error creating invoice. Invoice number might already exist.', 'error')
        else:
            flash('Invoice number and customer are required.', 'error')
    
    customers = Customer.query.all()
    items = Item.query.all()
    return render_template('create_invoice.html', customers=customers, items=items)


@main.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    try:
        db.session.delete(invoice)
        db.session.commit()
        flash('Invoice deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting invoice.', 'error')
    
    return redirect(url_for('main.invoices'))


@main.route('/invoices/<int:invoice_id>/json')
@login_required
def get_invoice_json(invoice_id):
    """Return invoice data as JSON for the edit modal."""
    invoice = Invoice.query.get_or_404(invoice_id)
    return jsonify({
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'customer_id': invoice.customer_id,
        'customer_name': invoice.customer.name,
        'total_amount': invoice.total_amount,
        'status': invoice.status
    })


@main.route('/invoices/edit/<int:invoice_id>', methods=['POST'])
@login_required
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    
    customer_id = request.form.get('customer_id')
    total_amount = request.form.get('total_amount')
    status = request.form.get('status')
    
    if not customer_id or total_amount is None or not status:
        flash('All fields are required.', 'error')
        return redirect(url_for('main.invoices'))
    
    try:
        invoice.customer_id = int(customer_id)
        invoice.total_amount = float(total_amount)
        invoice.status = status
        db.session.commit()
        flash('Invoice updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating invoice.', 'error')
    
    return redirect(url_for('main.invoices'))

@main.route('/customers')
@login_required
def customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)


@main.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    
    if name and email:
        customer = Customer(name=name, email=email, phone=phone, address=address)
        try:
            db.session.add(customer)
            db.session.commit()
            flash('Customer added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding customer. Email might already exist.', 'error')
    else:
        flash('Name and email are required.', 'error')
    
    return redirect(url_for('main.customers'))


@main.route('/customers/delete/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting customer.', 'error')
    
    return redirect(url_for('main.customers'))

@main.route('/transactions')
@login_required
def transactions():
    # For now, we'll create a simple transaction log based on recent activities
    # In a real system, you'd have a separate Transaction model
    recent_items = Item.query.order_by(Item.id.desc()).limit(10).all()
    recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(5).all()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    return render_template('transactions.html', 
                         recent_items=recent_items,
                         recent_customers=recent_customers, 
                         recent_invoices=recent_invoices)

@main.route('/')
def index():
    # Redirect to dashboard if logged in, otherwise to login
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main.route('/settings')
@login_required
def settings():
    form = ProfileForm(obj=current_user)
    return render_template('settings.html', form=form)


@main.route('/settings/update-profile', methods=['POST'])
@login_required
def update_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('main.settings'))
        
        # Check if email changed and if new email is already taken
        if form.email.data != current_user.email:
            from .models import User
            existing = User.query.filter_by(email=form.email.data).first()
            if existing:
                flash('That email is already registered to another account.', 'error')
                return redirect(url_for('main.settings'))
        
        try:
            current_user.username = form.username.data
            current_user.email = form.email.data
            
            # Update password only if a new one was provided
            if form.new_password.data:
                current_user.set_password(form.new_password.data)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'error')
    
    return redirect(url_for('main.settings'))


@main.route('/api/sales-analytics')
@login_required
def sales_analytics_api():
    """Return paid invoice data aggregated by time period for the dashboard chart."""
    period = request.args.get('period', '30days')
    now = datetime.utcnow()

    if period == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        invoices = Invoice.query.filter(
            Invoice.status == 'paid',
            Invoice.created_at >= start
        ).all()
        # Group by hour
        buckets = {}
        for h in range(24):
            buckets[h] = 0.0
        for inv in invoices:
            buckets[inv.created_at.hour] += inv.total_amount
        labels = [f'{h:02d}:00' for h in range(24)]
        data = [round(buckets[h], 2) for h in range(24)]

    elif period == '7days':
        start = now - timedelta(days=6)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        invoices = Invoice.query.filter(
            Invoice.status == 'paid',
            Invoice.created_at >= start
        ).all()
        # Group by day
        buckets = {}
        for d in range(7):
            day = (start + timedelta(days=d)).date()
            buckets[day] = 0.0
        for inv in invoices:
            day = inv.created_at.date()
            if day in buckets:
                buckets[day] += inv.total_amount
        labels = [d.strftime('%d %b') for d in sorted(buckets.keys())]
        data = [round(buckets[d], 2) for d in sorted(buckets.keys())]

    elif period == '1year':
        start = now - timedelta(days=364)
        start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        invoices = Invoice.query.filter(
            Invoice.status == 'paid',
            Invoice.created_at >= start
        ).all()
        # Group by month
        buckets = {}
        for m in range(12):
            month_start = now.replace(day=1) - timedelta(days=30 * (11 - m))
            key = (month_start.year, month_start.month)
            buckets[key] = 0.0
        for inv in invoices:
            key = (inv.created_at.year, inv.created_at.month)
            if key in buckets:
                buckets[key] += inv.total_amount
        sorted_keys = sorted(buckets.keys())
        labels = [datetime(y, m, 1).strftime('%b %Y') for y, m in sorted_keys]
        data = [round(buckets[k], 2) for k in sorted_keys]

    else:  # 30days default
        start = now - timedelta(days=29)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        invoices = Invoice.query.filter(
            Invoice.status == 'paid',
            Invoice.created_at >= start
        ).all()
        # Group by day
        buckets = {}
        for d in range(30):
            day = (start + timedelta(days=d)).date()
            buckets[day] = 0.0
        for inv in invoices:
            day = inv.created_at.date()
            if day in buckets:
                buckets[day] += inv.total_amount
        labels = [d.strftime('%d %b') for d in sorted(buckets.keys())]
        data = [round(buckets[d], 2) for d in sorted(buckets.keys())]

    total = round(sum(data), 2)
    return jsonify({'labels': labels, 'data': data, 'total': total})


# ── Expenses CRUD ─────────────────────────────────────────────────

@main.route('/expenses')
@login_required
def expenses():
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    return render_template('expenses.html', expenses=expenses)


@main.route('/expenses/add', methods=['POST'])
@login_required
def add_expense():
    title = request.form.get('title')
    amount = request.form.get('amount')
    category = request.form.get('category', 'General')
    description = request.form.get('description', '')
    expense_date = request.form.get('expense_date')

    if not title or amount is None:
        flash('Title and amount are required.', 'error')
        return redirect(url_for('main.expenses'))

    try:
        expense = Expense(
            title=title,
            amount=float(amount),
            category=category or 'General',
            description=description,
            expense_date=datetime.strptime(expense_date, '%Y-%m-%d') if expense_date else datetime.utcnow()
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error adding expense.', 'error')

    return redirect(url_for('main.expenses'))


@main.route('/expenses/<int:expense_id>/json')
@login_required
def get_expense_json(expense_id):
    """Return expense data as JSON for the edit modal."""
    expense = Expense.query.get_or_404(expense_id)
    return jsonify({
        'id': expense.id,
        'title': expense.title,
        'amount': expense.amount,
        'category': expense.category,
        'description': expense.description or '',
        'expense_date': expense.expense_date.strftime('%Y-%m-%d') if expense.expense_date else ''
    })


@main.route('/expenses/edit/<int:expense_id>', methods=['POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    title = request.form.get('title')
    amount = request.form.get('amount')
    category = request.form.get('category', 'General')
    description = request.form.get('description', '')
    expense_date = request.form.get('expense_date')

    if not title or amount is None:
        flash('Title and amount are required.', 'error')
        return redirect(url_for('main.expenses'))

    try:
        expense.title = title
        expense.amount = float(amount)
        expense.category = category or 'General'
        expense.description = description
        if expense_date:
            expense.expense_date = datetime.strptime(expense_date, '%Y-%m-%d')
        db.session.commit()
        flash('Expense updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating expense.', 'error')

    return redirect(url_for('main.expenses'))


@main.route('/expenses/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting expense.', 'error')

    return redirect(url_for('main.expenses'))
