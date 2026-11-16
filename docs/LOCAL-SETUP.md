# Running Inceptiondesign locally

The whole platform is built and tested on your computer, through phase 18. Hosting starts only at launch (phase 19), on a server outside the office (see `docs/plan/hosting-options.md`).

There are two levels:
- **Level 1** shows you ERPNext itself in about 10 minutes.
- **Level 2** is the real development environment that Claude Code works in.

## What you need

| Item | Notes |
|---|---|
| A computer with **16 GB RAM** (8 GB minimum) | Docker needs at least 8 GB for ERPNext. A `bench build` that dies with exit code 137 means it ran out of memory. |
| ~30 GB free disk | |
| **Docker Desktop** (Windows/macOS) or Docker Engine (Linux) | In Docker Desktop → Settings → Resources, give Docker at least 8 GB of memory. |
| **Git** | On Windows, also use **Git Bash** (or WSL2 Ubuntu) for all commands — not CMD or PowerShell. |
| **VS Code** + the **Dev Containers** extension | `code --install-extension ms-vscode-remote.remote-containers` |
| **Claude Code** | Installed on your machine. |

Platform notes:
- **Windows:** use the WSL2 backend in Docker Desktop. Cloning the repo inside the WSL2 Linux filesystem (for example `~/code`) is much faster than cloning into `C:\`.
- **macOS (Apple Silicon):** if containers fail to start, switch Docker Desktop's virtualization to "Apple Virtualization Framework".

## Level 1 — see ERPNext in 10 minutes (throwaway demo)

```bash
git clone https://github.com/frappe/frappe_docker
cd frappe_docker
docker compose -f pwd.yml up -d
```

1. Wait 2–5 minutes. You can follow progress with `docker compose -f pwd.yml logs -f create-site`.
2. Open http://localhost:8080 and log in as `Administrator` / `admin`.
3. Click through Projects, Customers, Sales Invoice and Lead to get a feel for what we reuse.

This demo cannot install custom apps. Delete it when done:

```bash
docker compose -f pwd.yml down -v
```

## Level 2 — the development environment

### 1. Get frappe_docker and the devcontainer config

```bash
mkdir -p ~/code && cd ~/code
git clone https://github.com/frappe/frappe_docker inceptiondesign-dev
cd inceptiondesign-dev
cp -R devcontainer-example .devcontainer
cp -R development/vscode-example development/.vscode
code .
```

### 2. Open in the container

In VS Code, open the Command Palette and run **Dev Containers: Reopen in Container**. The first build takes 5–15 minutes. Everything below runs in the VS Code terminal **inside** the container.

### 3. Set Node 24, Python 3.14 and Yarn

```bash
nvm install 24 && nvm use 24 && nvm alias default 24
pyenv install 3.14 && pyenv global 3.14
corepack enable && corepack prepare yarn@1.22.22 --activate
node -v && python --version && yarn -v
```

If `pyenv install 3.14` asks for an exact version, run `pyenv install --list | grep 3.14` and use the newest `3.14.x`.

### 4. Create the bench and the site

```bash
cd /workspace/development
bench init --skip-redis-config-generation --frappe-branch version-16 frappe-bench
cd frappe-bench
bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379

bench get-app --branch version-16 --resolve-deps erpnext
bench new-site inceptiondesign.localhost --db-root-password 123 --admin-password admin \
  --mariadb-user-host-login-scope=%
bench --site inceptiondesign.localhost install-app erpnext
bench --site inceptiondesign.localhost set-config developer_mode 1
bench use inceptiondesign.localhost
bench start
```

The passwords `123` and `admin` are for your laptop only. Never use them on a server.

### 5. Open it

Open http://inceptiondesign.localhost:8000 and log in as `Administrator` / `admin`. The setup wizard appears; choose:
- **Language:** Arabic
- **Country:** Egypt
- **Currency:** EGP
- **Time zone:** Africa/Cairo

If `inceptiondesign.localhost` does not resolve on your machine, add `127.0.0.1 inceptiondesign.localhost` to your hosts file:
- `/etc/hosts` on Linux and macOS
- `C:\Windows\System32\drivers\etc\hosts` on Windows

### 6. Get the code and hand over to Claude Code

Phases 0 and 1 were started in a Claude cloud session and pushed to GitHub (`ammarshatta/inception-design`). They were written without a running ERPNext, so the first job on your computer is to install and test them.

```bash
cd /workspace/development/frappe-bench
bench get-app construction_core https://github.com/ammarshatta/inception-design.git
cd apps/construction_core && yarn install && cd ../..
bench --site inceptiondesign.localhost install-app construction_core
bench --site inceptiondesign.localhost migrate
bench build --app construction_core
bench --site inceptiondesign.localhost set-config allow_tests true
bench --site inceptiondesign.localhost run-tests --app construction_core
```

If the repo is private, `bench get-app` asks for your GitHub login. Use a personal access token as the password, or clone with SSH.

Then start Claude Code inside the app folder and send this message:

```bash
cd /workspace/development/frappe-bench/apps/construction_core
claude
```

```text
Read CLAUDE.md, docs/progress/PROGRESS.md and docs/progress/phase-0.md and phase-1.md.
Phases 0 and 1 were written in a cloud session without a running site.
Install and test them on this bench, fix what fails, and fill in the "Verified on the
owner's computer" sections with pass/fail and evidence for every acceptance criterion.
Do not start phase 2 until I approve.
```

For every next phase, start a **new** Claude Code session in `apps/construction_core`:
"Work on phase N only. Read docs/plan/phase-NN-….md and docs/backlog/phase-NN.md. Write your plan in docs/progress/phase-N.md and wait for my approval."

## Daily use

- Start the server: open the folder in VS Code → Reopen in Container → `cd frappe-bench && bench start`.
- Stop: press `Ctrl+C`, then close VS Code. Docker keeps the database between sessions.
- **Reset everything:** delete the containers and volumes from Docker Desktop. This deletes your local data.

## Common problems

| Symptom | Fix |
|---|---|
| `bench build` exits with 137 | Give Docker more memory (Settings → Resources) |
| Site does not open on `inceptiondesign.localhost` | Add the hosts-file line above, or open `http://localhost:8000` |
| Very slow on Windows | Keep the project inside WSL2 (`~/code`), not on `C:\` |
| CSRF errors when using the portal dev server (port 8080) | `bench --site inceptiondesign.localhost set-config ignore_csrf 1` — **local only**, never on a server |
