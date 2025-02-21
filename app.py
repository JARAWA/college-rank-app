from fastapi import FastAPI
import pandas as pd
import os
import uvicorn

# Initialize FastAPI app
app = FastAPI()

# Load the CSV file
csv_path = "Structured_MHTCET_Cutoffs_with_validation.csv"

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path, encoding="ISO-8859-1")
else:
    raise FileNotFoundError(f"CSV file not found at {csv_path}")

@app.get("/")
def home():
    return {"message": "Welcome to the MHTCET College Finder API!"}

@app.get("/find_colleges")
def find_colleges(rank: int, category: str = None, quota: str = None, branch: str = None):
    """
    Endpoint to find colleges based on rank, category, quota, and branch.

    Parameters:
    - rank (int): User's MHTCET rank (required)
    - category (str): Category filter (optional)
    - quota (str): Quota type filter (optional)
    - branch (str): Branch filter (optional)

    Returns:
    - JSON list of matching colleges
    """

    if rank <= 0:
        return {"error": "Please enter a valid rank (greater than 0)"}

    # Filter colleges within ±1000 rank range
    mask = (df["rank"] >= rank - 1000) & (df["rank"] <= rank + 1000)

    if category and category.lower() != "all":
        mask &= df["category"].str.lower() == category.lower()
    if quota and quota.lower() != "all":
        mask &= df["quota_type"].str.lower() == quota.lower()
    if branch and branch.lower() != "all":
        mask &= df["branch_name"].str.lower() == branch.lower()

    results = df[mask].sort_values("rank")

    if results.empty:
        return {"message": "No colleges found matching your criteria."}

    return results.to_dict(orient="records")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
