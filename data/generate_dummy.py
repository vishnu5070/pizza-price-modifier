import pandas as pd
import os

data = {
    'pizza_name': ['The Hawaiian Pizza', 'Classic Deluxe', 'BBQ Chicken', 'Veggie Supreme'],
    'pizza_category': ['Classic', 'Classic', 'Chicken', 'Veggie'],
    'unit_price': [13.25, 16.00, 18.50, 15.00],
    'quantity': [2, 1, 3, 2],
    'total_price': [26.50, 16.00, 55.50, 30.00]
}

df = pd.DataFrame(data)
os.makedirs('d:/Intern/003/data', exist_ok=True)
df.to_excel('d:/Intern/003/data/pizza_sales.xlsx', index=False)
print("Dummy Excel file created.")
