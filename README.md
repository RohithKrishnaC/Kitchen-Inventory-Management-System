# Kitchen Inventory Management System

A full-stack web application built with Python (Flask) and SQLite to help you track perishable and non-perishable kitchen items, automated low stock alerts, and downloadable shopping lists.

## Features

- **User Authentication:** Registration and simple login logic via Flask sessions and Werkzeug hashing.
- **Inventory Tracking:** Add, use, and refill stock for kitchen supplies.
- **Dynamic Categories:** Stores Perishable vs Non-Perishable details.
- **Smart Alerts:** Flags items that are Low Stock (<= 5), Expiring Soon, or Expired.
- **PDF Shopping List:** Generates an automated PDF using `reportlab`.

## Tech Stack
- Backend: Python (Flask)
- Frontend: HTML/CSS (Custom Premium Design)
- Database: SQLite

## Folder Structure

```
kitchen_inventory/
├── app.py                 # Main Flask Application
├── requirements.txt       # Python dependencies
├── README.md              # Instructions
├── inventory.db           # SQLite DB (auto-generated on run)
├── static/
│   └── css/
│       └── styles.css     # Premium UI styling
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── add_item.html
    ├── inventory.html
    └── shopping_list.html
```

## How to Run Locally

1. **Verify Python Configuration**
   Make sure you have Python 3.7+ installed.

2. **Setup Virtual Environment (Recommended on Windows)**
   Navigate into the project directory and create a virtual environment:
   ```bash
   cd C:/Users/ROHITH/kitchen_inventory
   python -m venv venv
   ```

   Activate the virtual environment:
   ```bash
   # In Command Prompt
   venv\Scripts\activate.bat
   # In PowerShell
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Server**
   ```bash
   python app.py
   ```

5. **Open Browser**
   Go to `http://127.0.0.1:5000` to register, log in, and test your new application!
=======
# Kitchen-Inventory-Management-System
A practical kitchen inventory management system for restaurants built with Flask, enabling real-time stock tracking, low-stock alerts, and automated shopping list generation to improve operational efficiency and reduce waste.
