from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import pandas as pd
from typing import Optional

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Load data
df = pd.read_csv('Structured_MHTCET_Cutoffs_with_validation.csv', encoding='cp1252')

# Get unique values
categories = ["All"] + sorted([str(x) for x in df['category'].unique() if str(x) != 'nan' and str(x) != 'Not Specified'])
quotas = ["All"] + sorted([str(x) for x in df['quota_type'].unique() if str(x) != 'nan' and str(x) != 'Not Specified'])
branches = ["All"] + sorted([str(x) for x in df['branch_name'].unique() if str(x) != 'nan' and str(x) != 'Not Specified'])

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": categories,
            "quotas": quotas,
            "branches": branches
        }
    )

@app.post("/search")
async def search_colleges(
    request: Request,
    rank: int = Form(...),
    category: str = Form(default="All"),
    quota: str = Form(default="All"),
    branch: str = Form(default="All")
):
    try:
        mask = (df['rank'] >= rank - 1000) & (df['rank'] <= rank + 1000)

        if category != "All":
            mask &= df['category'] == category
        if quota != "All":
            mask &= df['quota_type'] == quota
        if branch != "All":
            mask &= df['branch_name'] == branch

        results = df[mask].sort_values('rank')
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "categories": categories,
                "quotas": quotas,
                "branches": branches,
                "results": results.to_dict('records'),
                "total_matches": len(results),
                "rank_min": results['rank'].min() if not results.empty else 0,
                "rank_max": results['rank'].max() if not results.empty else 0,
                "unique_colleges": results['college_name'].nunique() if not results.empty else 0
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "categories": categories,
                "quotas": quotas,
                "branches": branches,
                "error": str(e)
            }
        )
