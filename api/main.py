from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd, json, shutil, os, re, pytesseract
from PIL import Image

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    path = f"{UPLOAD_DIR}/{file.filename}"
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    text = pytesseract.image_to_string(Image.open(path))
    data = parse_text(text)
    return {"rows": len(data)}

@app.get("/insights")
def insights():
    df = load_all_json()
    best_hour = int(df.groupby(df['timestamp'].dt.hour)['revenue'].mean().idxmax())
    top_posts = df.nlargest(3, 'revenue')[['caption','revenue']].to_dict('records')
    trend = df.set_index('timestamp')['revenue'].resample('7D').sum().pct_change().iloc[-1]
    return {"best_hour": best_hour, "top_posts": top_posts, "trend": trend}

def parse_text(txt: str):
    rows = re.findall(r'(\d{4}-\d{2}-\d{2}).*\$(\d+\.?\d*).*\n([^\n]+)', txt)
    return [{"timestamp": pd.to_datetime(d), "revenue": float(r), "caption": c} for d, r, c in rows]

def load_all_json():
    frames = []
    for j in os.listdir(UPLOAD_DIR):
        if j.endswith(".json"):
            frames.append(pd.read_json(f"{UPLOAD_DIR}/{j}"))
    df = pd.concat(frames, ignore_index=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df
