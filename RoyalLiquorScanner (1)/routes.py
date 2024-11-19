import csv
from datetime import datetime
from io import StringIO, BytesIO
from flask import render_template, request, jsonify, send_file
from app import app, db
from models import Product, PurchaseOrder, OrderItem

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inventory')
def inventory():
    products = Product.query.all()
    return render_template('inventory.html', products=products)

@app.route('/orders')
def orders():
    purchase_orders = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()
    products = Product.query.all()  # Add this line to pass products to the template
    return render_template('orders.html', orders=purchase_orders, products=products)

@app.route('/api/order/<int:order_id>/details')
def get_order_details(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    items = []
    
    for item in order.items:
        items.append({
            'name': item.product.name,
            'quantity': item.quantity,
            'price': float(item.price),
            'subtotal': float(item.quantity * item.price)
        })
    
    return jsonify({
        'order_number': order.order_number,
        'date': order.created_at.strftime('%Y-%m-%d'),
        'status': order.status,
        'total': float(order.total_amount),
        'items': items
    })

@app.route('/api/import-products', methods=['POST'])
def import_products():
    try:
        imported_count = 0
        skipped_count = 0
        
        with open('Inventory_Royal_Liquor.csv', 'r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                try:
                    # Clean up price string and convert to float
                    price_str = row['Price'].strip('$ ')
                    if price_str:
                        price = float(price_str)
                    else:
                        price = 0.0

                    # Create new product
                    product = Product(
                        barcode=row['Barcode'],
                        name=row['Name'].strip('✨ '),  # Remove sparkle emoji if present
                        price=price,
                        quantity=0  # Set initial quantity to 0
                    )
                    db.session.add(product)
                    db.session.commit()
                    imported_count += 1
                except Exception as e:
                    # Skip duplicates and other errors
                    db.session.rollback()
                    skipped_count += 1
                    continue

        return jsonify({
            'success': True,
            'message': f'Successfully imported {imported_count} products. Skipped {skipped_count} duplicates.',
            'imported': imported_count,
            'skipped': skipped_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/product/<barcode>')
def get_product(barcode):
    product = Product.query.filter_by(barcode=barcode).first()
    if product:
        return jsonify({
            'id': product.id,
            'name': product.name,
            'price': round(float(product.price), 2),  # Ensure price is properly formatted
            'quantity': product.quantity
        })
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/product', methods=['POST'])
def add_product():
    data = request.json
    try:
        product = Product(
            barcode=data['barcode'],
            name=data['name'],
            quantity=data['quantity'],
            price=data['price']
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.json
    try:
        order = PurchaseOrder(
            order_number=PurchaseOrder.generate_order_number(),
            total_amount=data['total_amount']
        )
        db.session.add(order)
        
        for item in data['items']:
            order_item = OrderItem(
                purchase_order=order,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
            
            # Update inventory
            product = Product.query.get(item['product_id'])
            product.quantity += item['quantity']
        
        db.session.commit()
        return jsonify({'success': True, 'order_number': order.order_number})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/export/orders')
def export_orders():
    orders = PurchaseOrder.query.all()
    output = StringIO()
    cw = csv.writer(output)
    cw.writerow(['Order Number', 'Total Amount', 'Status', 'Created At'])
    
    for order in orders:
        cw.writerow([
            order.order_number,
            order.total_amount,
            order.status,
            order.created_at
        ])
    
    # Convert to bytes for send_file
    bytes_output = BytesIO()
    bytes_output.write(output.getvalue().encode('utf-8'))
    bytes_output.seek(0)
    output.close()
    
    return send_file(
        bytes_output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='purchase_orders.csv'
    )

@app.route('/api/order/<int:order_id>', methods=['PATCH'])
def update_order(order_id):
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        data = request.json
        
        if not data.get('items'):
            return jsonify({'error': 'No items provided'}), 400

        # Update order items
        existing_items = {item.id: item for item in order.items}
        updated_item_ids = [item['id'] for item in data['items']]
        
        # Remove items that are not in the update
        for item_id in existing_items:
            if str(item_id) not in updated_item_ids:
                db.session.delete(existing_items[item_id])
        
        # Update existing items and add new ones
        for item_data in data['items']:
            item_id = item_data['id']
            if item_id in existing_items:
                item = existing_items[item_id]
                item.quantity = item_data['quantity']
                item.price = item_data['price']
            else:
                new_item = OrderItem(
                    purchase_order_id=order.id,
                    product_id=item_id,
                    quantity=item_data['quantity'],
                    price=item_data['price']
                )
                db.session.add(new_item)

        # Update total amount
        order.total_amount = float(data['total_amount'])
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Order updated successfully'})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': 'Invalid numeric value provided'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
