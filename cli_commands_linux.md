# PYTHON DEVELOPMENT GUIDE - Ubuntu/Linux (AI/ML Edition)

## 0: System prep (once)

```bash
sudo apt update
sudo apt install -y build-essential git curl wget   libssl-dev libffi-dev zlib1g-dev libbz2-dev libreadline-dev   libsqlite3-dev libncursesw5-dev xz-utils tk-dev   libxml2-dev libxmlsec1-dev liblzma-dev
```

## 1: Virtual environments (simple + fast)

```bash
rm -rf python_environment
rm -rf venv

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

To uninstall everything in the environment:
```bash
pip freeze | xargs pip uninstall -y
```

## 2: Dependency management (pip-tools / poetry / uv)

### pip-tools
```bash
pip install pip-tools
pip-compile requirements.in
pip install -r requirements.txt
```

### Poetry
```bash
pip install poetry
poetry init
poetry add numpy pandas scikit-learn
poetry shell
```

### uv
```bash
pip install uv
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 3: Multiple Python versions (pyenv)

```bash
curl https://pyenv.run | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

pyenv install 3.12.6
pyenv local 3.12.6
python -m venv .venv && source .venv/bin/activate
```

## 4: AI/ML core packages

```bash
pip install numpy pandas scipy matplotlib seaborn jupyterlab ipykernel             scikit-learn polars pyarrow fastparquet             requests beautifulsoup4 lxml pydantic[dotenv]             black isort ruff mypy pre-commit pytest
python -m ipykernel install --user --name $(basename "$PWD")
```

### PyTorch (CPU or CUDA)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# or CUDA:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### TensorFlow
```bash
pip install tensorflow
```

## 5: Jupyter & VS Code

```bash
pip install jupyterlab
jupyter lab
sudo snap install code --classic
```

## 6: FastAPI

```bash
uvicorn main:app --reload
```

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("file_chat:app", host="127.0.0.1", port=8000, reload=True)
```

## 7: Docker + NVIDIA Toolkit

```bash
sudo apt remove -y docker docker.io containerd runc 2>/dev/null || true
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

### GPU toolkit
```bash
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure
sudo systemctl restart docker
```

### Docker commands
```bash
docker compose up
docker ps
docker logs <container>
docker compose down
```

## 8: Git workflow

Standard workflow:
```bash
git checkout -b feature/branch
git add .
git commit -m "commit msg"
git push origin feature/branch
```

Rebase with master:
```bash
git checkout master
git fetch origin master
git rebase origin/master
```

## 9: Code quality & pre-commit

```bash
pip install black isort ruff mypy pre-commit
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks: [{ id: black }]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks: [{ id: ruff }, { id: ruff-format }]
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks: [{ id: isort }]
EOF
pre-commit install
```

## 10: Terminal QoL (bash)

```bash
echo 'export PYTHONDONTWRITEBYTECODE=1' >> ~/.bashrc
echo 'export PIP_DISABLE_PIP_VERSION_CHECK=1' >> ~/.bashrc
echo "alias act='source .venv/bin/activate'" >> ~/.bashrc
echo "alias pipu='python -m pip install --upgrade pip'" >> ~/.bashrc
source ~/.bashrc
```

## 11: GPU sanity checks

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

## 12: Profiling

```bash
pip install memory_profiler line_profiler
python -m memory_profiler main.py
kernprof -l script.py && python -m line_profiler script.py.lprof
```

## 13: Project layout

```
my-ml-app/
  .venv/
  src/
    app/main.py
  notebooks/
    01_explore.ipynb
  tests/
    test_basic.py
  requirements.in
  requirements.txt
  .pre-commit-config.yaml
  README.md
```
