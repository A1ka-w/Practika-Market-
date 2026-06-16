from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import os

# ==================== Конфигурация ====================
# База данных будет создана в корне проекта
DATABASE_URL = "sqlite:///./nimmi_shop.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Настройка путей для шаблонов и статики
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(TEMPLATES_DIR, "images")  # Папка для изображений

# Создаем директории, если их нет
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)


# ==================== Модели данных ====================
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    image_url = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    stock = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    category = relationship("Category", back_populates="products")
    cart_items = relationship("CartItem", back_populates="product")


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    added_at = Column(DateTime, default=datetime.utcnow)
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product", back_populates="cart_items")


# ==================== Pydantic схемы ====================
class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    image_url: Optional[str] = None
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category_id: int
    category_name: Optional[str] = None
    stock: int
    is_active: bool

    class Config:
        from_attributes = True


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1


# ==================== FastAPI приложение ====================
app = FastAPI(title="NIMMI Shop API", version="1.0.0")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создание таблиц
Base.metadata.create_all(bind=engine)

# Подключение статических файлов (изображения)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== Инициализация данных ====================
def init_demo_data():
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже данные
        if db.query(Category).count() > 0:
            print("Данные уже есть, пропускаем инициализацию")
            return

        print("Инициализация демо-данных...")

        # Категории
        categories = [
            Category(name="Фрукты", slug="fruits",
                     image_url="https://i.pinimg.com/736x/fa/5a/1b/fa5a1b50491bd61fb2909d30b82ca252.jpg",
                     sort_order=1),
            Category(name="Овощи", slug="vegetables",
                     image_url="https://i1-c.pinimg.com/1200x/f9/ce/6b/f9ce6b6ce9140da9179756227f615535.jpg",
                     sort_order=2),
            Category(name="Выпечка", slug="bakery",
                     image_url="https://i1-c.pinimg.com/1200x/a8/25/d4/a825d4379809657ef57af5d3f45aa825.jpg",
                     sort_order=3),
        ]
        db.add_all(categories)
        db.commit()

        # Получаем ID категорий
        fruits = db.query(Category).filter(Category.slug == "fruits").first()
        vegetables = db.query(Category).filter(Category.slug == "vegetables").first()
        bakery = db.query(Category).filter(Category.slug == "bakery").first()


        print(f"✅ Добавлено {len(categories)} категорий и {len(products)} товаров")

    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка инициализации: {e}")
    finally:
        db.close()


# Запускаем инициализацию при старте
@app.on_event("startup")
async def startup_event():
    init_demo_data()


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


@app.get("/api/products/{product_slug}", response_model=ProductResponse)
def get_product(product_slug: str, db: Session = Depends(get_db)):
    """Получить товар по slug"""
    product = db.query(Product).filter(Product.slug == product_slug, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.category_name = product.category.name if product.category else None
    return product


# Корзина
def get_or_create_cart(session_id: str, db: Session) -> Cart:
    cart = db.query(Cart).filter(Cart.session_id == session_id).first()
    if not cart:
        cart = Cart(session_id=session_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


@app.get("/api/cart")
def get_cart(session_id: str, db: Session = Depends(get_db)):
    """Получить содержимое корзины"""
    cart = get_or_create_cart(session_id, db)

    items = []
    total = 0
    for item in cart.items:
        if item.product:
            subtotal = item.product.price * item.quantity
            total += subtotal
            items.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "product_price": item.product.price,
                "quantity": item.quantity,
                "subtotal": subtotal
            })

    return {
        "items": items,
        "total": total,
        "item_count": len(items)
    }


@app.post("/api/cart/add")
def add_to_cart(request: AddToCartRequest, session_id: str, db: Session = Depends(get_db)):
    """Добавить товар в корзину"""
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart = get_or_create_cart(session_id, db)

    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == request.product_id
    ).first()

    if cart_item:
        cart_item.quantity += request.quantity
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=request.product_id, quantity=request.quantity)
        db.add(cart_item)

    db.commit()

    return {"message": "Товар добавлен в корзину", "success": True}


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


# ==================== Главная страница ====================
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Отображение главной страницы"""
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>NIMMI Shop</title></head>
        <body>
            <h1>NIMMI Shop API</h1>
            <p>Сервер работает. Поместите ваш HTML файл в папку <strong>templates/index.html</strong></p>
            <hr>
            <h3>API Endpoints:</h3>
            <ul>
                <li><a href="/api/categories">/api/categories</a> - категории</li>
                <li><a href="/api/products">/api/products</a> - товары</li>
                <li><a href="/api/health">/api/health</a> - проверка</li>
            </ul>
        </body>
        </html>
        """)


# ==================== Запуск сервера ====================
if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 50)
    print("🚀 NIMMI Shop Server Starting...")
    print("=" * 50)
    print(f"📁 Templates folder: {TEMPLATES_DIR}")
    print(f"🖼️  Images folder: {STATIC_DIR}")
    print(f"🗄️  Database: {os.path.join(BASE_DIR, 'nimmi_shop.db')}")
    print("\n✨ Server will be available at: http://localhost:8000")
    print("📡 API docs: http://localhost:8000/docs")
    print("=" * 50 + "\n")

    uvicorn.run("script:app", host="0.0.0.0", port=8000, reload=True)
