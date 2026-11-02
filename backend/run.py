import uvicorn

from app import BACKEND_HOST, BACKEND_PORT

if __name__ == "__main__":
    uvicorn.run("app:app", host=BACKEND_HOST, port=BACKEND_PORT)
