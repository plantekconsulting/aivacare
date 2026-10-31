# AivaCare cloud test environment (GCP)

| Item | Value |
|---|---|
| Project | `aivacare-513321` |
| VM | `aivacare-vm` (e2-standard-2, us-central1-a, Debian 12, Docker Compose) |
| Static IP | 34.30.79.254 (stays the same when the VM is stopped and started) |
| Web app | https://app.34-30-79-254.sslip.io |
| API | https://api.34-30-79-254.sslip.io |
| Access | Team access code (shared privately - never commit it). Config lives in `/opt/aivacare/infra/.env` on the VM. |

Set these once in your shell:
```bash
P=aivacare-513321; Z=us-central1-a
```

## Start / stop to save money
```bash
gcloud compute instances start aivacare-vm --zone=$Z --project=$P   # about 2-3 min until the app responds (HAPI startup)
gcloud compute instances stop  aivacare-vm --zone=$Z --project=$P   # while stopped, you only pay for the disk and the static IP
```

## Add or change the Claude API key
```bash
gcloud compute ssh aivacare-vm --zone=$Z --project=$P
sudo nano /opt/aivacare/infra/.env        # set ANTHROPIC_API_KEY=...
cd /opt/aivacare/infra && sudo docker compose --profile cloud up -d api
```

## Deploy a new version
```bash
git archive --format=tar.gz -o aivacare.tgz HEAD
gcloud compute scp aivacare.tgz aivacare-vm:/home/$USER/ --zone=$Z --project=$P
gcloud compute ssh aivacare-vm --zone=$Z --project=$P --command \
  "sudo tar xzf ~/aivacare.tgz -C /opt/aivacare && cd /opt/aivacare/infra && sudo docker compose --profile cloud up -d --build"
```
`.env` is not part of the archive, so the secrets on the VM are kept.

## Reset the demo data
Sign in as **Demo Admin** and click **Reset**. This affects everyone using the environment.

## Logs
```bash
gcloud compute ssh aivacare-vm --zone=$Z --project=$P --command "cd /opt/aivacare/infra && sudo docker compose logs --tail 100 api"
```
