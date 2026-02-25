import pandas as pd
import re
from io import BytesIO

def normalize_name(name):
    """Normalize string: lower case, strip, remove specific suffixes."""
    if not isinstance(name, str):
        return ""
    s = name.lower().strip()
    # Remove common suffixes like ", 1 пор" or " 1 пор"
    s = re.sub(r'[, ]+1\s*пор.*$', '', s)
    return s.strip()

def parse_ttk(file_content, filename=""):
    """
    Parse Technological Map (Excel).
    Returns: List of {"dish_name": str, "ingredients": DataFrame}
    """
    try:
        # Load full excel
        df_raw = pd.read_excel(file_content, header=None)
    except Exception as e:
        return [], f"Error reading Excel: {e}"

    found_recipes = []
    
    # State
    current_dish_name = None
    parsing_ingredients = False
    current_ingredients = []
    
    # We iterate row by row
    rows = df_raw.values.tolist()
    
    def clean_num(x):
        if isinstance(x, (int, float)): return float(x)
        if isinstance(x, str):
             x = x.replace(',', '.').replace(' ', '').replace('\xa0', '')
             try: return float(x)
             except: return 0.0
        return 0.0

    for idx, row in enumerate(rows):
        row_str = [str(v).lower().strip() for v in row]
        print(f"Row {idx}: {row_str}")
        
        # 1. Look for Dish Name
        if not parsing_ingredients:
            if "наименование блюда" in " ".join(row_str):
                print(f"Found 'наименование блюда' at row {idx}")
                vals = [str(v).strip() for v in row if str(v).lower() != 'nan' and str(v).strip() != '']
                for i, v in enumerate(vals):
                    if "наименование блюда" in v.lower():
                        if i + 1 < len(vals):
                            current_dish_name = normalize_name(vals[i+1])
                            print(f"Set dish name to: {current_dish_name}")
                            break
            
            # 2. Look for Table Header "Наименование продукта"
            if "наименование продукта" in " ".join(row_str) and current_dish_name:
                print(f"Found ingredient header at row {idx}")
                parsing_ingredients = True
                current_ingredients = []
                continue # Skip header row

        # 3. Parse Ingredients
        if parsing_ingredients:
            # Stop conditions
            first_cell = str(row[1]).strip().lower() # Column B
            if "выход" in first_cell or "технология" in first_cell or "наименование блюда" in " ".join(row_str):
                print(f"Found stop condition '{first_cell}' or 'наименование блюда' at row {idx}")
                if current_dish_name and current_ingredients:
                    found_recipes.append({
                        "dish_name": current_dish_name, 
                        "ingredients": current_ingredients
                    })
                
                current_dish_name = None
                parsing_ingredients = False
                current_ingredients = []
                
                if "наименование блюда" in " ".join(row_str):
                    vals = [str(v).strip() for v in row if str(v).lower() != 'nan' and str(v).strip() != '']
                    for i, v in enumerate(vals):
                         if "наименование блюда" in v.lower():
                            if i + 1 < len(vals):
                                current_dish_name = normalize_name(vals[i+1])
                                break
                continue

            ing_name = first_cell
            if ing_name == 'nan' or not ing_name:
                continue
                
            try:
                unit = str(row[2]).strip()
                net_val = row[5]
                qty = clean_num(net_val)
                print(f"Parsed {ing_name}: net_val={net_val}, qty={qty}, unit={unit}")
                if qty == 0:
                     qty = clean_num(row[7]) if len(row) > 7 else 0

                if qty > 0:
                    current_ingredients.append({
                        "ingredient": normalize_name(ing_name),
                        "unit": unit,
                        "qty_per_dish": qty
                    })
            except Exception as e:
                print(f"Exception on row {idx}: {e}")
                continue

    # End of file - save last if exists
    if parsing_ingredients and current_dish_name and current_ingredients:
        found_recipes.append({
            "dish_name": current_dish_name, 
            "ingredients": current_ingredients
        })
        
    return found_recipes, None


