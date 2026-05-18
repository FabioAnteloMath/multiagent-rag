import sys
sys.path.insert(0, 'C:/WorkSpace/Pessoal/multiagent-rag/backend')

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")