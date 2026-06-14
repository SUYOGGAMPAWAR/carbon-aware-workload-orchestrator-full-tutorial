# 🌍 Carbon-Aware Workload Orchestrator — Full Beginner Tutorial

A complete, step-by-step guide to building and running a **"GreenOps" Carbon-Aware Workload Orchestrator** — a small system that automatically shifts a cloud workload between two regions (US-East and India) based on which region has *lower carbon emissions* at that moment, and commits the change to GitHub like a real GitOps pipeline.

This README assumes **zero prior experience** with Docker, Kubernetes, or the GitHub API. Follow it top to bottom and you'll end up with a working pipeline running locally, in Docker, and (optionally) on Kubernetes.

> 📁 This repo (`carbon-aware-workload-orchestrator-full-tutorial`) contains the **automation script** (the "brain").
> 📁 The companion repo, [`Carbon-Aware-Workload-Orchestrator`](https://github.com/SUYOGGAMPAWAR/Carbon-Aware-Workload-Orchestrator), contains the **Kubernetes manifests** (the "hands/feet") that actually get edited by the script.

---

## 📖 1. What Does This Project Actually Do?

Imagine you run a website (`enterprise-web-app`) that can live in two data center regions:

| Region    | Location   | Manifest file in 2nd repo     |
|-----------|------------|--------------------------------|
| `us-east` | Virginia   | `us-east/deployment.yaml`      |
| `india`   | Maharashtra| `india/deployment.yaml`        |

Every few minutes, a script (`carbon_router.py`) checks **how "dirty" the electricity grid is** in each region (i.e., how much CO₂ is produced per kWh). Whichever region currently has the **cleaner** grid gets `replicas: 3` (the app runs there), and the dirtier region gets `replicas: 0` (the app is turned off there).

The script then **pushes those changes directly to the GitHub repo** holding the Kubernetes YAML files — exactly like a human engineer (or a GitOps tool like ArgoCD) would.

Because real-time carbon data APIs usually require paid API keys, this tutorial uses a **mock function** (`get_mock_carbon_intensity`) that generates realistic-looking random emission numbers, so you can run the whole thing for free.

---

## 🏗️ 2. How It All Fits Together (Architecture)

```
            ┌─────────────────────────┐
            │   carbon_router.py       │
            │   (runs every 5 min,     │
            │    inside a Docker       │
            │    container, on a       │
            │    Kubernetes CronJob)   │
            └────────────┬─────────────┘
                          │
              1. Checks "carbon intensity"
                 for us-east & india (mocked)
                          │
                          ▼
              2. Picks the cleaner region
                          │
                          ▼
            ┌─────────────────────────────┐
            │  GitHub API (via PyGithub)   │
            │  Edits deployment.yaml files │
            │  in the 2nd repo and commits │
            └──────────────┬────────────────┘
                            │
                            ▼
        Carbon-Aware-Workload-Orchestrator (repo #2)
        ├── us-east/deployment.yaml   (replicas: 3 or 0)
        └── india/deployment.yaml     (replicas: 3 or 0)
```

In a real production setup, a GitOps tool (ArgoCD/Flux) watching repo #2 would then sync these changes to an actual Kubernetes cluster — scaling the app up in the cleaner region and down in the other.

---

## ✅ 3. Prerequisites

You'll need the following tools. Don't worry — Step 4 walks through installing every single one.

- A **GitHub account** (free)
- **Git**
- **Python 3.11+** and **pip**
- **Docker Desktop**
- (Optional, for the Kubernetes part) **kubectl** and **minikube**
- A code editor like **VS Code**

---

## 🧰 4. Step-by-Step Setup

### Step 4.1 — Install the basic tools

#### 🪟 Windows users

The easiest way is **Chocolatey** (a package manager for Windows).

> ⚠️ **Most common beginner mistake:** Chocolatey **only installs/works correctly when your terminal is running as Administrator**. If you open a normal PowerShell window, the installer will silently fail or `choco` won't be recognized afterward.

1. Press the **Start menu**, type `PowerShell`, then **right-click → "Run as administrator"**.
2. Install Chocolatey by pasting:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; `
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```
3. **Close and reopen PowerShell as Administrator again** (this matters — `choco` won't be on your PATH in the old window).
4. Install everything else:
   ```powershell
   choco install git python docker-desktop kubernetes-cli kubernetes-helm minikube -y
   ```
5. Restart your computer once Docker Desktop finishes installing (it usually asks for this).

#### 🍎 macOS users

```bash
brew install git python docker kubectl minikube
```
Then start the Docker Desktop app from Launchpad at least once.

#### 🐧 Linux (Ubuntu/Debian) users

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER   # then log out and back in
# kubectl + minikube (optional, see official docs for latest links)
```

---

### Step 4.2 — Fork the "manifest" repository (repo #2)

The script needs **write access** to a GitHub repo so it can edit YAML files and commit. You cannot let it push to *someone else's* repo — so fork it first.

1. Go to: **https://github.com/SUYOGGAMPAWAR/Carbon-Aware-Workload-Orchestrator**
2. Click **Fork** (top-right) → fork it into **your own GitHub account**.
3. Note your fork's full name, e.g. `yourusername/Carbon-Aware-Workload-Orchestrator`. You'll need this in Step 4.5.

This repo just contains two small files:
```
Carbon-Aware-Workload-Orchestrator/
├── us-east/deployment.yaml   (a Kubernetes Deployment, currently replicas: 3)
└── india/deployment.yaml     (a Kubernetes Deployment, currently replicas: 0)
```

---

### Step 4.3 — Create a GitHub Personal Access Token (PAT)

The script authenticates to GitHub using a token, not your password.

1. On GitHub, click your profile picture (top-right) → **Settings**.
2. Scroll all the way down the left sidebar → **Developer settings**.
3. Click **Personal access tokens → Tokens (classic)**.
4. Click **Generate new token → Generate new token (classic)**.
5. Give it a name (e.g. `greenops-router`), pick an expiration date.
6. ✅ Check the box for the **`repo`** scope (this gives full read/write access to your repositories — required to edit files and commit).
7. Click **Generate token**, then **copy it immediately** — GitHub only shows it once.

> ⚠️ Treat this token like a password. Never commit it to a public repo or paste it into chat. If you lose it, just generate a new one.

---

### Step 4.4 — Clone this tutorial repository

```bash
git clone https://github.com/SUYOGGAMPAWAR/carbon-aware-workload-orchestrator-full-tutorial.git
cd carbon-aware-workload-orchestrator-full-tutorial
```

---

### Step 4.5 — Fix and configure `carbon_router.py`

The script as written has **one small bug** you need to fix, plus **one value you must personalize**.

Open `carbon_router.py` in your editor:

1. **Add a missing import.** At the very top of the file, add:
   ```python
   import os
   ```
   (Without this, the script crashes with `NameError: name 'os' is not defined` on the very first line that reads `GITHUB_TOKEN`.)

2. **Point it at YOUR fork.** Change this line:
   ```python
   REPO_NAME = "SUYOGGAMPAWAR/Carbon-Aware-Workload-Orchestrator"
   ```
   to:
   ```python
   REPO_NAME = "yourusername/Carbon-Aware-Workload-Orchestrator"
   ```
   (Use the fork you created in Step 4.2. If you skip this, the script will either fail with a permissions error or — worse — try to push to someone else's repo and fail.)

---

### Step 4.6 — Set up Python and install dependencies

Create a virtual environment (keeps this project's packages separate from the rest of your system):

```bash
python -m venv venv

# Activate it:
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (cmd):
venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate
```

Install the two packages the script needs:

```bash
pip install PyGithub pyyaml
```

> 💡 On Linux, if `pip` complains about "externally managed environment", add `--break-system-packages` or just make sure your venv is activated (you'll see `(venv)` in your prompt).

---

### Step 4.7 — Set your GitHub token as an environment variable

The script reads the token from the `GITHUB_TOKEN` environment variable.

```bash
# Windows (PowerShell):
$env:GITHUB_TOKEN="ghp_yourTokenHere"

# Windows (cmd):
set GITHUB_TOKEN=ghp_yourTokenHere

# macOS/Linux:
export GITHUB_TOKEN="ghp_yourTokenHere"
```

> Set this in **every new terminal session** you use to run the script — it doesn't persist automatically.

> 🔑 **About `ghp_yourTokenHere`:** Every place in this README that shows `ghp_yourTokenHere` — and the `YOUR_TOKEN_GOES_HERE_LOCALLY` default inside `carbon_router.py` — is a **placeholder**, not a bug. It's deliberate stand-in text for *your* real PAT from Step 4.3. Swapping it out is a normal configuration step, not something "broken" the way the missing `import os` line is. If you copy-paste a command with the placeholder left in, GitHub will correctly reject it with `Bad credentials` — that's expected behavior, not a sign anything is wrong with the project.

---

### Step 4.8 — Run the orchestrator locally 🎉

```bash
python carbon_router.py
```

You should see output like:

```
Initiating GreenOps Carbon Routing Protocol...

Current US-East Emissions: 480 gCO2eq/kWh
Current India Emissions:   340 gCO2eq/kWh

=> DECISION: Shifting workload to region-india
[*] Successfully updated us-east/deployment.yaml to 0 replicas.
[*] Successfully updated india/deployment.yaml to 3 replicas.
```

Now go check **your forked repo on GitHub** — you should see a brand-new commit titled something like:
`"GreenOps Auto-Scaler: Shifting replicas to 3 in india/deployment.yaml"`,
and the `replicas:` value inside the YAML files should have changed.

Run the script again a minute later — sometimes it'll flip back, sometimes it'll print without committing (if the values are already correct, it skips the commit).

---

### Step 4.9 — Containerize it with Docker

The included `Dockerfile` packages the script into an image.

```bash
docker build -t greenops-router:v1 .
```

Run the container, passing in your token as an environment variable:

```bash
docker run --rm -e GITHUB_TOKEN="ghp_yourTokenHere" greenops-router:v1
```

You should see the same output as Step 4.8, but running inside an isolated container.

---

### Step 4.10 — (Optional) Run it on Kubernetes as a scheduled CronJob

`router-cronjob.yaml` defines a Kubernetes **CronJob** that runs the container every 5 minutes.

1. **Start a local cluster:**
   ```bash
   minikube start
   ```

2. **Build the image *inside* minikube's Docker environment.** This matters because `router-cronjob.yaml` uses `imagePullPolicy: IfNotPresent` — meaning Kubernetes will look for the image **locally** and never try to download it. If you build the image with your normal `docker build`, minikube's internal Docker won't see it and you'll get `ImagePullBackOff`.

   ```bash
   # macOS/Linux:
   eval $(minikube docker-env)

   # Windows (PowerShell):
   & minikube -p minikube docker-env | Invoke-Expression

   # Now build (note: same command, but now it builds inside minikube):
   docker build -t greenops-router:v1 .
   ```

3. **Create a Kubernetes Secret for your GitHub token** (the YAML file doesn't include one by default, so the container would have no token otherwise):

   ```bash
   kubectl create secret generic github-token --from-literal=GITHUB_TOKEN="ghp_yourTokenHere"
   ```

4. **Edit `router-cronjob.yaml`** to inject that secret into the container. Add an `env` section under `containers`, so it looks like:

   ```yaml
   containers:
   - name: router
     image: greenops-router:v1
     imagePullPolicy: IfNotPresent
     env:
     - name: GITHUB_TOKEN
       valueFrom:
         secretKeyRef:
           name: github-token
           key: GITHUB_TOKEN
   ```

5. **Apply the CronJob:**
   ```bash
   kubectl apply -f router-cronjob.yaml
   ```

6. **Watch it run:**
   ```bash
   kubectl get cronjob
   kubectl get jobs --watch
   kubectl get pods
   kubectl logs <pod-name>
   ```

   Since the schedule is `*/5 * * * *`, the first job may take up to 5 minutes to fire. To test immediately without waiting, you can manually trigger one:
   ```bash
   kubectl create job --from=cronjob/greenops-router-job manual-test-1
   kubectl logs job/manual-test-1
   ```

---

### Step 4.11 — Confirm it's working end-to-end

Every time the script runs (manually, in Docker, or via the CronJob), check:

1. Your fork's **commit history** — new commits from "GreenOps Auto-Scaler" should appear.
2. The `replicas:` values in `us-east/deployment.yaml` and `india/deployment.yaml` in your fork — they should toggle between `0` and `3` and always be opposite of each other.

If you connect this fork to a real cluster with ArgoCD/Flux watching it, those replica changes would automatically scale your actual application up/down in each region — that's the full GreenOps loop.

---

## 🐞 5. Common Errors & How to Fix Them

| Error / Symptom | Cause | Fix |
|---|---|---|
| `'choco' is not recognized as an internal or external command` | Chocolatey installed/run from a **non-admin** PowerShell window | Re-open PowerShell **as Administrator**, reinstall Chocolatey, then open a fresh admin terminal |
| `NameError: name 'os' is not defined` | `import os` is missing from `carbon_router.py` | Add `import os` at the top of the file (Step 4.5) |
| `github.GithubException.BadCredentialsException: 401 {"message": "Bad credentials"}` | Token is wrong, expired, `GITHUB_TOKEN` wasn't set in this terminal — **or** the placeholder `ghp_yourTokenHere`/`YOUR_TOKEN_GOES_HERE_LOCALLY` was left in place instead of your real PAT (expected, not a code bug) | Re-generate a PAT (Step 4.3) and re-export your **real token** (Step 4.7) in the **same terminal** you run the script from |
| `403 {"message": "Resource not accessible by personal access token"}` | Your token doesn't have the `repo` scope, or `REPO_NAME` still points to someone else's repo | Recheck the `repo` scope when creating the token, and confirm `REPO_NAME` matches **your fork** |
| `ModuleNotFoundError: No module named 'github'` or `'yaml'` | Dependencies not installed, or installed outside your virtual environment | Activate your venv (Step 4.6), then `pip install PyGithub pyyaml` |
| `Cannot connect to the Docker daemon at unix:///var/run/docker.sock` (or similar on Windows) | Docker Desktop isn't running | Open/start Docker Desktop and wait until it shows "Running", then retry |
| Pod stuck in `ImagePullBackOff` or `ErrImageNeverPull` | Image was built outside minikube's Docker context, but `imagePullPolicy: IfNotPresent` expects it locally | Run `eval $(minikube docker-env)` (or the PowerShell equivalent) **before** `docker build` (Step 4.10) |
| CronJob pod logs show `Bad credentials` even though local run worked | `router-cronjob.yaml` has no `GITHUB_TOKEN` configured | Create the `github-token` Secret and add the `env`/`secretKeyRef` block (Step 4.10) |
| `fatal: repository not found` from PyGithub | Typo in `REPO_NAME`, or repo is private and token lacks access | Double-check spelling and capitalization of `REPO_NAME`, and that the token belongs to the account that owns/forked the repo |
| YAML file formatting changes after the script runs (quotes, spacing) | `pyyaml`'s `yaml.dump()` reformats files when rewriting them | Expected behavior — not a bug. The data is still valid YAML |
| Script runs but prints nothing changed | Both regions' emissions led to the same decision as last run, so `update_github_replicas` skipped the commit (already correct) | Normal — run it again later, the mock values are randomized each run |

---

## 📂 6. Project Structure Reference

**This repo** (`carbon-aware-workload-orchestrator-full-tutorial`):
```
.
├── Dockerfile           # Packages carbon_router.py into a container image
├── carbon_router.py     # The main "brain" — checks emissions, updates GitHub
├── router-cronjob.yaml  # Kubernetes CronJob to run the container every 5 min
└── README.md
```

**Companion repo** (`Carbon-Aware-Workload-Orchestrator`) — fork this one:
```
.
├── us-east/deployment.yaml   # Kubernetes Deployment for the US-East region
└── india/deployment.yaml     # Kubernetes Deployment for the India region
```

---

## 🔮 7. Ideas to Extend This Project

- Swap `get_mock_carbon_intensity()` for a **real API** like [Electricity Maps](https://www.electricitymaps.com/) or WattTime to use live grid data.
- Add more regions (e.g., `eu-west`, `ap-south`) and pick the single lowest-emission region instead of just two.
- Connect the manifest repo to **ArgoCD** or **Flux** so replica changes auto-deploy to a real cluster.
- Send a Slack/Discord notification whenever the orchestrator shifts workloads.
- Add unit tests and a `requirements.txt` for easier dependency management.

---

🙌 That's it — you now have a fully working (mock) carbon-aware GitOps pipeline, from a Python script all the way to a Kubernetes CronJob. Happy building!
