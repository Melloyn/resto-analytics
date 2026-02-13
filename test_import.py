import sys
import os

# Create dummy Streamlit context or mock if needed?
# Actually just import should trigger top-level code execution.
try:
    from views import reports_view
    print("Import successful")
    if hasattr(reports_view, 'render_procurement'):
        print("Function exists")
    else:
        print("Function MISSING")
except Exception as e:
    print(f"Import Failed: {e}")
