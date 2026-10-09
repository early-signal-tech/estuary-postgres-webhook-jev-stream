"""Meals and their ingredients. Each order_id is assigned one of these meals."""

MEALS = {
    "Spaghetti Bolognese": [
        {"name": "spaghetti", "qty": 1, "unit": "lb", "category": "pantry"},
        {"name": "ground beef", "qty": 1, "unit": "lb", "category": "meat"},
        {"name": "crushed tomatoes", "qty": 1, "unit": "28oz can", "category": "pantry"},
        {"name": "yellow onion", "qty": 1, "unit": "each", "category": "produce"},
        {"name": "garlic", "qty": 1, "unit": "head", "category": "produce"},
        {"name": "carrot", "qty": 2, "unit": "each", "category": "produce"},
        {"name": "olive oil", "qty": 1, "unit": "bottle", "category": "pantry"},
        {"name": "parmesan", "qty": 1, "unit": "wedge", "category": "dairy"},
    ],
    "Chicken Stir-Fry": [
        {"name": "chicken breast", "qty": 2, "unit": "lb", "category": "meat"},
        {"name": "jasmine rice", "qty": 1, "unit": "2lb bag", "category": "pantry"},
        {"name": "broccoli", "qty": 1, "unit": "head", "category": "produce"},
        {"name": "red bell pepper", "qty": 2, "unit": "each", "category": "produce"},
        {"name": "soy sauce", "qty": 1, "unit": "bottle", "category": "pantry"},
        {"name": "fresh ginger", "qty": 1, "unit": "piece", "category": "produce"},
        {"name": "green onions", "qty": 1, "unit": "bunch", "category": "produce"},
        {"name": "sesame oil", "qty": 1, "unit": "bottle", "category": "pantry"},
    ],
    "Beef Tacos": [
        {"name": "ground beef", "qty": 2, "unit": "lb", "category": "meat"},
        {"name": "corn tortillas", "qty": 1, "unit": "pack", "category": "bakery"},
        {"name": "taco seasoning", "qty": 1, "unit": "packet", "category": "pantry"},
        {"name": "shredded cheddar", "qty": 1, "unit": "8oz bag", "category": "dairy"},
        {"name": "iceberg lettuce", "qty": 1, "unit": "head", "category": "produce"},
        {"name": "roma tomatoes", "qty": 3, "unit": "each", "category": "produce"},
        {"name": "sour cream", "qty": 1, "unit": "tub", "category": "dairy"},
        {"name": "salsa", "qty": 1, "unit": "jar", "category": "pantry"},
    ],
    "Caesar Salad with Salmon": [
        {"name": "salmon fillet", "qty": 2, "unit": "each", "category": "seafood"},
        {"name": "romaine hearts", "qty": 1, "unit": "3-pack", "category": "produce"},
        {"name": "caesar dressing", "qty": 1, "unit": "bottle", "category": "pantry"},
        {"name": "croutons", "qty": 1, "unit": "bag", "category": "bakery"},
        {"name": "parmesan", "qty": 1, "unit": "wedge", "category": "dairy"},
        {"name": "lemon", "qty": 2, "unit": "each", "category": "produce"},
    ],
    "Pancake Breakfast": [
        {"name": "all-purpose flour", "qty": 1, "unit": "5lb bag", "category": "pantry"},
        {"name": "eggs", "qty": 1, "unit": "dozen", "category": "dairy"},
        {"name": "milk", "qty": 1, "unit": "half gallon", "category": "dairy"},
        {"name": "butter", "qty": 1, "unit": "lb", "category": "dairy"},
        {"name": "maple syrup", "qty": 1, "unit": "bottle", "category": "pantry"},
        {"name": "blueberries", "qty": 1, "unit": "pint", "category": "produce"},
        {"name": "bacon", "qty": 1, "unit": "pack", "category": "meat"},
    ],
}

# Everyday items that don't belong to any meal; added as off-meal noise.
STAPLES = [
    {"name": "bananas", "qty": 1, "unit": "bunch", "category": "produce"},
    {"name": "ground coffee", "qty": 1, "unit": "12oz bag", "category": "pantry"},
    {"name": "paper towels", "qty": 1, "unit": "6-roll pack", "category": "household"},
    {"name": "dish soap", "qty": 1, "unit": "bottle", "category": "household"},
    {"name": "sparkling water", "qty": 1, "unit": "12-pack", "category": "beverages"},
    {"name": "greek yogurt", "qty": 1, "unit": "tub", "category": "dairy"},
    {"name": "potato chips", "qty": 1, "unit": "bag", "category": "snacks"},
    {"name": "apples", "qty": 6, "unit": "each", "category": "produce"},
    {"name": "sandwich bread", "qty": 1, "unit": "loaf", "category": "bakery"},
    {"name": "dark chocolate", "qty": 1, "unit": "bar", "category": "snacks"},
]
