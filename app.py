from fastapi import FastAPI, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import pandas as pd
import os
from typing import List, Optional

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Load data
try:
    df = pd.read_csv('Structured_MHTCET_Cutoffs_with_validation.csv', encoding='cp1252')
    # Get unique values
    categories = ["All"] + sorted([str(x) for x in df['category'].unique() if str(x) != 'nan' and str(x) != 'Not Specified'])
    quotas = ["All"] + sorted([str(x) for x in df['quota_type'].unique() if str(x) != 'nan' and str(x) != 'Not Specified'])
    branches = ["All"] + sorted([str(x) for x in df['branch_name'].unique() if str(x) != 'nan' and str(x) != 'Not Specified'])
    colleges = ["All"] + sorted(df['college_name'].unique().tolist())
    cities = ["All"] + sorted(df['city'].unique().tolist()) if 'city' in df.columns else ["All"]
except Exception as e:
    print(f"Error loading data: {e}")
    categories = ["All"]
    quotas = ["All"]
    branches = ["All"]
    colleges = ["All"]
    cities = ["All"]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": categories,
            "quotas": quotas,
            "branches": branches,
            "colleges": colleges,
            "cities": cities
        }
    )

@app.post("/search")
async def search_colleges(
    request: Request,
    rank_min: Optional[int] = Form(None),
    rank_max: Optional[int] = Form(None),
    categories: List[str] = Form(default=["All"]),
    quotas: List[str] = Form(default=["All"]),
    branches: List[str] = Form(default=["All"]),
    college_name: str = Form(default="All"),
    city: str = Form(default="All"),
    sort_by: str = Form(default="rank"),
    sort_order: str = Form(default="asc"),
    page: int = Form(default=1),
    per_page: int = Form(default=50)
):
    try:
        # Initialize mask
        mask = pd.Series(True, index=df.index)

        # Apply rank range filter
        if rank_min is not None:
            mask &= df['rank'] >= rank_min
        if rank_max is not None:
            mask &= df['rank'] <= rank_max

        # Apply multiple category filter
        if "All" not in categories:
            mask &= df['category'].isin(categories)

        # Apply multiple quota filter
        if "All" not in quotas:
            mask &= df['quota_type'].isin(quotas)

        # Apply multiple branch filter
        if "All" not in branches:
            mask &= df['branch_name'].isin(branches)

        # Apply college name filter
        if college_name != "All":
            mask &= df['college_name'] == college_name

        # Apply city filter
        if city != "All" and 'city' in df.columns:
            mask &= df['city'] == city

        # Apply sorting
        results = df[mask].sort_values(
            by=sort_by,
            ascending=(sort_order == "asc")
        )

        # Calculate pagination
        total_results = len(results)
        total_pages = (total_results + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        # Get paginated results
        paginated_results = results.iloc[start_idx:end_idx]

        # Calculate statistics
        stats = {
            "total_matches": total_results,
            "rank_min": results['rank'].min() if not results.empty else 0,
            "rank_max": results['rank'].max() if not results.empty else 0,
            "unique_colleges": results['college_name'].nunique() if not results.empty else 0,
            "unique_branches": results['branch_name'].nunique() if not results.empty else 0
        }

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "categories": categories,
                "quotas": quotas,
                "branches": branches,
                "colleges": colleges,
                "cities": cities,
                "results": paginated_results.to_dict('records'),
                "stats": stats,
                "current_page": page,
                "total_pages": total_pages,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "selected_categories": categories,
                "selected_quotas": quotas,
                "selected_branches": branches,
                "selected_college": college_name,
                "selected_city": city,
                "selected_rank_min": rank_min,
                "selected_rank_max": rank_max
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
                "colleges": colleges,
                "cities": cities,
                "error": str(e)
            }
        )

@app.get("/api/colleges")
async def get_colleges(search: str = ""):
    colleges = df[df['college_name'].str.contains(search, case=False, na=False)]['college_name'].unique()
    return {"colleges": colleges.tolist()}
