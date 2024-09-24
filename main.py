import os
from fastapi import FastAPI, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, Float, create_engine, UniqueConstraint
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import IntegrityError
import logging
from typing import Optional, List

# Setup logging
logging.basicConfig(level=logging.INFO)

# Database setup - store SQLite database in /tmp directory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tmp/test.db")  # Update this line
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create the database tables if they do not exist
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# SQLAlchemy Product Model with Unique Constraint on name
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint('name', name='uq_product_name'),)  # Unique constraint

# Pydantic Model for Product Schema (Create)
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Name cannot be empty")
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    quantity: int = Field(..., ge=0, description="Quantity must be greater than or equal to 0")
    description: Optional[str] = None
    category: Optional[str] = None

    @field_validator('name', 'description', 'category', mode='before')
    def empty_string_not_allowed(cls, v):
        if isinstance(v, str) and v.strip() == "":
            raise ValueError("Field cannot be an empty string")
        return v

# Pydantic Model for Product Schema (Response with ID)
class ProductResponse(ProductCreate):
    id: int

# Pydantic Model for Product Schema (Update)
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    category: Optional[str] = None

    @field_validator('name', 'description', 'category', mode='before')
    def empty_string_not_allowed_update(cls, v):
        if isinstance(v, str) and v.strip() == "":
            raise ValueError("Field cannot be an empty string")
        return v

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Product REST API"}

# Create a product with proper error handling
@app.post("/products/", response_model=ProductResponse)
def create_product(product: ProductCreate = Body(...), db: Session = Depends(get_db)):
    try:
        db_product = Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    except IntegrityError as e:
        db.rollback()
        logging.error(f"IntegrityError: {e}")
        raise HTTPException(status_code=400, detail="Product creation failed due to duplicate name.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while creating the product.")

# Retrieve a product by ID with error handling for non-existent and invalid IDs
@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Update a product and ensure constraints are respected
@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Use existing values for fields that are not provided in the update request
    update_data = product.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_product, key, value)

    try:
        db.commit()
        db.refresh(db_product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Update failed due to duplicate name.")
    
    return db_product

# Delete a product with proper error handling for non-existent products
@app.delete("/products/{product_id}", response_model=dict)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}

# List all products with optional price filtering and handling empty list case
@app.get("/products/", response_model=List[ProductResponse])
def list_products(price_gte: Optional[float] = Query(None, ge=0), db: Session = Depends(get_db)):
    query = db.query(Product)
    if price_gte is not None:
        query = query.filter(Product.price >= price_gte)
    products = query.all()
    
    # Handle empty list response gracefully
    return products if products else []

# Run the application if the script is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
