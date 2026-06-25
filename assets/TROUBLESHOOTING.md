# CRA Docker Troubleshooting

Solutions for common Docker setup problems when running Code Reproduction Agents. CRA requires task setup, runtime checks, official runs, validation, and evaluation to execute inside Docker wrappers, so Docker failures should be archived as first-class blocker evidence.

## `docker pull` Fails

Pulling base images from Docker Hub requires outbound internet access. If `docker pull` fails with a network or proxy error, try the options below.

### Proxy Setup

If your network requires a proxy, set proxy variables in the current shell and sync them to the Docker daemon:

```bash
export HTTP_PROXY=http://127.0.0.1:<YOUR_PROXY_PORT>
export HTTPS_PROXY=http://127.0.0.1:<YOUR_PROXY_PORT>
export http_proxy=$HTTP_PROXY
export https_proxy=$HTTPS_PROXY
export no_proxy="localhost,127.0.0.1"
export NO_PROXY="localhost,127.0.0.1"
```

If you have sudo access, configure Docker daemon proxy settings according to your system policy, then restart Docker and retry:

```bash
docker pull python:3.11-slim
```

Archive the failing pull/build log under `runs/<run-id>/docker_build.log` if this remains blocked.

### Registry Mirror

If direct Docker Hub access is unreliable, configure registry mirrors in `/etc/docker/daemon.json` when allowed by your environment:

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://dockerproxy.link",
    "https://docker.m.daocloud.io"
  ]
}
```

Then restart Docker and retry the pull/build command. Record which mirror was used in the run metadata or environment note.

### Offline Image Transfer

If the execution server has no internet access, transfer images from another machine:

```bash
# On a connected machine:
docker pull python:3.11-slim
docker image save python:3.11-slim -o python-3.11-slim.tar
scp python-3.11-slim.tar user@server:~

# On the target server:
docker image load -i python-3.11-slim.tar
```

Then rerun:

```bash
scripts/docker_build.sh
```

## Docker Permission Denied

If `docker ps` fails with permission errors, the current user may not have access to the Docker daemon. Options:

- Ask the administrator to add the user to the Docker group.
- Run the CRA wrapper commands through the approved job/sudo mechanism.
- Record `blocked_external` if Docker access is unavailable and required by the run contract.

Do not silently fall back to host execution unless the scope change is explicitly approved and recorded.

## Container Starts But Commands Fail

Check:

```bash
scripts/docker_run.sh
scripts/docker_exec.sh pwd
scripts/docker_exec.sh python --version
scripts/runtime_check.sh
```

Common causes:

- The target repo was not placed under `source/`.
- The Dockerfile did not install system packages or Python dependencies.
- The official command assumes a different working directory.
- Dataset/checkpoint mounts are missing.
- Secrets were not passed through `.cra_env` or an approved secret mechanism.

Archive the failing command and log. Classify these as `PATH`, `DEP`, `CFG`, `DATA`, or `ENV` in the checklist.

## GPU Runtime Problems

For GPU tasks, set Docker GPU args explicitly, for example:

```bash
export CRA_DOCKER_ARGS="--gpus all"
scripts/docker_run.sh
scripts/docker_exec.sh bash -lc 'python - <<"PY"
import torch
print(torch.cuda.is_available())
print(torch.cuda.device_count())
PY'
```

Record CUDA, framework, and device visibility output in `runtime_check.log` or `env_summary.txt`. If the host lacks NVIDIA Container Toolkit or GPU access, classify the issue as `INFRA` or `ENV`.

## Secret Leakage

CRA archives logs by design. Do not print tokens, cookies, private keys, or sensitive headers. Use `.cra_env` or an approved secret manager for runtime environment variables, and redact accidental secret output before final archiving. Record redactions in the checklist.
