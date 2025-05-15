import logging
import os
import tempfile

from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from markitdown import MarkItDown

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MarkItDown API Server",
    description="API endpoint to extract text and convert it to markdown, using MarkItDown (https://github.com/microsoft/markitdown).",
)

# Получаем токен из переменных окружения
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    logger.warning(f"API_TOKEN environment variable not set")
    raise RuntimeError("API_TOKEN environment variable not set")

# Проверка токена
def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        logger.warning(f"Invalid Authorization header format: {authorization}")
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        logger.warning(f"Invalid token value received: {token}")
        raise HTTPException(status_code=403, detail="Invalid API token")

FORBIDDEN_EXTENSIONS = [
    # список оставлен без изменений
    "exe", "msi", "bat", "cmd", "dmg", "pkg", "app", "bin", "sh", "run", "dll", "so", "dylib", "jar", "apk",
    "vbs", "ps1", "pyc", "pyo", "sys", "drv", "config", "ini", "dat", "db", "sqlite", "mdb", "dbf", "myd",
    "dxf", "dwg", "stl", "obj", "3ds", "blend", "gpg", "asc", "pgp", "vdi", "vmdk", "ova", "docker",
    "containerd", "class", "o", "a", "lib", "ttf", "otf", "fon"
]

def is_forbidden_file(filename):
    return (
        "." in filename and filename.rsplit(".", 1)[1].lower() in FORBIDDEN_EXTENSIONS
    )

def convert_to_md(filepath: str) -> str:
    logger.info(f"Converting file: {filepath}")
    markitdown = MarkItDown()
    result = markitdown.convert(filepath)
    logger.info(f"Conversion result: {result.text_content[:100]}")
    return result.text_content

@app.get("/")
def read_root():
    return {"MarkItDown API Server": "hit /docs for endpoint reference"}

@app.post("/process_file")
async def process_file(
    file: UploadFile = File(...),
    _: str = Depends(verify_token)  # Авторизация
):
    if is_forbidden_file(file.filename):
        return JSONResponse(content={"error": "File type not allowed"}, status_code=400)

    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name
            logger.info(f"Temporary file path: {temp_file_path}")

        markdown_content = convert_to_md(temp_file_path)
        logger.info("File converted to markdown successfully")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Temporary file deleted: {temp_file_path}")

    return JSONResponse(content={"markdown": markdown_content})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8490)
