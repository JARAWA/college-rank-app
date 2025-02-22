from fastapi import FastAPI, Request, Form, HTTPException, Header
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MHTCET College Finder",
    description="Advanced college suggestion tool for MHTCET 2025",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

class DataManager:
    def __init__(self, file_path):
        logger.info(f"Initializing DataManager with file path: {file_path}")
        self.original_df = self.load_data(file_path)
        self.df = self.original_df.copy()
        self.categories = self.prepare_dropdown(self.df, 'category')
        self.quotas = self.prepare_dropdown(self.df, 'quota_type')
        self.branches = self.prepare_dropdown(self.df, 'branch_name')
        logger.info("DataManager initialization complete")

    def load_data(self, file_path):
        try:
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Attempting to load file: {file_path}")
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return pd.DataFrame()

            df = pd.read_csv(file_path, encoding='cp1252')
            
            required_columns = [
                'college_code', 'college_name', 'branch_code', 'branch_name', 
                'category_code', 'category', 'quota_type', 'allocation_type', 
                'rank', 'percentile'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing columns: {missing_columns}")
                return pd.DataFrame()

            logger.info(f"Successfully loaded dataframe with shape: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return pd.DataFrame()

    def prepare_dropdown(self, df, column):
        if df.empty:
            logger.warning(f"Empty DataFrame while preparing dropdown for {column}")
            return ["All"]
        
        options = ["All"] + sorted([
            str(x) for x in df[column].unique() 
            if pd.notna(x) and str(x).lower() != 'not specified'
        ])
        logger.info(f"Prepared {len(options)} options for {column}")
        return options

    def search_colleges(self, rank: int, category: str = "All", 
                       quota: str = "All", branch: str = "All"):
        try:
            df = self.original_df.copy()
            
            if df.empty:
                logger.warning("Empty DataFrame during search")
                return self.empty_search_result()

            logger.info(f"Search parameters: rank={rank}, category={category}, "
                       f"quota={quota}, branch={branch}")

            mask = (df['rank'] >= rank - 1000) & (df['rank'] <= rank + 1000)

            if category != "All":
                mask &= df['category'] == category
            if quota != "All":
                mask &= df['quota_type'] == quota
            if branch != "All":
                mask &= df['branch_name'] == branch

            results = df[mask].sort_values('rank')
            
            logger.info(f"Found {len(results)} matching results")

            return {
                'results': results.to_dict('records'),
                'total_matches': len(results),
                'rank_min': results['rank'].min() if not results.empty else 0,
                'rank_max': results['rank'].max() if not results.empty else 0,
                'unique_colleges': results['college_name'].nunique() if not results.empty else 0
            }
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return self.empty_search_result()

    def empty_search_result(self):
        return {
            'results': [],
            'total_matches': 0,
            'rank_min': 0,
            'rank_max': 0,
            'unique_colleges': 0
        }

# Initialize data manager
try:
    DATA_FILE_PATH = os.path.join(os.getcwd(), 'Structured_MHTCET_Cutoffs_with_validation.csv')
    data_manager = DataManager(DATA_FILE_PATH)
except Exception as e:
    logger.error(f"Failed to initialize DataManager: {str(e)}")
    data_manager = None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if data_manager is None:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Data file could not be loaded"}
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
        logger.error(f"Search error: {str(e)}")
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
    try:
        if data_manager is None:
            raise HTTPException(status_code=500, detail="Data manager not initialized")

        search_results = data_manager.search_colleges(rank, category, quota, branch)
        
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
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "data_loaded": data_manager is not None,
        "data_size": len(data_manager.original_df) if data_manager is not None else 0
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
