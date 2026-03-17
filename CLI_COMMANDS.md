# PYTHON DEVELOPMENT GUIDE

# PYTHON VIRTUAL ENVIRONMENT COMMANDS

    1. Delete the existing virtual environment (optional):
        Remove-Item -Recurse -Force python_environment
        Remove-Item -Recurse -Force zvenv

    2. Create a new virtual environment:
        python -m venv python_environment
        python -m venv zvenv
        
    3. Activate the virtual environment:
        Windows:
        .\python_environment\Scripts\activate
        .\zvenv\Scripts\activate
        
        macOS/Linux:
        source python_environment/bin/activate
        source zvenv/bin/activate

    4.  Install pip-tools to help with resolving dependencies:
        pip install pip-tools

    5. Compile dependencies from `requirements.in` to generate a locked `requirements.txt`:
            pip-compile requirements.in

    6. Install the required packages:
        pip install -r requirements.txt

    7. To clean up all installed packages and start fresh (optional):
        Windows:
        pip freeze | ForEach-Object { pip uninstall -y $_ }
        
        macOS/Linux:
        pip freeze | xargs pip uninstall -y
        

    8. To deactivate the virtual environment:
        deactivate

# To execute the code
    streamlit run src/notice_generation/ui/app.py

# FASTAPI APPLICATION COMMANDS

    1. Run FastAPI application with uvicorn:
        uvicorn main:app --reload

        # From the project root (ai-reports-and-notices/)
        uvicorn src.notice_generation.api_service.main:app --reload

        #From inside the api_service directory
        cd src/notice_generation/api_service
        uvicorn main:app --reload

    2. To run the app if this script is executed directly:
        if __name__ == "__main__":
            import uvicorn
            uvicorn.run("file_chat:app", host="127.0.0.1", port=8000, reload=True)

# DOCKER FILE GUIDE

## USING `docker-compose.yml`  
    The following outlines the steps and commands used to get Docker running for Chroma and FastAPI.

    1. Install Docker
            
            First, ensure Docker is installed on your machine. You can download and install Docker Desktop from the official website: https://www.docker.com/products/docker-desktop.

            After installation, verify Docker is working by running:

            ```bash
            docker --version
            ```

    2. Build the Docker Image and Start the Chroma Container

            In your project directory, ensure you have a `docker-compose.yml` file and a `Dockerfile` for Chroma setup.

            To pull the Docker image for Chroma (replace with your desired version):

            ```bash
            docker pull ghcr.io/chroma-core/chroma:0.5.20
            ```

            To build and start the container, use the following command:

            ```bash
            docker-compose up
            ```

            This command will pull the necessary images, build the container, and run it. You should see logs similar to:

            ```
            chroma_docker  | Starting 'uvicorn chromadb.app:app' with args: --workers 1 --host 0.0.0.0 --port 8000 --proxy-headers --log-config chromadb/log_config.yml --timeout-keep-alive 30
            chroma_docker  | Uvicorn running on http://0.0.0.0:8000
            ```

    3. Check Docker Container Status

            After running `docker-compose up`, you can verify the status of the Chroma container using:

            ```bash
            docker ps
            ```

            This will show the running containers. Example output:

            ```
            CONTAINER ID   IMAGE                               COMMAND                  CREATED         STATUS         PORTS                    NAMES
            cccc5bfbd477   ghcr.io/chroma-core/chroma:0.5.20   "/docker_entrypoint.…"   2 minutes ago   Up 2 minutes   0.0.0.0:8800->8000/tcp   chroma_docker
            ```

            You should see the container running with the ports correctly mapped.

    4. Access Chroma's Interface

            Chroma's API should now be running and accessible at:

            ```
            http://127.0.0.1:8800
            ```

            The default port mapping is `8000` inside the container and `8800` on your local machine, as defined in the `docker-compose.yml` file.

    5. Check Logs of Running Container

            If you need to troubleshoot or view logs of the running Chroma container, use:

            ```bash
            docker logs chroma_docker
            ```

            This will display the logs and can help you understand any errors or status messages from the container.

    6. Running FastAPI

            With Docker running Chroma, now you can run your FastAPI application. Assuming your FastAPI app is in a file like `main.py`, you can start it with:

            ```bash
            uvicorn main:app --reload
            ```

            Make sure your FastAPI app is set to interact with Chroma, and visit `http://127.0.0.1:8001/docs` to view the API documentation.

    7. Stopping Docker Containers

            - Check Docker Version:
                ```bash
                docker --version
                ```

            - Run Docker Compose:
                ```bash
                docker-compose up
                ```

            - Check Running Containers:
                ```bash
                docker ps
            ```

            - View Logs of a Container:
                ```bash
                docker logs <container_name_or_id>
                ```

            - Stop Docker Containers:
                ```bash
                docker-compose down
                ```
## USING `gunicorn.config.py`  
    Ensure you have the following files in the same directory as your Dockerfile:
        - `requirements.txt` (List of Python dependencies)
        - `gunicorn.config.py` (Your Gunicorn configuration)
        - Your application code (e.g., `main.py` with app being the FastAPI or other WSGI/ASGI application).
        
        If any of these are missing, you need to create or obtain them.

    Build the Docker Image
        - docker build -t your_image_name .
            - docker build -t test_local_files .

    Run the Docker Container
        - docker run -d -p 8003:8003 --name your_container_name your_image_name
            - docker run -d -p 8003:8003 --name test_container test_local_files

# MEMORY PROFILING
     - python -m memory_profiler main.py

# GIT WORKFLOW GUIDE

This guide provides a **step-by-step workflow** for managing code changes using Git. Follow these steps to ensure smooth collaboration and keep your local branch up to date with `master`.

---

## **1. Clone the Repository (Only for First Time Setup)**
If you haven't cloned the repository yet:
```bash
# Clone the repository from remote
git clone <repository-url>

# Navigate to the project directory
cd <repository-name>
```

---

## **2. Create & Switch to a New Branch**
Always create a separate branch to work on new changes.
```bash
# Fetch latest changes from remote
git fetch origin

# Create a new branch based on the latest master
git checkout -b my-feature-branch origin/master
```

---

## **3. Make Changes & Track Them**
After making your changes, check what files were modified:
```bash
git status
```

---

## **4. Stage & Commit Changes**
Once you're ready to save your progress:
```bash
# Stage all changes
git add .

# Commit changes with a descriptive message
git commit -m "Added feature XYZ"
```

---

## **5. Push Changes & Create a PR**
Push your branch to remote and raise a pull request:
```bash
# Push changes to remote
git push origin my-feature-branch
```
Then, go to GitHub/GitLab/Bitbucket and create a **Pull Request (PR)** from `my-feature-branch` → `master`.

---

## **6. Keep Your Local Branch Updated with `master`**
While waiting for your PR to be reviewed, keep your branch updated:
```bash
# Fetch latest changes
git fetch origin

# Rebase your branch with master
git rebase origin/master
```

💡 If there are conflicts, resolve them, then continue:
```bash
git add .
git rebase --continue
```

---

## **7. After PR is Merged: Update Local Master & Branch**
Once your PR is merged, ensure both your **local master** and **local branch** are updated:
```bash
# Fetch latest changes from remote
git fetch origin

# Reset local master to match remote master
git checkout master
git reset --hard origin/master

# Switch back to your branch and rebase with updated master
git checkout my-feature-branch
git rebase origin/master
```

💡 Now, your local branch is fully updated with the latest master without switching to local master.

---

## **8. Start a New Task? Repeat the Process!**
When starting a new task, always:
1. **Pull latest `master` from remote**
2. **Create a new branch**
3. **Repeat the workflow** 🚀