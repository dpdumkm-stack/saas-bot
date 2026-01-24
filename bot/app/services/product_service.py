from app.models import Menu, Toko, db

def get_products(toko_id):
    """Get all products for a specific toko"""
    return Menu.query.filter_by(toko_id=toko_id).all()

def add_product(toko_id, data):
    """Add a new product"""
    try:
        new_product = Menu(
            toko_id=toko_id,
            item=data['item'],
            harga=int(data['harga']),
            stok=int(data.get('stok', -1)),
            category=data.get('category', 'Umum'),
            image_url=data.get('image_url'),
            description=data.get('description')
        )
        db.session.add(new_product)
        db.session.commit()
        return {"status": "success", "product": {
            "id": new_product.id,
            "item": new_product.item,
            "harga": new_product.harga,
            "stok": new_product.stok
        }}
    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}

def update_product(product_id, toko_id, data):
    """Update an existing product"""
    product = Menu.query.filter_by(id=product_id, toko_id=toko_id).first()
    if not product:
        return {"status": "error", "message": "Product not found"}
    
    try:
        if 'item' in data: product.item = data['item']
        if 'harga' in data: product.harga = int(data['harga'])
        if 'stok' in data: product.stok = int(data['stok'])
        if 'category' in data: product.category = data['category']
        if 'image_url' in data: product.image_url = data['image_url']
        if 'description' in data: product.description = data['description']
        
        db.session.commit()
        return {"status": "success"}
    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}

def delete_product(product_id, toko_id):
    """Delete a product"""
    product = Menu.query.filter_by(id=product_id, toko_id=toko_id).first()
    if not product:
        return {"status": "error", "message": "Product not found"}
    
    try:
        db.session.delete(product)
        db.session.commit()
        return {"status": "success"}
    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}
