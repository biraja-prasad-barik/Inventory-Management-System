# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from .models import Item, Customer, Invoice
from .forms import ItemForm
from . import db 

main = Blueprint('main', __name__)

@main.route('/dashboard')
@login_required
def dashboard():
   
    total_items = Item.query.count()
    low_stock_items = Item.query.filter(Item.quantity <= 10).count()
    
    # Calculate actual inventory value
    items = Item.query.all()
    inventory_value = sum(item.value for item in items)
    
    # Calculate actual metrics
    total_invoices = Invoice.query.count()
    total_customers = Customer.query.count()
    pending_invoices = Invoice.query.filter_by(status='pending').count()

    return render_template('dashboard.html', 
                           total_items=total_items, 
                           inventory_value=inventory_value,
                           low_stock_items=low_stock_items,
                           total_invoices=total_invoices,
                           total_customers=total_customers,
                           pending_invoices=pending_invoices
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
    return render_template('invoices.html', invoices=invoices)


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
