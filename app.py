from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
import numpy as np
import os
import io

app = FastAPI(
    title="MHTCET College Finder",
    description="Advanced college suggestion tool for MHTCET 2025",
    version="1.0.0"
)

# Ensure static files are mounted correctly
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Global data management
class DataManager:
    def __init__(self, file_path):
        self.original_df = self.load_data(file_path)
        self.df = self.original_df.copy()
        self.categories = self.prepare_dropdown(self.df, 'category')
        self.quotas = self.prepare_dropdown(self.df, 'quota_type')
        self.branches = self.prepare_dropdown(self.df, 'branch_name')

    def load_data(self, file_path):
        try:
            # Print current working directory and file path for debugging
            print(f"Current working directory: {os.getcwd()}")
            print(f"Attempting to load file: {file_path}")
            print(f"File exists: {os.path.exists(file_path)}")

            # Read CSV with error handling
            df = pd.read_csv(file_path, encoding='cp1252')
            
            # Ensure all necessary columns exist
            required_columns = [
                'college_code', 'college_name', 'branch_code', 'branch_name', 
                'category_code', 'category', 'quota_type', 'allocation_type', 
                'rank', 'percentile'
            ]
            
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")

            print(f"Loaded dataframe shape: {df.shape}")
            return df
        except Exception as e:
            print(f"Data loading error: {e}")
            return pd.DataFrame()

    def prepare_dropdown(self, df, column):
        # Handle empty DataFrame
        if df.empty:
            return ["All"]
        
        return ["All"] + sorted([
            str(x) for x in df[column].unique() 
            if pd.notna(x) and str(x).lower() != 'not specified'
        ])

    def search_colleges(
        self, 
        rank: int, 
        category: str = "All", 
        quota: str = "All", 
        branch: str = "All"
    ):
        # Reset to original dataframe
        df = self.original_df.copy()

        # Handle empty DataFrame
        if df.empty:
            print("DataFrame is empty")
            return {
                'results': [],
                'total_matches': 0,
                'rank_min': 0,
                'rank_max': 0,
                'unique_colleges': 0
            }

        # Print search parameters for debugging
        print(f"Search parameters: rank={rank}, category={category}, quota={quota}, branch={branch}")

        # Create initial mask based on rank
        mask = (df['rank'] >= rank - 1000) & (df['rank'] <= rank + 1000)

        # Apply additional filters
        if category != "All":
            mask &= df['category'] == category
        if quota != "All":
            mask &= df['quota_type'] == quota
        if branch != "All":
            mask &= df['branch_name'] == branch

        # Apply mask and sort
        results = df[mask].sort_values('rank')
        
        print(f"Search results count: {len(results)}")

        return {
            'results': results.to_dict('records'),
            'total_matches': len(results),
            'rank_min': results['rank'].min() if not results.empty else 0,
            'rank_max': results['rank'].max() if not results.empty else 0,
            'unique_colleges': results['college_name'].nunique() if not results.empty else 0
        }

# Determine the correct path for the CSV file
def find_csv_file():
    possible_paths = [
        'Structured_MHTCET_Cutoffs_with_validation.csv',
        './Structured_MHTCET_Cutoffs_with_validation.csv',
        os.path.join(os.getcwd(), 'Structured_MHTCET_Cutoffs_with_validation.csv')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError("Could not find the CSV file")

# Initialize data manager
try:
    DATA_FILE_PATH = find_csv_file()
    data_manager = DataManager(DATA_FILE_PATH)
except Exception as e:
    print(f"Failed to initialize DataManager: {e}")
    data_manager = None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if data_manager is None:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Data file could not be loaded"
        })
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "categories": data_manager.categories,
        "quotas": data_manager.quotas,
        "branches": data_manager.branches
    })

@app.post("/search")
async def search_colleges(
    request: Request,
    rank: int = Form(...),
    category: str = Form(default="All"),
    quota: str = Form(default="All"),
    branch: str = Form(default="All")
):
    if data_manager is None:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Data manager not initialized"
        })

    try:
        search_results = data_manager.search_colleges(
            rank, category, quota, branch
        )
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "categories": data_manager.categories,
            "quotas": data_manager.quotas,
            "branches": data_manager.branches,
            "rank": rank,
            "category": category,
            "quota": quota,
            "branch": branch,
            **search_results
        })
    except Exception as e:
        print(f"Search error: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "categories": data_manager.categories,
            "quotas": data_manager.quotas,
            "branches": data_manager.branches,
            "error": str(e)
        })

@app.post("/export")
async def export_results(
    request: Request,
    rank: int = Form(...),
    category: str = Form(default="All"),
    quota: str = Form(default="All"),
    branch: str = Form(default="All")
):
    if data_manager is None:
        raise HTTPException(status_code=500, detail="Data manager not initialized")

    try:
        search_results = data_manager.search_colleges(
            rank, category, quota, branch
        )
        
        results_df = pd.DataFrame(search_results['results'])
        
        output = io.StringIO()
        results_df.to_csv(output, index=False)
        
        response = StreamingResponse(
            iter([output.getvalue()]), 
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=college_results.csv"}
        )
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optional: Add an error page template
@app.get("/error")
async def error_page(request: Request):
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "An unexpected error occurred"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
