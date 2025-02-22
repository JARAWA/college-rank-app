from fastapi import FastAPI, Request, Form, HTTPException, Header
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import pandas as pd
import numpy as np
import os
import io
import logging
import datetime
from typing import Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MHTCET College Finder",
    description="Advanced college suggestion tool for MHTCET 2025",
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # In production, replace with your actual domain
)

# Setup static files and templates
static_path = Path("static")
templates_path = Path("templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

class DataManager:
    def __init__(self, file_path: str):
        """Initialize the DataManager with the CSV file path."""
        logger.info(f"Initializing DataManager with file path: {file_path}")
        self.file_path = file_path
        self.original_df = self.load_data()
        self.df = self.original_df.copy() if not self.original_df.empty else pd.DataFrame()
        self.initialize_dropdowns()
        self.last_reload = datetime.datetime.now()

    def load_data(self) -> pd.DataFrame:
        """Load and validate the CSV data."""
        try:
            if not os.path.exists(self.file_path):
                logger.error(f"File not found: {self.file_path}")
                return pd.DataFrame()

            df = pd.read_csv(self.file_path, encoding='cp1252')
            
            required_columns = [
                'college_code', 'college_name', 'branch_code', 'branch_name',
                'category_code', 'category', 'quota_type', 'allocation_type',
                'rank', 'percentile'
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing columns: {missing_columns}")
                return pd.DataFrame()

            # Data cleaning and validation
            df = df.dropna(subset=['rank', 'college_name', 'branch_name'])
            df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
            df = df.dropna(subset=['rank'])

            logger.info(f"Successfully loaded {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"Error loading data: {str(e)}", exc_info=True)
            return pd.DataFrame()

    def initialize_dropdowns(self):
        """Initialize dropdown options."""
        if self.df.empty:
            self.categories = ["All"]
            self.quotas = ["All"]
            self.branches = ["All"]
            return

        self.categories = self.prepare_dropdown('category')
        self.quotas = self.prepare_dropdown('quota_type')
        self.branches = self.prepare_dropdown('branch_name')

    def prepare_dropdown(self, column: str) -> list:
        """Prepare dropdown options for a given column."""
        if self.df.empty:
            return ["All"]
        
        options = ["All"] + sorted([
            str(x) for x in self.df[column].unique() 
            if pd.notna(x) and str(x).lower() != 'not specified'
        ])
        logger.debug(f"Prepared {len(options)} options for {column}")
        return options

    def search_colleges(
        self, 
        rank: int, 
        category: str = "All", 
        quota: str = "All", 
        branch: str = "All",
        rank_range: int = 1000
    ) -> dict:
        """Search colleges based on given criteria."""
        try:
            if self.df.empty:
                logger.warning("Search attempted on empty DataFrame")
                return self.empty_search_result()

            logger.info(f"Searching with parameters: rank={rank}, category={category}, "
                       f"quota={quota}, branch={branch}")

            # Create base mask for rank range
            mask = (self.df['rank'] >= rank - rank_range) & (self.df['rank'] <= rank + rank_range)

            # Apply additional filters
            if category != "All":
                mask &= self.df['category'] == category
            if quota != "All":
                mask &= self.df['quota_type'] == quota
            if branch != "All":
                mask &= self.df['branch_name'] == branch

            # Apply mask and sort results
            results = self.df[mask].sort_values('rank')
            
            logger.info(f"Found {len(results)} matching results")

            return {
                'results': results.to_dict('records'),
                'total_matches': len(results),
                'rank_min': results['rank'].min() if not results.empty else 0,
                'rank_max': results['rank'].max() if not results.empty else 0,
                'unique_colleges': results['college_name'].nunique() if not results.empty else 0
            }

        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return self.empty_search_result()

    def empty_search_result(self) -> dict:
        """Return empty search result structure."""
        return {
            'results': [],
            'total_matches': 0,
            'rank_min': 0,
            'rank_max': 0,
            'unique_colleges': 0
        }

# Initialize DataManager
try:
    DATA_FILE_PATH = os.path.join(os.getcwd(), 'Structured_MHTCET_Cutoffs_with_validation.csv')
    data_manager = DataManager(DATA_FILE_PATH)
except Exception as e:
    logger.error(f"Failed to initialize DataManager: {str(e)}", exc_info=True)
    data_manager = None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page route."""
    if data_manager is None:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Application is not properly initialized"}
        )
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": data_manager.categories,
            "quotas": data_manager.quotas,
            "branches": data_manager.branches
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
    """Search colleges endpoint."""
    try:
        if data_manager is None:
            raise HTTPException(status_code=500, detail="Data manager not initialized")

        search_results = data_manager.search_colleges(rank, category, quota, branch)
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "categories": data_manager.categories,
                "quotas": data_manager.quotas,
                "branches": data_manager.branches,
                "rank": rank,
                "category": category,
                "quota": quota,
                "branch": branch,
                **search_results
            }
        )
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": str(e)}
        )

@app.post("/export")
async def export_results(
    request: Request,
    rank: int = Form(...),
    category: str = Form(default="All"),
    quota: str = Form(default="All"),
    branch: str = Form(default="All")
):
    """Export search results to CSV."""
    try:
        if data_manager is None:
            raise HTTPException(status_code=500, detail="Data manager not initialized")

        search_results = data_manager.search_colleges(rank, category, quota, branch)
        
        if not search_results['results']:
            raise HTTPException(status_code=404, detail="No results to export")

        results_df = pd.DataFrame(search_results['results'])
        
        output = io.StringIO()
        results_df.to_csv(output, index=False)
        
        response = StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=college_results.csv"
            }
        )
        return response

    except Exception as e:
        logger.error(f"Export error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "data_loaded": data_manager is not None,
        "data_size": len(data_manager.original_df) if data_manager is not None else 0,
        "last_reload": data_manager.last_reload.isoformat() if data_manager is not None else None
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Global error: {exc}", exc_info=True)
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
