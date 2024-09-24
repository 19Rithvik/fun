from fastapi.testclient import TestClient
from .main import app  # Ensure this is the correct path to your FastAPI app

# Create a TestClient instance to interact with the FastAPI app
client = TestClient(app)

# Function to clean up all products
def cleanup_products():
    response = client.get("/products/")
    for product in response.json():
        client.delete(f"/products/{product['id']}")

cleanup_products()  

# Test for creating a new product
def test_create_product():
    print("Testing: Create Product")

    product_data = {
        "name": "Test Product",
        "price": 100.5,
        "quantity": 10,
        "description": "A test product",
        "category": "Test Category"
    }

    # Test creating a new product
    response = client.post("/products/", json=product_data)
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"]
    assert data["quantity"] == product_data["quantity"]
    assert data["description"] == product_data["description"]
    assert data["category"] == product_data["category"]

    # Try creating the same product again (expect failure due to unique constraint on name)
    response = client.post("/products/", json=product_data)
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 400
    assert response.json() == {"detail": "Product creation failed due to duplicate name."}

# Test for getting a product by ID
def test_get_product():
    print("Testing: Get Product")

    # First, create a product to retrieve
    product_data = {
        "name": "Get Test Product",
        "price": 50.0,
        "quantity": 5,
        "description": "A product to test GET",
        "category": "Test Category"
    }
    response = client.post("/products/", json=product_data)
    assert response.status_code == 200
    product_id = response.json()["id"]

    # Retrieve the product by ID
    response = client.get(f"/products/{product_id}")
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"]
    assert data["quantity"] == product_data["quantity"]

    # Test for a product that doesn't exist (non-existent ID)
    response = client.get("/products/9999")
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

# Test for deleting a product
def test_delete_product():
    print("Testing: Delete Product")

    # Create a product to delete
    product_data = {
        "name": "Delete Test Product",
        "price": 75.0,
        "quantity": 3,
        "description": "A product to test DELETE",
        "category": "Test Category"
    }
    response = client.post("/products/", json=product_data)
    assert response.status_code == 200
    product_id = response.json()["id"]

    # Delete the product
    response = client.delete(f"/products/{product_id}")
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {"message": "Product deleted successfully"}

    # Ensure the product is no longer available
    response = client.get(f"/products/{product_id}")
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

    # Try deleting a non-existent product
    response = client.delete(f"/products/{product_id}")
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

# Test for updating a product
def test_update_product():
    print("Testing: Update Product")

    # Create a product to update
    product_data = {
        "name": "Update Test Product",
        "price": 60.0,
        "quantity": 20,
        "description": "A product to test update",
        "category": "Test Category"
    }
    response = client.post("/products/", json=product_data)
    assert response.status_code == 200
    product_id = response.json()["id"]

    # Update the product
    updated_data = {
        "price": 80.0,
        "quantity": 25
    }
    response = client.put(f"/products/{product_id}", json=updated_data)
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == updated_data["price"]
    assert data["quantity"] == updated_data["quantity"]

# Test for listing products
def test_list_products():
    print("Testing: List Products")
    
    # Get the current number of products in the database
    response = client.get("/products/")
    assert response.status_code == 200
    initial_data = response.json()
    initial_count = len(initial_data)

    # Create multiple products
    product_1 = {
        "name": "Product 1",
        "price": 10.0,
        "quantity": 1,
        "description": "Product 1 description",
        "category": "Category 1"
    }
    product_2 = {
        "name": "Product 2",
        "price": 20.0,
        "quantity": 2,
        "description": "Product 2 description",
        "category": "Category 2"
    }

    # Add new products
    client.post("/products/", json=product_1)
    client.post("/products/", json=product_2)

    # List all products again
    response = client.get("/products/")
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 200
    updated_data = response.json()
    
    # Ensure the total number of products now equals initial count + 2
    assert len(updated_data) == initial_count + 2  # Ensure total products count increased

    # List products with price filter
    response = client.get("/products/?price_gte=15")
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    
    # Check the database for expected products matching the price criteria
    expected_products = [p for p in updated_data if p["price"] >= 15]
    
    # Print the expected products
    print("Expected products matching price filter (>= 15):")
    for product in expected_products:
        print(product)
    
    # Assert that the API response matches expected products
    assert len(data) == len(expected_products)  # Ensure the length matches
    for product in data:
        assert product in expected_products  # Ensure each returned product is in expected products

# Test for invalid product creation
def test_invalid_product_creation():
    print("Testing: Invalid Product Creation")

    # Test product creation with invalid data (negative price)
    invalid_product_data = {
        "name": "Invalid Product",
        "price": -100.0,  # Invalid price
        "quantity": 10,
        "description": "Invalid product test",
        "category": "Test Category"
    }

    response = client.post("/products/", json=invalid_product_data)
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 422  # Unprocessable Entity (invalid data)

    # Test product creation with missing required fields
    incomplete_product_data = {
        "price": 100.0,
        "quantity": 10
    }

    response = client.post("/products/", json=incomplete_product_data)
    print(f"Status Code: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 422  # Unprocessable Entity (missing required fields)

# Run the tests
if __name__ == "__main__":
    print("Starting tests...")
    test_create_product()
    test_get_product()
    test_delete_product()
    test_update_product()
    test_list_products()
    test_invalid_product_creation()
    print("All tests completed.")
