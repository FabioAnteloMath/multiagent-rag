import uvicorn
import sys

if __name__ == "__main__":
    print("Starting server on port 8011...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8011,
        log_level="info",
        reload=False
    )