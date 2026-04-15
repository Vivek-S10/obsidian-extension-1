#!/bin/bash

# Function to run the backend
run_backend() {
    echo "Starting Backend..."
    export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
    ./venv/bin/uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
}

# Function to run the frontend
run_frontend() {
    echo "Starting Frontend..."
    cd frontend && npm run dev
}

# Main script logic
case "$1" in
    backend)
        run_backend
        ;;
    frontend)
        run_frontend
        ;;
    dev)
        echo "Starting both Backend and Frontend..."
        # Trap SIGINT (Ctrl+C) to kill both background processes
        trap 'kill %1; kill %2; exit' SIGINT SIGTERM EXIT
        
        run_backend &
        run_frontend &
        
        # Wait for both processes to complete
        wait
        ;;
    *)
        echo "Usage: $0 {backend|frontend|dev}"
        echo "  backend  : Run the FastAPI backend"
        echo "  frontend : Run the Vite/React frontend"
        echo "  dev      : Run both concurrently"
        exit 1
        ;;
esac
