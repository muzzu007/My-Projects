import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import sqlite3
import os
import random
from datetime import datetime
import pandas as pd
import subprocess
import webbrowser
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import traceback

# ==============================================
# DATABASE SETUP
# ==============================================

class DatabaseManager:
    def __init__(self):
        self.setup_database()
        
    def setup_database(self):
        """Create SQLite database and tables"""
        conn = sqlite3.connect('inventory_store_database.db')
        cursor = conn.cursor()
        
        # Create products table - no qrcode_image, no media_paths
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT NOT NULL,
            size TEXT,
            purchase_price_with_gst REAL,
            selling_price_with_gst REAL,
            price_before_gst REAL,
            gst_amount REAL,
            gst_percentage REAL DEFAULT 5.0,
            stock INTEGER DEFAULT 0,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Active',
            profit REAL
        )
        ''')
        
        # Create invoices table with profit tracking
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE,
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            customer_city TEXT,
            subtotal REAL,
            tax_amount REAL,
            discount_amount REAL DEFAULT 0,
            discount_percentage REAL DEFAULT 0,
            total_amount REAL,
            invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT,
            total_profit REAL,
            status TEXT DEFAULT 'Active'
        )
        ''')
        
        # Create invoice_items table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            product_id INTEGER,
            barcode TEXT,
            product_name TEXT,
            size TEXT,
            quantity INTEGER,
            unit_price REAL,
            unit_gst REAL,
            unit_price_with_gst REAL,
            total_price REAL,
            total_gst REAL,
            total_with_gst REAL,
            purchase_price REAL,
            profit REAL,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
        ''')
        
        # Create profit_report table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS profit_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date DATE,
            total_sales_with_gst REAL,
            total_purchases REAL,
            total_profit REAL,
            total_gst_collected REAL,
            total_discount_given REAL,
            number_of_invoices INTEGER
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        return sqlite3.connect('inventory_store_database.db')


# ==============================================
# UTILITY FUNCTIONS
# ==============================================

def calculate_gst_breakdown(price, price_includes_gst=True, gst_percentage=5):
    if price_includes_gst:
        price_before_gst = price / (1 + (gst_percentage / 100))
        gst_amount = price - price_before_gst
    else:
        price_before_gst = price
        gst_amount = price * (gst_percentage / 100)
    
    return {
        'price_with_gst': round(price_before_gst + gst_amount, 2),
        'price_before_gst': round(price_before_gst, 2),
        'gst_amount': round(gst_amount, 2),
        'gst_percentage': gst_percentage
    }

def calculate_profit(purchase_price_with_gst, selling_price_with_gst):
    return round(selling_price_with_gst - purchase_price_with_gst, 2)

def generate_unique_barcode():
    conn = sqlite3.connect('inventory_store_database.db')
    cursor = conn.cursor()
    while True:
        barcode = str(random.randint(100000000000, 999999999999))
        cursor.execute("SELECT barcode FROM products WHERE barcode = ?", (barcode,))
        if not cursor.fetchone():
            break
    conn.close()
    return barcode

def generate_invoice_number():
    today = datetime.now().strftime("%Y%m%d")
    existing_numbers = set()
    
    conn = sqlite3.connect('inventory_store_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT invoice_number FROM invoices WHERE invoice_number LIKE ?", (f'INV-{today}-%',))
    for inv in cursor.fetchall():
        existing_numbers.add(inv[0])
    conn.close()
    
    sequence = 1
    while True:
        invoice_number = f"INV-{today}-{sequence:03d}"
        if invoice_number not in existing_numbers:
            break
        sequence += 1
    return invoice_number

def delete_invoice_files(invoice_number):
    pdf_path = f"invoices_pdf/Invoice_{invoice_number}.pdf"
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
            return True
        except:
            return False
    return True

# ==============================================
# INVOICE PDF GENERATION (with placeholder company info)
# ==============================================

def create_invoice_pdf(invoice_data, items, subtotal, tax_amount, discount_amount, 
                      discount_percentage, total_amount, filename="invoice.pdf"):
    """Create PDF invoice with placeholder company details"""
    
    # PLACEHOLDER COMPANY INFO
    LOGO_FILENAME = "company_logo.png"   # Replace with your logo file
    COMPANY_INFO = {
        "name": "ADD COMPANY LOGO",
        "address_line1": "ADD ADDRESS",
        "address_line2": "ADD ADDRESS-2",
        "phone": "Phone: PHONE NUMBER"
    }
    
    if not os.path.exists("invoices_pdf"):
        os.makedirs("invoices_pdf")
    
    filename = f"invoices_pdf/{filename}"
    
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, 
                           topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Normal'], 
                                fontSize=24, textColor=colors.black, 
                                alignment=TA_RIGHT, spaceAfter=20, 
                                fontName='Helvetica-Bold')
    company_style = ParagraphStyle('CompanyStyle', parent=styles['Normal'], 
                                  fontSize=11, leading=14, textColor=colors.black)
    
    # Header with logo placeholder (if logo file exists)
    left_elements = []
    if os.path.exists(LOGO_FILENAME):
        try:
            logo = RLImage(LOGO_FILENAME)
            display_width = 150
            aspect_ratio = logo.imageHeight / float(logo.imageWidth)
            display_height = display_width * aspect_ratio
            logo.drawWidth = display_width
            logo.drawHeight = display_height
            left_elements.append(logo)
            left_elements.append(Spacer(1, 10))
        except:
            pass
    
    address_block = f"""
    <font size=14><b>{COMPANY_INFO['name']}</b></font><br/>
    {COMPANY_INFO['address_line1']}<br/>
    {COMPANY_INFO['address_line2']}<br/>
    {COMPANY_INFO['phone']}
    """
    left_elements.append(Paragraph(address_block, company_style))
    
    # Invoice details table
    meta_data = [
        ["INVOICE #", "DATE"],
        [invoice_data['invoice_number'], invoice_data['date']]
    ]
    meta_table = Table(meta_data, colWidths=[92, 80], rowHeights=[20, 20])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D3D3D3')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    
    header_container_data = [
        [
            left_elements,
            [
                Paragraph("INVOICE", title_style),
                Spacer(1, 10),
                meta_table
            ]
        ]
    ]
    header_table = Table(header_container_data, colWidths=[300, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, 0), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 30))
    
    # BILL TO
    bill_to_header_style = ParagraphStyle('BillToHeader', parent=styles['Normal'], 
                                         fontSize=13, fontName='Helvetica-Bold', 
                                         textColor=colors.black, alignment=TA_LEFT, 
                                         spaceAfter=5, leftIndent=0)
    bill_to_detail_style = ParagraphStyle('BillToDetail', parent=styles['Normal'], 
                                         fontSize=11, fontName='Helvetica', 
                                         textColor=colors.black, alignment=TA_LEFT, 
                                         leading=14, spaceAfter=10, leftIndent=0)
    story.append(Paragraph("BILL TO", bill_to_header_style))
    customer_details_text = f"""
    <b>Name:</b> {invoice_data['customer_name']}<br/>
    <b>Address:</b> {invoice_data['customer_address']}<br/>
    <b>City/Zip:</b> {invoice_data['customer_city']}<br/>
    <b>Phone:</b> {invoice_data['customer_phone']}
    """
    story.append(Paragraph(customer_details_text, bill_to_detail_style))
    story.append(Spacer(1, 20))
    
    # PRODUCT TABLE
    table_data = [["S.NO.", "PRODUCT NAME", "SIZE", "QUANTITY", "PRICE (Rs.)"]]
    for i, item in enumerate(items, 1):
        table_data.append([
            str(i),
            item['name'],
            item['size'],
            str(item['quantity']),
            f"{item['unit_price_without_tax']:,.2f}"
        ])
    # Fill empty rows to 10
    for _ in range(10 - len(table_data)):
        table_data.append(["", "", "", "", ""])
    
    table_data.append(["", "Subtotal", "", "", f"{subtotal:,.2f}"])
    if discount_amount > 0:
        discount_label = f"Discount ({discount_percentage:.1f}%)" if discount_percentage > 0 else "Discount"
        table_data.append(["", discount_label, "", "", f"-{discount_amount:,.2f}"])
    table_data.append(["", "Tax amount(5%)", "", "", f"{tax_amount:,.2f}"])
    table_data.append(["", "Total", "", "", f"{total_amount:,.2f}"])
    
    num_product_rows = 10
    subtotal_row = num_product_rows
    discount_row = subtotal_row + 1 if discount_amount > 0 else None
    tax_row = discount_row + 1 if discount_amount > 0 else subtotal_row + 1
    total_row = tax_row + 1
    
    col_widths = [40, 180, 60, 60, 80]
    row_heights = [30] + [25] * (total_row)
    row_heights[total_row] = 30
    
    table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
    
    style_commands = [
        ('BOX', (0, 0), (-1, total_row), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D3D3D3')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBEFORE', (1, 0), (1, total_row), 1, colors.black),
        ('LINEBEFORE', (2, 0), (2, total_row), 1, colors.black),
        ('LINEBEFORE', (3, 0), (3, total_row), 1, colors.black),
        ('LINEBEFORE', (4, 0), (4, total_row), 1, colors.black),
        ('ALIGN', (0, 1), (0, num_product_rows - 1), 'CENTER'),
        ('ALIGN', (1, 1), (1, num_product_rows - 1), 'LEFT'),
        ('ALIGN', (2, 1), (2, num_product_rows - 1), 'CENTER'),
        ('ALIGN', (3, 1), (3, num_product_rows - 1), 'CENTER'),
        ('ALIGN', (4, 1), (4, num_product_rows - 1), 'RIGHT'),
        ('VALIGN', (1, 1), (1, len(items)), 'TOP'),
        ('LINEABOVE', (0, subtotal_row), (-1, subtotal_row), 1, colors.black),
        ('FONTNAME', (1, subtotal_row), (-1, subtotal_row), 'Helvetica-Bold'),
        ('ALIGN', (1, subtotal_row), (1, subtotal_row), 'LEFT'),
        ('ALIGN', (4, subtotal_row), (4, subtotal_row), 'RIGHT'),
    ]
    if discount_amount > 0:
        style_commands.extend([
            ('LINEABOVE', (0, discount_row), (-1, discount_row), 1, colors.black),
            ('ALIGN', (1, discount_row), (1, discount_row), 'LEFT'),
            ('ALIGN', (4, discount_row), (4, discount_row), 'RIGHT'),
        ])
    style_commands.extend([
        ('LINEABOVE', (0, tax_row), (-1, tax_row), 1, colors.black),
        ('LINEABOVE', (0, total_row), (-1, total_row), 2, colors.black),
        ('BACKGROUND', (0, total_row), (-1, total_row), colors.HexColor('#F0F0F0')),
        ('FONTNAME', (1, total_row), (-1, total_row), 'Helvetica-Bold'),
        ('FONTSIZE', (1, total_row), (-1, total_row), 12),
        ('ALIGN', (1, total_row), (1, total_row), 'LEFT'),
        ('ALIGN', (4, total_row), (4, total_row), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, len(items)), 5),
        ('BOTTOMPADDING', (0, 1), (-1, len(items)), 2),
        ('TOPPADDING', (0, subtotal_row), (-1, total_row), 6),
    ])
    table.setStyle(TableStyle(style_commands))
    story.append(table)
    
    story.append(Spacer(1, 40))
    # Removed signature line to keep it clean
    doc.build(story)
    return filename


# ==============================================
# MAIN GUI APPLICATION
# ==============================================

class ShoeStoreGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory and Store Management System")
        self.root.geometry("1400x800")
        
        self.db = DatabaseManager()
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.create_product_tab()
        self.create_invoice_tab()
        self.create_invoice_history_tab()
        self.create_profit_report_tab()
        
        self.load_products()
        
    def create_product_tab(self):
        self.product_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.product_frame, text='📦 Product Management')
        
        left_frame = ttk.LabelFrame(self.product_frame, text="Add/Edit Product", padding=10)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # Product Details
        ttk.Label(left_frame, text="Product Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.product_name = ttk.Entry(left_frame, width=30)
        self.product_name.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(left_frame, text="Size:").grid(row=1, column=0, sticky='w', pady=5)
        self.product_size = ttk.Entry(left_frame, width=30)
        self.product_size.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(left_frame, text="Wholesale Price (with GST):").grid(row=2, column=0, sticky='w', pady=5)
        self.purchase_price = ttk.Entry(left_frame, width=30)
        self.purchase_price.grid(row=2, column=1, pady=5, padx=5)
        ttk.Label(left_frame, text="Your cost including GST (e.g., ₹350)").grid(row=2, column=2, sticky='w', padx=5)
        
        # Price Option
        ttk.Label(left_frame, text="Retail Price Option:").grid(row=3, column=0, sticky='w', pady=5)
        self.price_option = tk.StringVar(value="with_tax")
        price_frame = ttk.Frame(left_frame)
        price_frame.grid(row=3, column=1, sticky='w', pady=5)
        ttk.Radiobutton(price_frame, text="With GST Included", variable=self.price_option, 
                       value="with_tax", command=self.update_price_example).pack(anchor='w')
        ttk.Radiobutton(price_frame, text="Without GST", variable=self.price_option, 
                       value="without_tax", command=self.update_price_example).pack(anchor='w')
        
        self.price_example_label = ttk.Label(left_frame, text="Enter ₹650 (includes GST, shows as ₹619 in invoice)")
        self.price_example_label.grid(row=4, column=1, sticky='w', pady=5)
        
        ttk.Label(left_frame, text="Retail Price:").grid(row=5, column=0, sticky='w', pady=5)
        self.selling_price = ttk.Entry(left_frame, width=30)
        self.selling_price.grid(row=5, column=1, pady=5, padx=5)
        
        ttk.Label(left_frame, text="Barcode:").grid(row=6, column=0, sticky='w', pady=5)
        self.barcode_entry = ttk.Entry(left_frame, width=30)
        self.barcode_entry.grid(row=6, column=1, pady=5, padx=5)
        ttk.Button(left_frame, text="Generate", command=self.generate_barcode).grid(row=6, column=2, padx=5)
        
        ttk.Label(left_frame, text="GST Percentage:").grid(row=7, column=0, sticky='w', pady=5)
        self.gst_percentage = ttk.Entry(left_frame, width=30)
        self.gst_percentage.insert(0, "5")
        self.gst_percentage.grid(row=7, column=1, pady=5, padx=5)
        
        ttk.Label(left_frame, text="Stock:").grid(row=8, column=0, sticky='w', pady=5)
        self.product_stock = ttk.Entry(left_frame, width=30)
        self.product_stock.insert(0, "0")
        self.product_stock.grid(row=8, column=1, pady=5, padx=5)
        
        # Profit Preview
        self.profit_preview_label = ttk.Label(left_frame, text="", foreground="green")
        self.profit_preview_label.grid(row=9, column=0, columnspan=3, pady=10)
        self.selling_price.bind('<KeyRelease>', self.update_profit_preview)
        self.purchase_price.bind('<KeyRelease>', self.update_profit_preview)
        
        # Buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=10, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="Add Product", command=self.add_product).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Update Product", command=self.update_product).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_product_form).pack(side='left', padx=5)
        
        # Right Panel - Product List
        right_frame = ttk.LabelFrame(self.product_frame, text="Product List", padding=10)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        search_frame = ttk.Frame(right_frame)
        search_frame.pack(fill='x', pady=5)
        ttk.Label(search_frame, text="Search (Name or Barcode):").pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<KeyRelease>', self.search_products)
        ttk.Button(search_frame, text="Refresh", command=self.load_products).pack(side='left', padx=5)
        
        columns = ('ID', 'Barcode', 'Name', 'Size', 'Wholesale', 'Retail', 'Before GST', 'GST', 'Profit', 'Stock', 'Status')
        self.product_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.product_tree.heading(col, text=col)
            self.product_tree.column(col, width=100)
        self.product_tree.pack(fill='both', expand=True, pady=10)
        self.product_tree.bind('<<TreeviewSelect>>', self.on_product_select)
        
        scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=self.product_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill='x', pady=5)
        ttk.Button(action_frame, text="Delete Selected", command=self.delete_product).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Export to CSV", command=self.export_products).pack(side='left', padx=5)
    
    # --- Product Methods ---
    def update_price_example(self):
        option = self.price_option.get()
        if option == "with_tax":
            self.price_example_label.config(text="Enter ₹650 (includes GST, shows as ₹619 in invoice)")
        else:
            self.price_example_label.config(text="Enter ₹619 (adds GST, total ₹650 in invoice)")
    
    def update_profit_preview(self, event=None):
        try:
            purchase = float(self.purchase_price.get()) if self.purchase_price.get() else 0
            selling = float(self.selling_price.get()) if self.selling_price.get() else 0
            option = self.price_option.get()
            gst_percentage = float(self.gst_percentage.get()) if self.gst_percentage.get() else 5
            if purchase > 0 and selling > 0:
                if option == "with_tax":
                    breakdown = calculate_gst_breakdown(selling, True, gst_percentage)
                    selling_price_with_gst = selling
                else:
                    breakdown = calculate_gst_breakdown(selling, False, gst_percentage)
                    selling_price_with_gst = breakdown['price_with_gst']
                profit = calculate_profit(purchase, selling_price_with_gst)
                price_before_gst = breakdown['price_before_gst']
                gst_amount = breakdown['gst_amount']
                self.profit_preview_label.config(
                    text=f"Profit: ₹{profit:.2f} | Price with GST: ₹{selling_price_with_gst:.2f} | Price without GST: ₹{price_before_gst:.2f} | GST: ₹{gst_amount:.2f}"
                )
        except:
            pass
    
    def generate_barcode(self):
        barcode = generate_unique_barcode()
        self.barcode_entry.delete(0, tk.END)
        self.barcode_entry.insert(0, barcode)
    
    def add_product(self):
        name = self.product_name.get().strip()
        size = self.product_size.get().strip()
        current_barcode = self.barcode_entry.get().strip()
        
        if not name or not self.selling_price.get() or not self.purchase_price.get():
            messagebox.showwarning("Warning", "Product Name, Retail Price, and Wholesale Price are required.")
            return
        
        try:
            purchase_price = float(self.purchase_price.get())
            selling_price = float(self.selling_price.get())
            gst_percentage = float(self.gst_percentage.get())
            stock = int(self.product_stock.get()) if self.product_stock.get() else 0
        except ValueError:
            messagebox.showerror("Error", "Prices, GST, and Stock must be valid numbers.")
            return
        
        if not current_barcode:
            final_barcode = generate_unique_barcode()
            self.barcode_entry.delete(0, tk.END)
            self.barcode_entry.insert(0, final_barcode)
        else:
            final_barcode = current_barcode
        
        option = self.price_option.get()
        if option == "with_tax":
            breakdown = calculate_gst_breakdown(selling_price, True, gst_percentage)
            selling_price_with_gst = selling_price
        else:
            breakdown = calculate_gst_breakdown(selling_price, False, gst_percentage)
            selling_price_with_gst = breakdown['price_with_gst']
        
        profit = calculate_profit(purchase_price, selling_price_with_gst)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO products 
            (barcode, name, size, purchase_price_with_gst, selling_price_with_gst,
             price_before_gst, gst_amount, gst_percentage, stock, profit) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                final_barcode, name, size, purchase_price, selling_price_with_gst,
                breakdown['price_before_gst'], breakdown['gst_amount'], gst_percentage,
                stock, profit
            ))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", f"Product '{name}' added successfully!\nProfit: ₹{profit:.2f}")
            self.clear_product_form()
            self.load_products()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product with this barcode already exists!")
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            print(traceback.format_exc())
    
    def update_product(self):
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a product to update.")
            return
        
        item = self.product_tree.item(selection[0])
        product_id = item['values'][0]
        name = self.product_name.get().strip()
        size = self.product_size.get().strip()
        barcode = self.barcode_entry.get().strip()
        
        if not name or not self.selling_price.get() or not self.purchase_price.get():
            messagebox.showwarning("Warning", "Product Name, Retail Price, and Wholesale Price are required.")
            return
        
        try:
            purchase_price = float(self.purchase_price.get())
            selling_price = float(self.selling_price.get())
            gst_percentage = float(self.gst_percentage.get())
            stock = int(self.product_stock.get()) if self.product_stock.get() else 0
        except ValueError:
            messagebox.showerror("Error", "Prices, GST, and Stock must be valid numbers.")
            return
        
        option = self.price_option.get()
        if option == "with_tax":
            breakdown = calculate_gst_breakdown(selling_price, True, gst_percentage)
            selling_price_with_gst = selling_price
        else:
            breakdown = calculate_gst_breakdown(selling_price, False, gst_percentage)
            selling_price_with_gst = breakdown['price_with_gst']
        
        profit = calculate_profit(purchase_price, selling_price_with_gst)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            UPDATE products SET 
                barcode=?, name=?, size=?, purchase_price_with_gst=?, selling_price_with_gst=?,
                price_before_gst=?, gst_amount=?, gst_percentage=?, stock=?,
                profit=?, last_updated=CURRENT_TIMESTAMP 
            WHERE id=?
            ''', (
                barcode, name, size, purchase_price, selling_price_with_gst,
                breakdown['price_before_gst'], breakdown['gst_amount'], gst_percentage,
                stock, profit, product_id
            ))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Product updated successfully!\nProfit: ₹{profit:.2f}")
            self.clear_product_form()
            self.load_products()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product with this barcode already exists!")
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            print(traceback.format_exc())
    
    def delete_product(self):
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a product to delete")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this product?"):
            item = self.product_tree.item(selection[0])
            product_id = item['values'][0]
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE products SET status = "Deleted" WHERE id = ?', (product_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted.")
            self.load_products()
    
    def clear_product_form(self):
        self.product_name.delete(0, tk.END)
        self.product_size.delete(0, tk.END)
        self.purchase_price.delete(0, tk.END)
        self.selling_price.delete(0, tk.END)
        self.barcode_entry.delete(0, tk.END)
        self.gst_percentage.delete(0, tk.END)
        self.gst_percentage.insert(0, "5")
        self.product_stock.delete(0, tk.END)
        self.product_stock.insert(0, "0")
        self.price_option.set("with_tax")
        self.profit_preview_label.config(text="")
        self.update_price_example()
    
    def load_products(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(''' 
        SELECT id, barcode, name, size, purchase_price_with_gst, selling_price_with_gst,
               price_before_gst, gst_amount, profit, stock, status
        FROM products 
        WHERE status = 'Active' 
        ORDER BY name 
        ''')
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
        for row in cursor.fetchall():
            self.product_tree.insert('', 'end', values=row)
        conn.close()
    
    def search_products(self, event=None):
        search_term = self.search_entry.get()
        if not search_term:
            self.load_products()
            return
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(''' 
        SELECT id, barcode, name, size, purchase_price_with_gst, selling_price_with_gst,
               price_before_gst, gst_amount, profit, stock, status
        FROM products 
        WHERE (name LIKE ? OR barcode LIKE ?) AND status = 'Active' 
        ORDER BY name 
        ''', (f'%{search_term}%', f'%{search_term}%'))
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
        for row in cursor.fetchall():
            self.product_tree.insert('', 'end', values=row)
        conn.close()
    
    def on_product_select(self, event):
        selection = self.product_tree.selection()
        if not selection:
            return
        item = self.product_tree.item(selection[0])
        values = item['values']
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (values[0],))
        product = cursor.fetchone()
        if product:
            self.product_name.delete(0, tk.END)
            self.product_name.insert(0, product[2])
            self.product_size.delete(0, tk.END)
            self.product_size.insert(0, product[3])
            self.purchase_price.delete(0, tk.END)
            self.purchase_price.insert(0, product[4])
            self.selling_price.delete(0, tk.END)
            self.selling_price.insert(0, product[5])
            self.barcode_entry.delete(0, tk.END)
            self.barcode_entry.insert(0, product[1])
            self.gst_percentage.delete(0, tk.END)
            self.gst_percentage.insert(0, product[8])
            self.product_stock.delete(0, tk.END)
            self.product_stock.insert(0, product[10])
            self.update_profit_preview()
            if round(product[5], 2) == round(product[6] * (1 + product[8] / 100), 2):
                self.price_option.set("with_tax")
            else:
                self.price_option.set("without_tax")
            self.update_price_example()
        conn.close()
    
    def export_products(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if filename:
            conn = self.db.get_connection()
            df = pd.read_sql_query("SELECT * FROM products WHERE status != 'Deleted'", conn)
            df.to_csv(filename, index=False)
            conn.close()
            messagebox.showinfo("Success", f"Products exported to {filename}")
    
    # =========================================================
    # INVOICE TAB
    # =========================================================
    
    def create_invoice_tab(self):
        self.invoice_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.invoice_frame, text='🧾 Generate Invoice')
        
        left_frame = ttk.LabelFrame(self.invoice_frame, text="Customer & Product Selection", padding=10)
        left_frame.pack(side='left', fill='y', padx=5, pady=5)
        
        # Customer Details
        ttk.Label(left_frame, text="Customer Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.customer_name = ttk.Entry(left_frame, width=30)
        self.customer_name.grid(row=0, column=1, pady=5, padx=5, columnspan=2)
        
        ttk.Label(left_frame, text="Phone Number:").grid(row=1, column=0, sticky='w', pady=5)
        self.customer_phone = ttk.Entry(left_frame, width=30)
        self.customer_phone.grid(row=1, column=1, pady=5, padx=5, columnspan=2)
        
        ttk.Label(left_frame, text="Address:").grid(row=2, column=0, sticky='w', pady=5)
        self.customer_address = tk.Text(left_frame, height=3, width=25, wrap='word')
        self.customer_address.grid(row=2, column=1, pady=5, padx=5, columnspan=2)
        
        ttk.Label(left_frame, text="City/Zip:").grid(row=3, column=0, sticky='w', pady=5)
        self.customer_city = ttk.Entry(left_frame, width=30)
        self.customer_city.grid(row=3, column=1, pady=5, padx=5, columnspan=2)
        
        ttk.Separator(left_frame, orient='horizontal').grid(row=4, column=0, columnspan=3, sticky='ew', pady=10)
        
        # Product Search
        ttk.Label(left_frame, text="Product Search (Barcode/Name):").grid(row=5, column=0, sticky='w', pady=5)
        self.product_search = ttk.Entry(left_frame, width=30)
        self.product_search.grid(row=5, column=1, pady=5, padx=5, columnspan=2)
        self.product_search.bind('<KeyRelease>', self.search_products_for_invoice)
        
        self.search_results_listbox = tk.Listbox(left_frame, height=5, width=40)
        self.search_results_listbox.grid(row=6, column=0, columnspan=3, pady=5, padx=5, sticky='ew')
        self.search_results_listbox.bind('<<ListboxSelect>>', self.on_product_select_for_invoice)
        
        self.selected_product = None
        ttk.Label(left_frame, text="Selected Product:").grid(row=7, column=0, sticky='w', pady=10)
        self.selected_product_label = ttk.Label(left_frame, text="None", foreground="blue")
        self.selected_product_label.grid(row=7, column=1, sticky='w', pady=10, columnspan=2)
        
        ttk.Label(left_frame, text="Enter Size:").grid(row=8, column=0, sticky='w', pady=5)
        self.invoice_size_entry = ttk.Entry(left_frame, width=15)
        self.invoice_size_entry.grid(row=8, column=1, sticky='w', pady=5, padx=5)
        ttk.Label(left_frame, text="(e.g., 6, 7, 8, 41, 42, etc)").grid(row=8, column=2, sticky='w', padx=5)
        
        ttk.Label(left_frame, text="Quantity:").grid(row=9, column=0, sticky='w', pady=5)
        self.product_quantity = ttk.Spinbox(left_frame, from_=1, to=100, width=10)
        self.product_quantity.grid(row=9, column=1, sticky='w', pady=5, padx=5)
        self.product_quantity.set(1)
        
        ttk.Button(left_frame, text="Add to Invoice", command=self.add_product_to_invoice).grid(row=10, column=1, sticky='w', pady=10, padx=5)
        
        # Discount Section
        ttk.Label(left_frame, text="Discount Type:").grid(row=11, column=0, sticky='w', pady=10)
        self.discount_type = ttk.Combobox(left_frame, values=["None", "Fixed Amount", "Percentage"], width=15)
        self.discount_type.grid(row=11, column=1, sticky='w', pady=10, padx=5)
        self.discount_type.set("None")
        self.discount_type.bind('<<ComboboxSelected>>', self.toggle_discount_fields)
        
        self.discount_frame = ttk.Frame(left_frame)
        self.discount_frame.grid(row=12, column=0, columnspan=3, sticky='w', padx=5)
        self.discount_value = None
        
        ttk.Separator(left_frame, orient='horizontal').grid(row=13, column=0, columnspan=3, sticky='ew', pady=10)
        
        # Payment Method
        ttk.Label(left_frame, text="Payment Method:").grid(row=14, column=0, sticky='w', pady=5)
        self.payment_method = ttk.Combobox(left_frame, values=["Cash", "Card", "UPI/Wallet", "Bank Transfer"], width=15)
        self.payment_method.grid(row=14, column=1, sticky='w', pady=5, padx=5)
        self.payment_method.set("Cash")
        
        # Buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=15, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="Generate Invoice", command=self.generate_invoice).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Clear Invoice", command=self.clear_invoice).pack(side='left', padx=10)
        
        # Right Frame: Invoice Items & Summary
        right_frame = ttk.LabelFrame(self.invoice_frame, text="Invoice Items & Summary", padding=10)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        columns = ('Barcode', 'Name', 'Size', 'Qty', 'Unit Price', 'Total (with GST)')
        self.invoice_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=10)
        for col in columns:
            self.invoice_tree.heading(col, text=col)
            self.invoice_tree.column(col, width=100)
        self.invoice_tree.column('Name', width=150)
        self.invoice_tree.column('Unit Price', width=100)
        self.invoice_tree.pack(fill='x', pady=5)
        self.invoice_tree.bind('<Delete>', self.remove_item_from_invoice_event)
        
        ttk.Button(right_frame, text="Remove Selected Item (or press Delete)", command=self.remove_item_from_invoice).pack(pady=5)
        
        ttk.Label(right_frame, text="Invoice Summary:").pack(anchor='w', pady=10)
        self.summary_text = ScrolledText(right_frame, height=15, width=60, wrap='word')
        self.summary_text.pack(fill='both', expand=True)
        
        self.invoice_items = []
        self.search_results = []
    
    # --- Invoice Helper Methods ---
    def search_products_for_invoice(self, event=None):
        search_term = self.product_search.get().strip()
        self.search_results_listbox.delete(0, tk.END)
        self.search_results = []
        if not search_term:
            return
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(''' 
        SELECT id, barcode, name, size, purchase_price_with_gst, selling_price_with_gst, gst_percentage
        FROM products 
        WHERE (name LIKE ? OR barcode LIKE ?) AND status = 'Active' 
        ORDER BY name 
        ''', (f'%{search_term}%', f'%{search_term}%'))
        for row in cursor.fetchall():
            self.search_results.append(row)
            self.search_results_listbox.insert(tk.END, f"{row[2]} (Size: {row[3]}, Barcode: {row[1]})")
        conn.close()
    
    def on_product_select_for_invoice(self, event):
        selection = self.search_results_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self.search_results):
            product = self.search_results[index]
            self.selected_product = product
            self.selected_product_label.config(text=f"{product[2]} (Barcode: {product[1]})")
            self.invoice_size_entry.delete(0, tk.END)
            self.invoice_size_entry.insert(0, product[3])
    
    def toggle_discount_fields(self, event=None):
        for widget in self.discount_frame.winfo_children():
            widget.destroy()
        self.discount_value = None
        discount_type = self.discount_type.get()
        if discount_type == "Fixed Amount":
            ttk.Label(self.discount_frame, text="Discount Amount (₹):").pack(side='left', padx=5)
            self.discount_value = ttk.Entry(self.discount_frame, width=15)
            self.discount_value.pack(side='left', padx=5)
        elif discount_type == "Percentage":
            ttk.Label(self.discount_frame, text="Discount (%):").pack(side='left', padx=5)
            self.discount_value = ttk.Entry(self.discount_frame, width=15)
            self.discount_value.pack(side='left', padx=5)
        if self.discount_value:
            self.discount_value.bind('<KeyRelease>', lambda e: self.update_invoice_summary())
        self.update_invoice_summary()
    
    def add_product_to_invoice(self):
        if not hasattr(self, 'selected_product') or not self.selected_product:
            messagebox.showwarning("Warning", "Please select a product first")
            return
        try:
            quantity = int(self.product_quantity.get())
            if quantity <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid quantity (> 0)")
            return
        
        size = self.invoice_size_entry.get().strip()
        if not size:
            size = self.selected_product[3]
        
        product_id = self.selected_product[0]
        barcode = self.selected_product[1]
        product_name = self.selected_product[2]
        purchase_price = self.selected_product[4]
        selling_price_with_gst = self.selected_product[5]
        gst_percentage = self.selected_product[6]
        
        breakdown = calculate_gst_breakdown(selling_price_with_gst, price_includes_gst=True, gst_percentage=gst_percentage)
        unit_price_without_gst = breakdown['price_before_gst']
        unit_gst = breakdown['gst_amount']
        
        total_price_without_gst = round(unit_price_without_gst * quantity, 2)
        total_gst = round(unit_gst * quantity, 2)
        total_with_gst = round(selling_price_with_gst * quantity, 2)
        profit = calculate_profit(purchase_price, selling_price_with_gst) * quantity
        
        item = {
            'product_id': product_id,
            'barcode': barcode,
            'name': product_name,
            'size': size,
            'quantity': quantity,
            'purchase_price': purchase_price,
            'unit_price_without_gst': unit_price_without_gst,
            'unit_gst': unit_gst,
            'unit_price_with_gst': selling_price_with_gst,
            'total_price': total_price_without_gst,
            'total_gst': total_gst,
            'total_with_gst': total_with_gst,
            'profit': profit
        }
        
        self.invoice_items.append(item)
        self.invoice_tree.insert('', 'end', values=(
            barcode, product_name, size, quantity,
            f"₹{unit_price_without_gst:,.2f}", f"₹{total_with_gst:,.2f}"
        ))
        self.update_invoice_summary()
    
    def remove_item_from_invoice_event(self, event):
        self.remove_item_from_invoice()
    
    def remove_item_from_invoice(self):
        selection = self.invoice_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to remove.")
            return
        index = self.invoice_tree.index(selection[0])
        self.invoice_tree.delete(selection[0])
        if 0 <= index < len(self.invoice_items):
            self.invoice_items.pop(index)
        self.update_invoice_summary()
    
    def update_invoice_summary(self):
        for item in self.invoice_tree.get_children():
            self.invoice_tree.delete(item)
        for item in self.invoice_items:
            self.invoice_tree.insert('', 'end', values=(
                item['barcode'], item['name'], item['size'],
                item['quantity'], f"₹{item['unit_price_without_gst']:,.2f}",
                f"₹{item['total_with_gst']:,.2f}"
            ))
        if not self.invoice_items:
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(1.0, "No items in invoice")
            return
        
        subtotal = sum(item['total_price'] for item in self.invoice_items)
        total_gst = sum(item['total_gst'] for item in self.invoice_items)
        total_with_gst = sum(item['total_with_gst'] for item in self.invoice_items)
        total_purchase_cost = sum(item['purchase_price'] * item['quantity'] for item in self.invoice_items)
        total_profit = sum(item['profit'] for item in self.invoice_items)
        
        discount_amount = 0
        discount_percentage = 0
        if hasattr(self, 'discount_value') and self.discount_value and self.discount_value.winfo_exists() and self.discount_value.get():
            try:
                discount_type = self.discount_type.get()
                discount_val = float(self.discount_value.get())
                if discount_type == "Fixed Amount":
                    discount_amount = min(discount_val, total_with_gst)
                elif discount_type == "Percentage":
                    discount_percentage = discount_val
                    discount_amount = total_with_gst * (discount_percentage / 100)
                    discount_amount = min(discount_amount, total_with_gst)
            except ValueError:
                discount_amount = 0
        
        final_total = total_with_gst - discount_amount
        final_calculated_profit = round(total_profit - discount_amount, 2)
        
        summary = f"""
INVOICE SUMMARY
{'-' * 60}
Number of Items: {len(self.invoice_items)}
Subtotal (without GST): ₹{subtotal:,.2f}
GST Amount (5%): ₹{total_gst:,.2f}
Subtotal (with GST): ₹{total_with_gst:,.2f}
{'-' * 60}
Discount Given ({discount_percentage:.1f}%): - ₹{discount_amount:,.2f}
FINAL TOTAL: ₹{final_total:,.2f}
{'-' * 60}
Payment Method: {self.payment_method.get()}
Total Profit on this Invoice: ₹{final_calculated_profit:,.2f}
Wholesale Cost: ₹{total_purchase_cost:,.2f}
"""
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, summary)
    
    def generate_invoice(self):
        if not self.invoice_items:
            messagebox.showwarning("Warning", "Invoice is empty. Please add products.")
            return
        if not self.customer_name.get().strip():
            messagebox.showwarning("Warning", "Please enter Customer Name.")
            return
        
        subtotal = sum(item['total_price'] for item in self.invoice_items)
        total_gst = sum(item['total_gst'] for item in self.invoice_items)
        total_with_gst = sum(item['total_with_gst'] for item in self.invoice_items)
        total_profit_before_discount = sum(item['profit'] for item in self.invoice_items)
        
        discount_amount = 0
        discount_percentage = 0
        if hasattr(self, 'discount_value') and self.discount_value and self.discount_value.winfo_exists() and self.discount_value.get():
            try:
                discount_type = self.discount_type.get()
                discount_val = float(self.discount_value.get())
                if discount_type == "Fixed Amount":
                    discount_amount = min(discount_val, total_with_gst)
                elif discount_type == "Percentage":
                    discount_percentage = discount_val
                    discount_amount = total_with_gst * (discount_percentage / 100)
                    discount_amount = min(discount_amount, total_with_gst)
            except ValueError:
                discount_amount = 0
        
        final_total = total_with_gst - discount_amount
        final_calculated_profit = round(total_profit_before_discount - discount_amount, 2)
        
        try:
            invoice_number = generate_invoice_number()
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            customer_address = self.customer_address.get("1.0", tk.END).strip()
            
            cursor.execute('''
            INSERT INTO invoices (invoice_number, customer_name, customer_phone, customer_address,
                                 customer_city, subtotal, tax_amount, discount_amount,
                                 discount_percentage, total_amount, payment_method, total_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_number, self.customer_name.get(), self.customer_phone.get(),
                customer_address, self.customer_city.get(),
                subtotal, total_gst, discount_amount, discount_percentage,
                final_total, self.payment_method.get(), final_calculated_profit
            ))
            invoice_id = cursor.lastrowid
            
            for item in self.invoice_items:
                cursor.execute('''
                INSERT INTO invoice_items (invoice_id, product_id, barcode, product_name, size, quantity,
                                         unit_price, unit_gst, unit_price_with_gst, total_price,
                                         total_gst, total_with_gst, purchase_price, profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    invoice_id, item['product_id'], item['barcode'], item['name'], item['size'],
                    item['quantity'], item['unit_price_without_gst'], item['unit_gst'],
                    item['unit_price_with_gst'], item['total_price'], item['total_gst'],
                    item['total_with_gst'], item['purchase_price'], item['profit']
                ))
            
            conn.commit()
            conn.close()
            
            # Update stock
            conn = self.db.get_connection()
            cursor = conn.cursor()
            for item in self.invoice_items:
                cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['product_id']))
            conn.commit()
            conn.close()
            
            # Generate PDF
            invoice_data = {
                'invoice_number': invoice_number,
                'date': datetime.now().strftime("%d/%m/%Y"),
                'customer_name': self.customer_name.get(),
                'customer_phone': self.customer_phone.get(),
                'customer_address': customer_address,
                'customer_city': self.customer_city.get()
            }
            pdf_items = []
            for item in self.invoice_items:
                pdf_items.append({
                    'name': item['name'],
                    'size': item['size'],
                    'quantity': item['quantity'],
                    'unit_price_without_tax': item['unit_price_without_gst'],
                    'unit_price_with_tax': item['unit_price_with_gst']
                })
            pdf_filename = f"Invoice_{invoice_number}.pdf"
            create_invoice_pdf(
                invoice_data, pdf_items, subtotal, total_gst, discount_amount,
                discount_percentage, final_total, pdf_filename
            )
            
            self.update_profit_report(total_with_gst, final_calculated_profit, total_gst, discount_amount)
            
            messagebox.showinfo("Success", f"Invoice {invoice_number} created successfully!\n\n"
                                f"Customer: {self.customer_name.get()}\n"
                                f"Total Amount: ₹{final_total:,.2f}")
            
            self.clear_invoice()
            self.load_invoices()
            
            if os.path.exists(f"invoices_pdf/{pdf_filename}"):
                try:
                    subprocess.Popen(['start', f"invoices_pdf/{pdf_filename}"], shell=True)
                except:
                    try:
                        webbrowser.open(f"invoices_pdf/{pdf_filename}")
                    except:
                        pass
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during invoice generation: {str(e)}")
            print(traceback.format_exc())
    
    def update_profit_report(self, total_sales_with_gst, total_profit, total_gst, total_discount_given):
        today = datetime.now().strftime("%Y-%m-%d")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        total_purchases = 0
        for item in self.invoice_items:
            total_purchases += (item['purchase_price'] * item['quantity'])
        
        cursor.execute('SELECT id, total_sales_with_gst, total_purchases, total_profit, total_gst_collected, total_discount_given, number_of_invoices FROM profit_report WHERE report_date = ?', (today,))
        existing_report = cursor.fetchone()
        
        if existing_report:
            new_sales = existing_report[1] + total_sales_with_gst
            new_purchases = existing_report[2] + total_purchases
            new_profit = existing_report[3] + total_profit
            new_gst = existing_report[4] + total_gst
            new_discount = existing_report[5] + total_discount_given
            new_invoices = existing_report[6] + 1
            cursor.execute('''
                UPDATE profit_report SET 
                    total_sales_with_gst = ?, total_purchases = ?, total_profit = ?,
                    total_gst_collected = ?, total_discount_given = ?, number_of_invoices = ?
                WHERE report_date = ?
            ''', (new_sales, new_purchases, new_profit, new_gst, new_discount, new_invoices, today))
        else:
            cursor.execute('''
                INSERT INTO profit_report (report_date, total_sales_with_gst, total_purchases, total_profit, total_gst_collected, total_discount_given, number_of_invoices)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (today, total_sales_with_gst, total_purchases, total_profit, total_gst, total_discount_given, 1))
        
        conn.commit()
        conn.close()
    
    def clear_invoice(self):
        for item in self.invoice_tree.get_children():
            self.invoice_tree.delete(item)
        self.customer_name.delete(0, tk.END)
        self.customer_phone.delete(0, tk.END)
        self.customer_address.delete("1.0", tk.END)
        self.customer_city.delete(0, tk.END)
        if hasattr(self, 'product_search'):
            self.product_search.delete(0, tk.END)
        if hasattr(self, 'search_results_listbox'):
            self.search_results_listbox.delete(0, tk.END)
        if hasattr(self, 'selected_product_label'):
            self.selected_product_label.config(text="None")
        if hasattr(self, 'invoice_size_entry'):
            self.invoice_size_entry.delete(0, tk.END)
        if hasattr(self, 'product_quantity'):
            self.product_quantity.set(1)
        self.selected_product = None
        self.discount_type.set("None")
        if hasattr(self, 'discount_value') and self.discount_value:
            if self.discount_value.winfo_exists():
                self.discount_value.destroy()
        self.payment_method.set("Cash")
        self.summary_text.delete(1.0, tk.END)
        self.invoice_items = []
        if hasattr(self, 'discount_frame'):
            for widget in self.discount_frame.winfo_children():
                widget.destroy()
    
    # =========================================================
    # INVOICE HISTORY TAB
    # =========================================================
    
    def create_invoice_history_tab(self):
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text='📜 Invoice History')
        
        search_frame = ttk.Frame(self.history_frame, padding=10)
        search_frame.pack(fill='x')
        ttk.Label(search_frame, text="Search Invoices:").pack(side='left', padx=5)
        self.invoice_search = ttk.Entry(search_frame, width=30)
        self.invoice_search.pack(side='left', padx=5)
        self.invoice_search.bind('<KeyRelease>', self.search_invoices)
        ttk.Button(search_frame, text="Load All", command=self.load_invoices).pack(side='left', padx=5)
        
        main_content_frame = ttk.Frame(self.history_frame, padding=10)
        main_content_frame.pack(fill='both', expand=True)
        
        list_frame = ttk.LabelFrame(main_content_frame, text="Invoices", padding=10)
        list_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        columns = ('Invoice #', 'Date', 'Customer', 'Phone', 'Subtotal', 'Tax', 'Discount', 'Total', 'Profit', 'Status')
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        col_widths = [100, 120, 120, 100, 90, 70, 90, 90, 90, 80]
        for i, col in enumerate(columns):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=col_widths[i])
        self.history_tree.pack(fill='both', expand=True, pady=10)
        self.history_tree.bind('<<TreeviewSelect>>', self.show_invoice_details)
        
        details_frame = ttk.LabelFrame(main_content_frame, text="Details & Actions", padding=10)
        details_frame.pack(side='right', fill='both', padx=5, pady=5)
        ttk.Label(details_frame, text="Invoice Details:").pack(anchor='w')
        self.details_text = ScrolledText(details_frame, height=20, width=50, wrap='word')
        self.details_text.pack(fill='both', expand=True, pady=5)
        
        action_button_frame = ttk.Frame(details_frame)
        action_button_frame.pack(fill='x', pady=10)
        ttk.Button(action_button_frame, text="View PDF", command=self.view_invoice_pdf).pack(side='left', padx=5)
        ttk.Button(action_button_frame, text="Delete Invoice (Cancel)", command=self.delete_invoice).pack(side='left', padx=5)
        ttk.Button(action_button_frame, text="Export to Excel", command=self.export_invoices).pack(side='right', padx=5)
        
        self.load_invoices()
    
    def load_invoices(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT invoice_number, invoice_date, customer_name, customer_phone,
               subtotal, tax_amount, discount_amount, total_amount, total_profit, status
        FROM invoices
        WHERE status = 'Active'
        ORDER BY invoice_date DESC
        ''')
        for row in cursor.fetchall():
            self.history_tree.insert('', 'end', values=(
                row[0], row[1][:19] if row[1] else '', row[2], row[3],
                f"₹{row[4]:,.2f}", f"₹{row[5]:,.2f}", f"₹{row[6]:,.2f}",
                f"₹{row[7]:,.2f}", f"₹{row[8]:,.2f}", row[9]
            ))
        conn.close()
    
    def search_invoices(self, event=None):
        search_term = self.invoice_search.get()
        if not search_term:
            self.load_invoices()
            return
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT invoice_number, invoice_date, customer_name, customer_phone,
               subtotal, tax_amount, discount_amount, total_amount, total_profit, status
        FROM invoices
        WHERE (customer_name LIKE ? OR invoice_number LIKE ?) AND status = 'Active'
        ORDER BY invoice_date DESC
        ''', (f'%{search_term}%', f'%{search_term}%'))
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for row in cursor.fetchall():
            self.history_tree.insert('', 'end', values=(
                row[0], row[1][:19] if row[1] else '', row[2], row[3],
                f"₹{row[4]:,.2f}", f"₹{row[5]:,.2f}", f"₹{row[6]:,.2f}",
                f"₹{row[7]:,.2f}", f"₹{row[8]:,.2f}", row[9]
            ))
        conn.close()
    
    def show_invoice_details(self, event):
        selection = self.history_tree.selection()
        if not selection:
            return
        item = self.history_tree.item(selection[0])
        invoice_number = item['values'][0]
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM invoices WHERE invoice_number = ? AND status = "Active"', (invoice_number,))
        invoice = cursor.fetchone()
        if not invoice:
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(1.0, "Invoice not found or deleted.")
            conn.close()
            return
        
        cursor.execute('''
        SELECT product_name, size, quantity, unit_price, unit_gst, total_price, total_gst, total_with_gst, profit
        FROM invoice_items
        WHERE invoice_id = ? AND status = "Active"
        ''', (invoice[0],))
        items = cursor.fetchall()
        conn.close()
        
        details = f"""
INVOICE NUMBER: {invoice[1]}
DATE: {invoice[11].split('.')[0]}
PAYMENT: {invoice[12]}
{'-'*40}
CUSTOMER: {invoice[2]}
PHONE: {invoice[3]}
ADDRESS: {invoice[4]}, {invoice[5]}
{'-'*40}
ITEMS (Name | Size | Qty | Price Excl. GST | Total Incl. GST)
{'-'*40}
"""
        total_items = 0
        for item_row in items:
            details += f"{item_row[0]} | {item_row[1]} | {item_row[2]} | ₹{item_row[3]:,.2f} | ₹{item_row[7]:,.2f}\n"
            total_items += item_row[2]
        details += f"""
{'-'*40}
Subtotal (Excl. GST): ₹{invoice[6]:,.2f}
Tax Amount (5%): ₹{invoice[7]:,.2f}
Discount: - ₹{invoice[8]:,.2f} ({invoice[9]}%)
{'-'*40}
FINAL AMOUNT: ₹{invoice[10]:,.2f}
TOTAL PROFIT: ₹{invoice[13]:,.2f}
TOTAL ITEMS: {total_items}
SOURCE: Local Database
"""
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)
    
    def view_invoice_pdf(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an invoice to view its PDF.")
            return
        item = self.history_tree.item(selection[0])
        invoice_number = item['values'][0]
        pdf_path = f"invoices_pdf/Invoice_{invoice_number}.pdf"
        if os.path.exists(pdf_path):
            try:
                subprocess.Popen(['start', pdf_path], shell=True)
            except:
                try:
                    webbrowser.open(pdf_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open PDF file. Error: {e}")
        else:
            messagebox.showerror("Error", f"PDF file not found for Invoice {invoice_number}.")
    
    def delete_invoice(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an invoice to delete/cancel.")
            return
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to CANCEL this invoice? This action is recorded and impacts the Profit Report."):
            return
        
        item = self.history_tree.item(selection[0])
        invoice_number = item['values'][0]
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id, subtotal, tax_amount, discount_amount, discount_percentage, total_amount, total_profit, invoice_date FROM invoices WHERE invoice_number = ? AND status = "Active"', (invoice_number,))
            invoice_data = cursor.fetchone()
            if invoice_data:
                invoice_id = invoice_data[0]
                subtotal = invoice_data[1]
                tax_amount = invoice_data[2]
                discount_amount = invoice_data[3]
                discount_percentage = invoice_data[4]
                total_amount = invoice_data[5]
                total_profit = invoice_data[6]
                invoice_date = invoice_data[7]
                if ' ' in str(invoice_date):
                    invoice_date = str(invoice_date).split(' ')[0]
                
                cursor.execute('''
                    SELECT SUM(total_with_gst) as total_sales_with_gst,
                           SUM(purchase_price * quantity) as total_purchases
                    FROM invoice_items
                    WHERE invoice_id = ? AND status = 'Active'
                ''', (invoice_id,))
                totals = cursor.fetchone()
                total_sales_with_gst = totals[0] if totals and totals[0] else 0
                total_purchases = totals[1] if totals and totals[1] else 0
                
                cursor.execute('UPDATE invoices SET status = "Deleted" WHERE invoice_number = ?', (invoice_number,))
                cursor.execute('UPDATE invoice_items SET status = "Deleted" WHERE invoice_id = ?', (invoice_id,))
                
                cursor.execute('SELECT id, total_sales_with_gst, total_purchases, total_profit, total_gst_collected, total_discount_given, number_of_invoices FROM profit_report WHERE report_date = ?', (invoice_date,))
                profit_report = cursor.fetchone()
                if profit_report:
                    new_sales = max(0, profit_report[1] - total_sales_with_gst)
                    new_purchases = max(0, profit_report[2] - total_purchases)
                    new_profit = max(0, profit_report[3] - total_profit)
                    new_gst = max(0, profit_report[4] - tax_amount)
                    new_discount = max(0, profit_report[5] - discount_amount)
                    new_invoices = max(0, profit_report[6] - 1)
                    cursor.execute('''
                        UPDATE profit_report SET
                            total_sales_with_gst = ?, total_purchases = ?, total_profit = ?,
                            total_gst_collected = ?, total_discount_given = ?, number_of_invoices = ?
                        WHERE report_date = ?
                    ''', (new_sales, new_purchases, new_profit, new_gst, new_discount, new_invoices, invoice_date))
                    if new_sales == 0 and new_purchases == 0 and new_profit == 0 and new_gst == 0 and new_discount == 0 and new_invoices == 0:
                        cursor.execute('DELETE FROM profit_report WHERE report_date = ?', (invoice_date,))
            
            conn.commit()
            conn.close()
            
            delete_invoice_files(invoice_number)
            self.load_invoices()
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(1.0, f"Invoice {invoice_number} has been CANCELLED successfully.\nProfit report updated.")
            messagebox.showinfo("Success", f"Invoice {invoice_number} CANCELLED successfully!")
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during deletion: {str(e)}")
            print(traceback.format_exc())
            conn.close()
    
    def export_invoices(self):
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if filename:
            conn = self.db.get_connection()
            try:
                invoices_df = pd.read_sql_query("SELECT * FROM invoices WHERE status != 'Deleted'", conn)
                items_df = pd.read_sql_query("SELECT * FROM invoice_items WHERE status != 'Deleted'", conn)
                with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                    invoices_df.to_excel(writer, sheet_name='Invoices', index=False)
                    items_df.to_excel(writer, sheet_name='Invoice_Items', index=False)
                messagebox.showinfo("Success", f"Invoices exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during export: {str(e)}")
            finally:
                conn.close()
    
    # =========================================================
    # PROFIT & LOSS REPORT TAB
    # =========================================================
    
    def create_profit_report_tab(self):
        self.report_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.report_frame, text='💰 Profit & Loss Report')
        
        report_type_frame = ttk.LabelFrame(self.report_frame, text="Report Type", padding=10)
        report_type_frame.pack(fill='x', padx=10, pady=10)
        self.report_type = tk.StringVar(value="daily")
        ttk.Radiobutton(report_type_frame, text="Daily Report", variable=self.report_type, value="daily").pack(side='left', padx=20)
        ttk.Radiobutton(report_type_frame, text="Monthly Report", variable=self.report_type, value="monthly").pack(side='left', padx=20)
        ttk.Radiobutton(report_type_frame, text="Date Range", variable=self.report_type, value="range").pack(side='left', padx=20)
        ttk.Radiobutton(report_type_frame, text="Product-wise Profit", variable=self.report_type, value="product").pack(side='left', padx=20)
        
        date_frame = ttk.Frame(self.report_frame, padding=10)
        date_frame.pack(fill='x', padx=10)
        ttk.Label(date_frame, text="Date (YYYY-MM-DD):").pack(side='left', padx=5)
        self.report_date = ttk.Entry(date_frame, width=12)
        self.report_date.pack(side='left', padx=5)
        self.report_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        self.range_frame = ttk.Frame(self.report_frame, padding=10)
        ttk.Label(self.range_frame, text="From:").pack(side='left', padx=5)
        self.range_from = ttk.Entry(self.range_frame, width=12)
        self.range_from.pack(side='left', padx=5)
        ttk.Label(self.range_frame, text="To:").pack(side='left', padx=5)
        self.range_to = ttk.Entry(self.range_frame, width=12)
        self.range_to.pack(side='left', padx=5)
        self.range_to.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        button_frame = ttk.Frame(self.report_frame, padding=10)
        button_frame.pack(fill='x', padx=10)
        ttk.Button(button_frame, text="Generate Report", command=self.generate_profit_report).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Export Report", command=self.export_profit_report).pack(side='left', padx=5)
        
        self.report_text = ScrolledText(self.report_frame, height=20, width=100, wrap='word')
        self.report_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def generate_profit_report(self):
        report_type = self.report_type.get()
        conn = self.db.get_connection()
        report_content = ""
        try:
            if report_type == "daily":
                date = self.report_date.get()
                cursor = conn.cursor()
                cursor.execute('''
                SELECT total_sales_with_gst, total_purchases, total_profit, total_gst_collected, total_discount_given, number_of_invoices
                FROM profit_report
                WHERE report_date = ?
                ''', (date,))
                result = cursor.fetchone()
                if result:
                    report_content = f"""
DAILY PROFIT & LOSS REPORT - {date}
{'='*70}
Total Invoices: {result[5]}
Total Sales (with GST): ₹{result[0]:,.2f}
Total Wholesale Cost: ₹{result[1]:,.2f}
Total GST Collected: ₹{result[3]:,.2f}
Total Discount Given: ₹{result[4]:,.2f}
{'='*70}
TOTAL PROFIT: ₹{result[2]:,.2f}
PROFIT MARGIN: {(result[2]/result[0]*100 if result[0]>0 else 0):.1f}%
"""
                else:
                    report_content = f"No profit data found for date: {date}"
            
            elif report_type == "monthly":
                date_str = self.report_date.get()
                if len(date_str) < 7:
                    messagebox.showerror("Error", "Please enter a valid date in YYYY-MM-DD format to determine the month.")
                    return
                month = date_str[:7]
                cursor = conn.cursor()
                cursor.execute('''
                SELECT strftime('%Y-%m', report_date) as month,
                       SUM(total_sales_with_gst) as total_sales,
                       SUM(total_purchases) as total_purchases,
                       SUM(total_profit) as total_profit,
                       SUM(total_gst_collected) as total_gst,
                       SUM(total_discount_given) as total_discount,
                       SUM(number_of_invoices) as total_invoices
                FROM profit_report
                WHERE strftime('%Y-%m', report_date) = ?
                GROUP BY strftime('%Y-%m', report_date)
                ''', (month,))
                result = cursor.fetchone()
                if result:
                    report_content = f"""
MONTHLY PROFIT & LOSS REPORT - {month}
{'='*70}
Total Invoices: {result[6]}
Total Sales (with GST): ₹{result[1]:,.2f}
Total Wholesale Cost: ₹{result[2]:,.2f}
Total GST Collected: ₹{result[4]:,.2f}
Total Discount Given: ₹{result[5]:,.2f}
{'='*70}
TOTAL PROFIT: ₹{result[3]:,.2f}
PROFIT MARGIN: {(result[3]/result[1]*100 if result[1]>0 else 0):.1f}%

DAILY BREAKDOWN:
{'='*70}
"""
                    cursor.execute('''
                    SELECT report_date, total_sales_with_gst, total_profit, number_of_invoices
                    FROM profit_report
                    WHERE strftime('%Y-%m', report_date) = ?
                    ORDER BY report_date
                    ''', (month,))
                    for day_row in cursor.fetchall():
                        report_content += f"{day_row[0]}: Sales ₹{day_row[1]:,.2f} | Profit ₹{day_row[2]:,.2f} | Invoices {day_row[3]}\n"
                else:
                    report_content = f"No profit data found for month: {month}"
            
            elif report_type == "range":
                date_from = self.range_from.get()
                date_to = self.range_to.get()
                cursor = conn.cursor()
                cursor.execute('''
                SELECT SUM(total_sales_with_gst), SUM(total_purchases), SUM(total_profit), SUM(total_gst_collected), SUM(total_discount_given), SUM(number_of_invoices)
                FROM profit_report
                WHERE report_date BETWEEN ? AND ?
                ''', (date_from, date_to))
                result = cursor.fetchone()
                if result and result[0] is not None:
                    total_sales = result[0]
                    total_purchases = result[1]
                    total_profit = result[2]
                    total_gst = result[3]
                    total_discount = result[4]
                    total_invoices = result[5]
                    report_content = f"""
PROFIT & LOSS REPORT - DATE RANGE: {date_from} to {date_to}
{'='*70}
Total Invoices: {total_invoices}
Total Sales (with GST): ₹{total_sales:,.2f}
Total Wholesale Cost: ₹{total_purchases:,.2f}
Total GST Collected: ₹{total_gst:,.2f}
Total Discount Given: ₹{total_discount:,.2f}
{'='*70}
TOTAL PROFIT: ₹{total_profit:,.2f}
PROFIT MARGIN: {(total_profit/total_sales*100 if total_sales>0 else 0):.1f}%
"""
                else:
                    report_content = f"No profit data found in range: {date_from} to {date_to}"
            
            elif report_type == "product":
                cursor = conn.cursor()
                # Get product-level data
                cursor.execute('''
                SELECT 
                    p.id,
                    p.name,
                    p.size,
                    SUM(ii.quantity) as total_qty,
                    SUM(ii.total_with_gst) as total_sales,
                    SUM(ii.purchase_price * ii.quantity) as total_cost,
                    SUM(ii.profit) as total_profit_before_discount
                FROM invoice_items ii
                JOIN products p ON ii.product_id = p.id
                WHERE ii.status = 'Active'
                GROUP BY p.id, p.size
                HAVING total_qty > 0
                ''')
                product_data = cursor.fetchall()
                
                # Get invoice discount info, but also pre-discount total per invoice
                cursor.execute('''
                SELECT 
                    ii.product_id,
                    ii.total_with_gst,
                    i.discount_amount,
                    i.id as invoice_id
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_id = i.id
                WHERE ii.status = 'Active' AND i.status = 'Active'
                ''')
                invoice_items_data = cursor.fetchall()
                
                # Compute pre-discount total per invoice
                invoice_pre_total = {}
                for prod_id, item_total, disc, inv_id in invoice_items_data:
                    invoice_pre_total[inv_id] = invoice_pre_total.get(inv_id, 0) + item_total
                
                # Allocate discount proportionally using pre-discount total
                product_discount = {}
                for prod_id, item_total, disc, inv_id in invoice_items_data:
                    if disc > 0 and invoice_pre_total[inv_id] > 0:
                        allocated = (item_total / invoice_pre_total[inv_id]) * disc
                    else:
                        allocated = 0
                    product_discount[prod_id] = product_discount.get(prod_id, 0) + allocated
                
                # Build report
                report_content = f"""
PRODUCT-WISE PROFIT REPORT (with discount allocated)
{'='*70}
| {'Product Name':<25} | {'Size':<5} | {'Qty Sold':<8} | {'Total Sales':<12} | {'Total Cost':<10} | {'Profit (after disc)':<15} |
{'-'*90}
"""
                total_all_profit = 0
                for row in product_data:
                    prod_id = row[0]
                    name = row[1]
                    size = row[2]
                    qty = row[3]
                    sales = row[4]
                    cost = row[5]
                    profit_before = row[6]
                    allocated_discount = product_discount.get(prod_id, 0)
                    profit_after = profit_before - allocated_discount
                    total_all_profit += profit_after
                    report_content += f"| {name[:25]:<25} | {size:<5} | {qty:<8} | ₹{sales:<10,.2f} | ₹{cost:<8,.2f} | ₹{profit_after:<13,.2f} |\n"
                report_content += f"{'-'*90}\n"
                report_content += f"TOTAL PROFIT AFTER DISCOUNT: ₹{total_all_profit:,.2f}\n"
        
        except Exception as e:
            report_content = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
        finally:
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, report_content)
            conn.close()
    
    def export_profit_report(self):
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if filename:
            report_type = self.report_type.get()
            conn = self.db.get_connection()
            try:
                if report_type in ["daily", "monthly", "range"]:
                    if report_type == "daily":
                        date = self.report_date.get()
                        query = f"SELECT * FROM profit_report WHERE report_date = '{date}'"
                    elif report_type == "monthly":
                        date_str = self.report_date.get()
                        month = date_str[:7]
                        query = f"SELECT * FROM profit_report WHERE strftime('%Y-%m', report_date) = '{month}'"
                    else:
                        date_from = self.range_from.get()
                        date_to = self.range_to.get()
                        query = f"SELECT * FROM profit_report WHERE report_date BETWEEN '{date_from}' AND '{date_to}'"
                    df = pd.read_sql_query(query, conn)
                    df.to_excel(filename, index=False)
                elif report_type == "product":
                    cursor = conn.cursor()
                    cursor.execute('''
                    SELECT 
                        p.id,
                        p.name,
                        p.size,
                        SUM(ii.quantity) as total_qty,
                        SUM(ii.total_with_gst) as total_sales,
                        SUM(ii.purchase_price * ii.quantity) as total_cost,
                        SUM(ii.profit) as total_profit_before_discount
                    FROM invoice_items ii
                    JOIN products p ON ii.product_id = p.id
                    WHERE ii.status = 'Active'
                    GROUP BY p.id, p.size
                    HAVING total_qty > 0
                    ''')
                    product_data = cursor.fetchall()
                    
                    cursor.execute('''
                    SELECT 
                        ii.product_id,
                        ii.total_with_gst,
                        i.discount_amount,
                        i.id as invoice_id
                    FROM invoice_items ii
                    JOIN invoices i ON ii.invoice_id = i.id
                    WHERE ii.status = 'Active' AND i.status = 'Active'
                    ''')
                    invoice_items_data = cursor.fetchall()
                    
                    invoice_pre_total = {}
                    for prod_id, item_total, disc, inv_id in invoice_items_data:
                        invoice_pre_total[inv_id] = invoice_pre_total.get(inv_id, 0) + item_total
                    
                    product_discount = {}
                    for prod_id, item_total, disc, inv_id in invoice_items_data:
                        if disc > 0 and invoice_pre_total[inv_id] > 0:
                            allocated = (item_total / invoice_pre_total[inv_id]) * disc
                        else:
                            allocated = 0
                        product_discount[prod_id] = product_discount.get(prod_id, 0) + allocated
                    
                    rows = []
                    for row in product_data:
                        prod_id = row[0]
                        name = row[1]
                        size = row[2]
                        qty = row[3]
                        sales = row[4]
                        cost = row[5]
                        profit_before = row[6]
                        allocated_discount = product_discount.get(prod_id, 0)
                        profit_after = profit_before - allocated_discount
                        rows.append({
                            'Product Name': name,
                            'Size': size,
                            'Qty Sold': qty,
                            'Total Sales': sales,
                            'Total Cost': cost,
                            'Profit Before Discount': profit_before,
                            'Allocated Discount': allocated_discount,
                            'Profit After Discount': profit_after
                        })
                    df = pd.DataFrame(rows)
                    df.to_excel(filename, index=False)
                messagebox.showinfo("Success", f"Report exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during export: {str(e)}")
            finally:
                conn.close()


# ==============================================
# MAIN EXECUTION
# ==============================================

if __name__ == "__main__":
    # Create necessary directories
    if not os.path.exists("invoices_pdf"):
        os.makedirs("invoices_pdf")
    
    root = tk.Tk()
    app = ShoeStoreGUI(root)
    
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()