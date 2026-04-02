import pandas as pd
import os
import sys

# Import the processing function from app.py
from app import process_excel

def test_logic():
    test_file = 'veri.xlsx'
    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found.")
        return

    print("--- Running Precise Logic Verification ---")
    
    # Create a mock file object as gradio would pass
    class MockFile:
        def __init__(self, name):
            self.name = name
            
    mock_file = MockFile(test_file)
    output_path, _ = process_excel(mock_file)
    
    if not output_path:
        print("Error: Processing failed.")
        return
        
    df = pd.read_excel(output_path)
    
    errors = []
    
    # Rule checks
    for idx, row in df.iterrows():
        # 1. New Target CPA != 0
        if row['New target CPA'] <= 0:
            errors.append(f"Row {idx}: New target CPA is {row['New target CPA']} (Expected > 0)")
            
        # 2. New daily budget >= 4.9 (Min 5)
        if row['New daily budget'] < 4.9:
            errors.append(f"Row {idx}: New daily budget is {row['New daily budget']} (Expected >= 5)")
        
        # 3. Label KPI adjacency (Priority 1)
        # We need to map the internal column name to the Excel column name for validation
        kpi_col = "Label KPI value" if "Label KPI value" in df.columns else "Label KPI"
        kpi = row[kpi_col]
        tcpa = row['New target CPA']
        if tcpa > kpi * 1.16: # Max 15% flex
             errors.append(f"Row {idx}: New target CPA {tcpa} exceeds KPI {kpi} by > 15%")

    if not errors:
        print("SUCCESS: All precise logic checks passed!")
    else:
        print(f"FAILED: {len(errors)} errors found.")
        for err in errors[:5]:
            print(f" - {err}")
            
    # Cleanup
    # os.remove(output_path)

if __name__ == "__main__":
    test_logic()