def parse_turnover(file_content, filename=""):
    """
    Parse 1C Turnover Balance Sheet (Excel).
    Returns: 
        df_stock: [ingredient, unit, stock_qty, income_qty, outcome_qty]
        df_history: [date, ingredient, qty_out] (Daily movements)
    """
    try:
        df_raw = pd.read_excel(file_content, header=None)
    except Exception as e:
        return None, None, f"Error reading Excel: {e}"
        
    header_row_idx = None
    
    # 1. Find Header
    for idx, row in df_raw.iterrows():
        row_str = row.astype(str).str.lower().tolist()
        if any("номенклатура" in s for s in row_str) and any("дебет" in s for s in row_str):
            header_row_idx = idx
            break
            
    if header_row_idx is None:
        return None, None, "Не найден заголовок таблицы (Ожидается: Номенклатура)"
        
    # 2. Extract Data
    data_stock = []
    data_history = []
    
    current_main_ingredient = None
    search_col_idx = 1 # Column B usually has "Кол."
    
    rows = df_raw.values.tolist()
    
    for i in range(header_row_idx + 1, len(rows)):
        currentRow = rows[i]
        
        # Check if this is a "Quantity" row
        if search_col_idx >= len(currentRow): continue
        marker = str(currentRow[search_col_idx]).strip()
        
        if marker == "Кол.":
            # The Name is in the PREVIOUS row, column 0
            if i > 0:
                prevRow = rows[i-1]
                name = str(prevRow[0]).strip()
                
                # Filter out junk names
                if not name or name.lower() == 'nan':
                    continue
                    
                # Define helper first
                def get_val(r, idx):
                    if idx >= len(r): return 0.0
                    try:
                        val = r[idx]
                        if str(val).lower() == 'nan': return 0.0
                        if isinstance(val, (int, float)): return float(val)
                        return float(str(val).replace(',', '.').replace(' ', '').replace('\xa0', ''))
                    except:
                        return 0.0

                # 1. CHECK IF HISTORY ROW ("Обороты за ...")
                date_match = re.search(r'Обороты за (\d{2}\.\d{2}\.\d{2})', name)
                if date_match:
                    # It is a Date row -> belongs to current_main_ingredient
                    if current_main_ingredient:
                        date_str = date_match.group(1)
                        # Column 5 (F) is Credit (Outcome/Consumption)
                        outcome = get_val(currentRow, 5)
                        
                        # We only care about consumption > 0
                        if outcome > 0:
                            data_history.append({
                                "date": date_str,
                                "ingredient": current_main_ingredient,
                                "qty_out": outcome
                            })
                    continue

                # 2. CHECK JUNK
                if "итого" in name.lower():
                    continue
                if re.match(r'^\d{2}\.\d{2}$', name): # Filter account numbers like 41.01
                    continue
                    
                # 3. IT IS A MAIN INGREDIENT ROW
                stock_end = get_val(currentRow, 6)
                income = get_val(currentRow, 4)
                outcome = get_val(currentRow, 5)
                
                # Column 2 (C) usually contains Unit
                unit = str(currentRow[2]).strip() if len(currentRow) > 2 else ""
                
                # Update Context
                current_main_ingredient = normalize_name(name)
                
                data_stock.append({
                    "ingredient": current_main_ingredient,
                    "unit": unit,
                    "stock_qty": stock_end,
                    "income_qty": income,
                    "outcome_qty": outcome
                })
        
    df_history = pd.DataFrame(data_history)
    if not df_history.empty:
        # Convert date to datetime objects
        df_history["date"] = pd.to_datetime(df_history["date"], format="%d.%m.%y", errors="coerce")
        
    if not data_stock:
        return None, None, "Данные не найдены (проверьте структуру файла или наличие строк 'Кол.')"
        
    return pd.DataFrame(data_stock), df_history, None
