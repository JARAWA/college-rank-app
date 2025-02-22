from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import List, Optional
import pandas as pd
import numpy as np
import os
import io

app = FastAPI(
    title="MHTCET College Finder",
    description="Advanced college suggestion tool for MHTCET 2025",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Global data management
class DataManager:
    def __init__(self, file_path):
        self.df = self.load_data(file_path)
        self.categories = self.prepare_dropdown(self.df, 'category')
        self.quotas = self.prepare_dropdown(self.df, 'quota_type')
        self.branches = self.prepare_dropdown(self.df, 'branch_name')

    def load_data(self, file_path):
        try:
            df = pd.read_csv(file_path, encoding='cp1252')
            return df
        except Exception as e:
            print(f"Data loading error: {e}")
            return pd.DataFrame()

    def prepare_dropdown(self, df, column):
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
        mask = (self.df['rank'] >= rank - 1000) & (self.df['rank'] <= rank + 1000)

        if category != "All":
            mask &= self.df['category'] == category
        if quota != "All":
            mask &= self.df['quota_type'] == quota
        if branch != "All":
            mask &= self.df['branch_name'] == branch

        results = self.df[mask].sort_values('rank')
        
        return {
            'results': results.to_dict('records'),
            'total_matches': len(results),
            'rank_min': results['rank'].min() if not results.empty else 0,
            'rank_max': results['rank'].max() if not results.empty else 0,
            'unique_colleges': results['college_name'].nunique() if not results.empty else 0
        }

# Initialize data manager
data_manager = DataManager('Structured_MHTCET_Cutoffs_with_validation.csv')

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
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
    try:
        search_results = data_manager.search_colleges(
            rank, category, quota, branch
        )
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "categories": data_manager.categories,
            "quotas": data_manager.quotas,
            "branches": data_manager.branches,
            **search_results
        })
    except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
