# Operations Guide

## Start the Application

Activate the environment and start Streamlit from the repository root:

```powershell
.venv\Scripts\Activate.ps1
python -m streamlit run apps/streamlit_app.py --server.port=8503 --server.fileWatcherType=none
```

The disabled file watcher avoids noisy Transformers module inspection. Restart
the process after code or `.env` changes.

## Confirm the Backend

Check `.env` without printing the token value:

```powershell
Get-Content .env | Select-String 'CHAT_MODEL_BACKEND|HF_INFERENCE_MODEL_ID|HF_INFERENCE_PROVIDER'
```

Hosted mode requires:

- `CHAT_MODEL_BACKEND=huggingface`
- a non-empty `HF_TOKEN`
- a model supported by the selected inference provider

The tested hosted combination is
`Qwen/Qwen2.5-7B-Instruct-1M` with `featherless-ai`. Availability is external and
may change.

## Verify the Server

```powershell
Invoke-WebRequest http://localhost:8503 -UseBasicParsing
```

An HTTP 200 confirms the Streamlit server is reachable. It does not by itself
confirm search or hosted model access, which require a research request.

## Troubleshooting

### `getaddrinfo failed`

This is a DNS resolution failure. Check connectivity to:

```powershell
Resolve-DnsName duckduckgo.com
Resolve-DnsName router.huggingface.co
Resolve-DnsName r.jina.ai
```

Search DNS failures now return a no-sources response. Hosted-model DNS failures
return a retry message. If DNS is resolving again, refresh and retry.

### Local model loads after enabling hosted mode

The Streamlit process was probably started before `.env` changed. Stop it and
restart it so the model factory reads the new environment.

### Hugging Face `model_not_available` or `model_not_supported`

The model-provider pairing is unavailable or not enabled for the account. Check
the model's current Inference Providers list on Hugging Face, then update both
`HF_INFERENCE_MODEL_ID` and `HF_INFERENCE_PROVIDER` and restart the app.

### Empty hosted response

Some providers may consume a very small output allowance without returning
visible content. Increase **Max response tokens** and retry. The adapter rejects
blank responses explicitly.

## Usage Monitoring

Requests routed with `HF_TOKEN` are attributed to the corresponding Hugging Face
account. Review monthly model/provider usage at:

- `https://huggingface.co/settings/inference-providers`
- `https://huggingface.co/settings/billing`

Usage reporting can lag briefly. Free credits and provider prices may change.

## Logs

All `.log` files belong in `logs/`, including Streamlit stdout/stderr, JVM crash
logs, replay logs, and temporary test logs. The project root should contain zero
`.log` files.

When starting Streamlit as a background process, redirect output directly:

```powershell
Start-Process -FilePath '.\.venv\Scripts\python.exe' `
  -ArgumentList '-m','streamlit','run','apps\streamlit_app.py','--server.port=8503','--server.fileWatcherType=none' `
  -RedirectStandardOutput 'logs\streamlit-8503.stdout.log' `
  -RedirectStandardError 'logs\streamlit-8503.stderr.log' `
  -WindowStyle Hidden
```

Logs are ignored by Git and may contain operational details. Never write tokens
or secret environment values to them.
