import sqlite3
from datetime import datetime, timedelta
import io
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
app = Flask(__name__)
# In production, this should be an environment variable.
app.secret_key = 'super_secret_kitchen_key'
DATABASE = 'inventory.db'
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                type TEXT NOT NULL,
                expiry_date TEXT,
                shelf_life TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                amount_used REAL NOT NULL,
                unit TEXT NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (item_id) REFERENCES items (id)
            )
        ''')
        db.commit()
init_db()
def get_item_status(item):
    """Calculate the status of an item based on its quantity and dates."""
    status_list = []
    
    # Check low stock
    if float(item['quantity']) <= 5:
        status_list.append('LOW STOCK')
        
    # Check perishable logic
    if item['type'] == 'perishable' and item['expiry_date']:
        try:
            today = datetime.now().date()
            expiry = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            if today > expiry:
                status_list.append('EXPIRED')
            elif today + timedelta(days=7) >= expiry:
                status_list.append('EXPIRING SOON')
        except ValueError:
            pass # Handle poorly formatted dates gracefully
            
    if not status_list:
        return 'NORMAL'
        
    return ' | '.join(status_list)
def dict_from_row(row):
    """Convert a row to a dictionary and append the calculated status."""
    d = dict(row)
    d['status'] = get_item_status(d)
    return d
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                (name, email, generate_password_hash(password))
            )
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
            
    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
            
        flash('Invalid email or password.', 'danger')
        
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    items_raw = db.execute('SELECT * FROM items WHERE user_id = ?', (session['user_id'],)).fetchall()
    items = [dict_from_row(row) for row in items_raw]
    
    total_items = len(items)
    perishable = sum(1 for item in items if item['type'] == 'perishable')
    non_perishable = sum(1 for item in items if item['type'] == 'non-perishable')
    
    expired_items = [item for item in items if 'EXPIRED' in item['status']]
    
    top_used_raw = db.execute('''
        SELECT item_name, unit, SUM(amount_used) as total_used 
        FROM usage_history 
        WHERE user_id = ? 
        GROUP BY item_id 
        ORDER BY total_used DESC 
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    top_used = [dict(row) for row in top_used_raw]
    
    return render_template('dashboard.html', 
                         total=total_items, 
                         perishable=perishable, 
                         non_perishable=non_perishable,
                         expired_items=expired_items,
                         top_used=top_used)
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        unit = request.form['unit']
        item_type = request.form['type']
        
        # Determine specific fields based on type
        expiry_date = request.form.get('expiry_date') if item_type == 'perishable' else None
        shelf_life = request.form.get('shelf_life') if item_type == 'non-perishable' else None
        
        db = get_db()
        db.execute(
            '''INSERT INTO items (user_id, name, quantity, unit, type, expiry_date, shelf_life)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (session['user_id'], name, quantity, unit, item_type, expiry_date, shelf_life)
        )
        db.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('inventory'))
        
    return render_template('add_item.html')
@app.route('/inventory')
def inventory():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    items_raw = db.execute('SELECT * FROM items WHERE user_id = ?', (session['user_id'],)).fetchall()
    items = [dict_from_row(row) for row in items_raw]
    
    return render_template('inventory.html', items=items)
@app.route('/use_item/<int:item_id>', methods=['POST'])
def use_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    amount = float(request.form.get('amount', 0))
    if amount <= 0:
        flash('Amount to use must be greater than zero.', 'danger')
        return redirect(url_for('inventory'))
        
    db = get_db()
    item = db.execute('SELECT quantity, name, unit FROM items WHERE id = ? AND user_id = ?', 
                      (item_id, session['user_id'])).fetchone()
                      
    if item:
        new_quantity = max(0, float(item['quantity']) - amount)
        db.execute('UPDATE items SET quantity = ? WHERE id = ?', (new_quantity, item_id))
        
        # Log usage history
        actual_used = float(item['quantity']) - new_quantity
        if actual_used > 0:
            db.execute('''INSERT INTO usage_history (user_id, item_id, item_name, amount_used, unit)
                          VALUES (?, ?, ?, ?, ?)''', 
                       (session['user_id'], item_id, item['name'], actual_used, item['unit']))
                       
        db.commit()
        flash('Item used.', 'success')
        
    return redirect(url_for('inventory'))
@app.route('/refill_item/<int:item_id>', methods=['POST'])
def refill_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    amount = float(request.form.get('amount', 0))
    if amount <= 0:
        flash('Amount to refill must be greater than zero.', 'danger')
        return redirect(url_for('inventory'))
        
    db = get_db()
    item = db.execute('SELECT quantity FROM items WHERE id = ? AND user_id = ?', 
                      (item_id, session['user_id'])).fetchone()
                      
    if item:
        new_quantity = float(item['quantity']) + amount
        db.execute('UPDATE items SET quantity = ? WHERE id = ?', (new_quantity, item_id))
        db.commit()
        flash('Item refilled.', 'success')
        
    return redirect(url_for('inventory'))
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    history_raw = db.execute('''
        SELECT item_name, amount_used, unit, used_at 
        FROM usage_history 
        WHERE user_id = ? 
        ORDER BY used_at DESC
    ''', (session['user_id'],)).fetchall()
    
    history_logs = [dict(row) for row in history_raw]
    return render_template('history.html', logs=history_logs)
@app.route('/shopping_list')
def shopping_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    items_raw = db.execute('SELECT * FROM items WHERE user_id = ?', (session['user_id'],)).fetchall()
    
    # Filter for low stock or expired/expiring soon items to auto-include
    list_items = []
    for row in items_raw:
        item = dict_from_row(row)
        if 'LOW STOCK' in item['status'] or 'EXPIRED' in item['status'] or 'EXPIRING SOON' in item['status'] or float(item['quantity']) == 0:
            list_items.append(item)
            
    return render_template('shopping_list.html', items=list_items)
@app.route('/generate_pdf')
def generate_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    items_raw = db.execute('SELECT * FROM items WHERE user_id = ?', (session['user_id'],)).fetchall()
    
    # Same filter as shopping list
    list_items = []
    for row in items_raw:
        item = dict_from_row(row)
        if 'LOW STOCK' in item['status'] or 'EXPIRED' in item['status'] or 'EXPIRING SOON' in item['status'] or float(item['quantity']) == 0:
            list_items.append(item)
            
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "Kitchen Inventory - Shopping List")
    
    p.setFont("Helvetica", 12)
    y = 710
    
    if not list_items:
        p.drawString(50, y, "Your shopping list is currently empty.")
    else:
        # Table Header
        p.drawString(50, y, "Item Name")
        p.drawString(250, y, "Current Quantity")
        p.drawString(400, y, "Status")
        
        p.line(50, y - 5, 550, y - 5)
        y -= 25
        
        for item in list_items:
            if y < 50:
                p.showPage()
                y = 750
            p.drawString(50, y, str(item['name']))
            p.drawString(250, y, f"{item['quantity']} {item['unit']}")
            p.drawString(400, y, str(item['status']))
            y -= 25
            
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='shopping_list.pdf', mimetype='application/pdf')
if __name__ == '__main__':
    app.run(debug=True)