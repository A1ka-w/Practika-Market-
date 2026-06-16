
# ==================== API Эндпоинты ====================
@app.get("/api/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Получить все категории"""
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.sort_order).all()
    return categories


@app.get("/api/products", response_model=List[ProductResponse])
def get_products(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Получить товары (опционально по категории)"""
    query = db.query(Product).filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    products = query.order_by(Product.sort_order).all()

    for p in products:
        p.category_name = p.category.name if p.category else None
    return products



@app.get("/api/search")
def search_products(q: str, db: Session = Depends(get_db)):
    """Поиск товаров по названию"""
    if not q:
        return {"results": []}

    products = db.query(Product).filter(
        Product.is_active == True,
        Product.name.ilike(f"%{q}%")
    ).limit(20).all()

    results = []
    for p in products:
        results.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "price": p.price,
            "thumbnail_url": p.thumbnail_url,
            "category_name": p.category.name if p.category else None
        })

    return {"results": results}


@app.get("/api/health")
def health_check():
    """Проверка работоспособности"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


