import pandas as pd
import os
import shutil
from typing import List, Dict, Tuple


UPDATED_FILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'updated_excels')

class ExcelService:
    def __init__(self):
        self.file_path = None
        self.df = None

    def load_file(self, file_path: str) -> bool:
        if not file_path.endswith('.xlsx'):
            return False
        try:
            self.df = pd.read_excel(file_path)
            self.file_path = file_path
            # Normalize column names slightly to be robust
            self.df.columns = [str(c).strip().lower().replace(' ', '_') for c in self.df.columns]
            return True
        except Exception as e:
            print(f"Error loading excel: {e}")
            return False

    def get_categories(self) -> List[str]:
        if self.df is not None and 'pizza_category' in self.df.columns:
            return sorted(self.df['pizza_category'].dropna().unique().tolist())
        return []

    def preview_changes(self, category: str, price_change: float) -> List[Dict]:
        """Returns a list of dictionaries with old and new values for preview."""
        if self.df is None or 'pizza_category' not in self.df.columns or 'unit_price' not in self.df.columns or 'pizza_name' not in self.df.columns:
            return []
        
        preview_data = []
        # Filter matching rows
        mask = self.df['pizza_category'] == category
        filtered_df = self.df[mask]
        
        for index, row in filtered_df.iterrows():
            old_price = float(row['unit_price'])
            new_price = old_price + price_change
            preview_data.append({
                'pizza_name': row['pizza_name'],
                'old_price': old_price,
                'new_price': new_price,
                'difference': price_change
            })
        
        return preview_data

    def apply_and_save(self, category: str, price_change: float) -> Tuple[bool, int, str]:
        """Applies the changes, recalculates total_price, and saves to a new file.
        Returns (success, rows_modified, new_file_path)
        """
        if self.df is None:
            return False, 0, "No file loaded"
            
        mask = self.df['pizza_category'] == category
        rows_modified = int(mask.sum())
        
        if rows_modified == 0:
            return False, 0, "No matching category found."

        # Apply changes
        self.df.loc[mask, 'unit_price'] = self.df.loc[mask, 'unit_price'] + price_change
        
        # Recalculate total_price if quantity exists
        if 'quantity' in self.df.columns and 'total_price' in self.df.columns:
            self.df.loc[mask, 'total_price'] = self.df.loc[mask, 'unit_price'] * self.df.loc[mask, 'quantity']

        try:
            os.makedirs(UPDATED_FILES_DIR, exist_ok=True)

            original_name = os.path.basename(self.file_path)
            base, ext = os.path.splitext(original_name)
            new_file_path = os.path.join(UPDATED_FILES_DIR, f"{base}_updated{ext}")
            
            # Write back maintaining column order from original reading, but normalized names
            self.df.to_excel(new_file_path, index=False)
            return True, rows_modified, new_file_path
        except Exception as e:
            return False, 0, str(e)
