set dotenv-load := true

branch := "dev"

default:
    @just --list --justfile {{ justfile() }}

sync:
    rye sync

install:
    rye sync --no-lock

start:
    docker compose up --build -d

stop:
    docker compose down

log:
    docker compose logs -f

pull branch=branch:
    git checkout {{ branch }}
    git pull origin {{ branch }}

update branch=branch: stop (pull branch) start


api:
    rye run uvicorn src.omnimcp_be.app:app --port 7001

dev:
	if command -v watchexec >/dev/null 2>&1; then \
		watchexec \
			--watch src \
			--exts py \
			--on-busy-update=restart \
			--stop-signal SIGKILL \
			-- rye run uvicorn src.omnimcp_be.app:app --port 7001 --app-dir src/; \
	else \
		rye run uvicorn src.omnimcp_be.app:app --port 7001 --reload; \
	fi

setup:
    # Rye
    curl -sSf https://rye-up.com/get | bash
    echo 'source "$HOME/.rye/env"' >> ~/.bashrc

    # Direnv
    curl -sfL https://direnv.net/install.sh | bash
    echo 'eval "$(direnv hook bash)"' >> ~/.bashrc

    # Install git hooks
    just install-hooks

    @echo "Restart your shell to finish setup!"

format:
    # Format Python code with black and isort
    rye run isort --profile=black --skip-gitignore .
    rye run ruff check --fix --exit-zero .
    rye run ruff format .

format-file PATH:
    rye run isort --profile=black --skip-gitignore {{PATH}}
    rye run ruff check --fix --exit-zero {{PATH}}
    rye run ruff format {{PATH}}
    
install-hooks:
    #!/usr/bin/env sh
    # Create pre-commit config file
    rye add isort
    rye add ruff
    rye sync --no-lock
    cat > .pre-commit-config.yaml << 'EOF'
    repos:
    -   repo: https://github.com/pycqa/isort
        rev: 5.13.2
        hooks:
        -   id: isort
            args: ["--profile", "black", "--skip-gitignore"]
            
    -   repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.8.4
        hooks:
        -   id: ruff
            args: ["--fix", "--exit-zero"]
        -   id: ruff-format 
    EOF

    # Install pre-commit if not already installed
    if ! command -v pre-commit >/dev/null 2>&1; then
        rye add pre-commit
    fi

    # Install the pre-commit hooks
    pre-commit install

    echo "Pre-commit hooks installed successfully!"
