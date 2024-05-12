import json
import random
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load the dataset
with open('data.json') as f:
    data = json.load(f)

ingredient_options = {
    "low": 0.05,
    "medium": 0.1,
    "high": 0.15
}

#Landing Page
@app.route("/", methods=["GET"])
def hello_world():
    home_page_ingredients=[]
    
    h1 = "Welcome to the best restaurant ever!"
    
    home_page_ingredients.append(h1)
    
    return jsonify(home_page_ingredients)

# Listing meals by their vegan, vegetarian or non-vegetarian status
@app.route('/listMeals', methods=['GET'])
def list_meals():
    is_vegetarian = request.args.get('is_vegetarian', '').lower() in ['true', '1', 't', 'y', 'yes']
    is_vegan = request.args.get('is_vegan', '').lower() in ['true', '1', 't', 'y', 'yes']

    filtered_meals = []

    for meal in data['meals']:
        if is_vegetarian and not is_meal_vegetarian(meal):
            continue
        if is_vegan and not is_meal_vegan(meal):
            continue
        filtered_meals.append({
            'id': meal['id'],
            'name': meal['name'],
            'ingredients': [ingredient['name'] for ingredient in meal['ingredients']]
        })

    return jsonify(filtered_meals)

# Helper function to find vegetarian product
def is_meal_vegetarian(meal):
    for ingredient in meal['ingredients']:
        ingredient_info = get_ingredient_info(ingredient['name'])
        if not ingredient_info or 'vegetarian' not in ingredient_info['groups']:
            return False
    return True

# Helper function to find vegan product
def is_meal_vegan(meal):
    for ingredient in meal['ingredients']:
        ingredient_info = get_ingredient_info(ingredient['name'])
        if not ingredient_info or 'vegan' not in ingredient_info['groups']:
            return False
    return True

# Helper function to find ingredient info in details
def get_ingredient_info(ingredient_name):
    for ingredient in data['ingredients']:
        if ingredient['name'].lower() == ingredient_name.lower():
            return ingredient
    return None

# Get single meal by its id
@app.route('/getMeal', methods=['GET'])
def get_meal():
    meal_id = request.args.get('id')

    if meal_id is None:
        return jsonify({'error': 'Meal ID is required'}), 400

    meal = find_meal_by_id(int(meal_id))
    
    if meal is None:
        return jsonify({'error': 'Meal not found'}), 404

    meal_info = {
        'id': meal['id'],
        'name': meal['name'],
        'ingredients': []
    }

    for ingredient in meal['ingredients']:
        ingredient_info = get_ingredient_info(ingredient['name'])
        if ingredient_info:
            ingredient_entry = {
                'name': ingredient['name'],
                'options': ingredient_info['options']
            }
            meal_info['ingredients'].append(ingredient_entry)

    return jsonify(meal_info)

def find_meal_by_id(meal_id):
    for meal in data['meals']:
        if meal['id'] == meal_id:
            return meal
    return None

# Calculating quality score for meal
@app.route('/quality', methods=['POST'])
def calculate_quality():
    meal_id = int(request.form.get('meal_id'))
    ingredient_qualities = {key: request.form.get(key, 'high') for key in request.form.keys() if key != 'meal_id'}

    quality_score = calculate_quality_score(meal_id, ingredient_qualities)
    return jsonify({"quality_score": quality_score})

def calculate_quality_score(meal_id, ingredient_qualities):
    total_score = 0
    meal = find_meal_by_id(meal_id) 
    
    for ingredient in meal['ingredients']:
        ingredient_info = get_ingredient_info(ingredient['name']) 
        quality = ingredient_qualities.get(ingredient['name'], 'high')  # Default to 'high' if quality not specified
        
        # I made it up, high quality products receive 5 points and so on
        if quality == 'high':
            multiplier = 5
        elif quality == 'medium':
            multiplier = 3
        else:
            multiplier = 1
        
        # Get the price of the ingredient from its options
        price = 0
        for option in ingredient_info['options']:
            if option['quality'] == quality:
                price = option['price']
                break
        
        total_score += price * multiplier
    
    return total_score

# Calculating price for meals 
@app.route('/price', methods=['POST'])
def calculate_price():
    meal_id = request.form.get('meal_id')

    if meal_id is None:
        return jsonify({'error': 'Meal ID is required'}), 400

    meal = find_meal_by_id(int(meal_id))

    if meal is None:
        return jsonify({'error': 'Meal not found'}), 404

    total_price = 0

    # Iterate over each ingredient in the meal
    for ingredient in meal['ingredients']:
        ingredient_name = ingredient['name']

        # Get ingredient quality selection from request, default to "high" if not specified
        ingredient_quality = request.form.get(ingredient_name, 'high')

        # Find ingredient quality options from dataset
        ingredient_info = get_ingredient_info(ingredient_name)

        if ingredient_info:
            # Get the price based on the selected quality option
            price = get_price(ingredient_quality, ingredient_info)
            total_price += price

    return jsonify({'price': total_price})

def get_price(quality_option, ingredient_info):
    for option in ingredient_info['options']:
        if option['quality'] == quality_option:
            return option['price']
    return 0  

@app.route('/random', methods=['POST'])
def random_meal():
    budget = request.form.get('budget')
    if budget is not None:
        try:
            budget = float(budget)
        except ValueError:
            return jsonify({'error': 'Invalid budget value'}), 400
    else:
        budget = float('inf')
    # Check if meal is valid for our budget
    valid_meals = [meal for meal in data['meals'] if calculate_meal_price(meal) <= budget]

    if not valid_meals:
        return jsonify({'error': 'No valid meals found within budget'}), 400

   

    random_meal = random.choice(valid_meals) 

    while (calculate_meal_price(random_meal) > budget):
        random_meal = random.choice(valid_meals) 

    return jsonify({
        'id': random_meal['id'],
        'name': random_meal['name'],
        'price': calculate_meal_price(random_meal),
        'ingredients': [ingredient['name'] for ingredient in random_meal['ingredients']]
    })
    
def calculate_meal_price(meal):
    total_price = 0
    for ingredient in meal['ingredients']:
        total_price += get_price(ingredient['name'], ingredient['quantity'], ingredient['quantity_type'])
    return total_price

def get_price(ingredient_name, quantity, quantity_type):
    for ingredient in data['ingredients']:
        if ingredient['name'].lower() == ingredient_name.lower():
            for option in ingredient['options']:
                ingredient_price_per_kg = option['price']
                quantity_in_kg = convert_to_kg(quantity, quantity_type)
                return ingredient_price_per_kg * quantity_in_kg
    return 0

def convert_to_kg(quantity, quantity_type):
    if quantity_type == 'gram':
        return quantity / 1000
    elif quantity_type == 'liter':
        return quantity * 1000
    elif quantity_type == 'milliliter':
        return quantity
    else:
        return quantity


@app.route('/search', methods=['GET'])
def search_meals():
    query = request.args.get('query', '').lower() # for case-insensitive search

    if not query:
        return jsonify([])  

    # Filter meals based on whether the query is a substring of the meal name (case-insensitive)
    matching_meals = [meal for meal in data['meals'] if query in meal['name'].lower()]

    return jsonify(matching_meals)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
