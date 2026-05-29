import threading
import uvicorn
from signup import app as flask_app
from main import app as fastapi_app

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000, debug=False)

def run_fastapi():
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_flask, daemon=True)
    t2 = threading.Thread(target=run_fastapi, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
