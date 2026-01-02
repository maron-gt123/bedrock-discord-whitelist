# 📝 Bedrock Discord Whitelist Bot

This bot is designed to **easily manage the whitelist for Minecraft Bedrock Edition servers** via Discord.  
Users can apply for whitelist access on Discord, and administrators can approve them to grant access to the server.

> ⚠️ This bot assumes that you are running the Bedrock server **on Kubernetes**.  
> Commands are sent directly to the Bedrock server using `kubectl exec`.

---

## 🌟 Features

- Apply, approve, revoke, and list whitelist entries via Discord  
- Rate limit: **1 application per 60 seconds**  
- Sends commands to the Minecraft Bedrock server **directly via Kubernetes exec**  
- Automatically retrieves XUID from Gamertag using **PlayerDB API**  
- Admin commands: `/approve`, `/revoke`, `/reload`  
- Can be deployed as a **Docker container** for easy setup  

---

## 🖥 Requirements

- Python 3.10 or higher (not required if using the Docker image)  
- Discord Bot Token  
- Minecraft Bedrock server running on Kubernetes  

Required environment variables:

| Variable | Description |
|-----------|-------------|
| `BOT_TOKEN` | Discord Bot Token |
| `APPLY_CHANNEL` | Channel ID for whitelist applications |
| `APPROVE_CHANNEL` | Channel ID for approvals |
| `ADMIN_ROLE` | Role ID for administrators |
| `BEDROCK_NAMESPACE` | Kubernetes namespace where the Bedrock pod is running |
| `BEDROCK_POD` | Name of the Bedrock pod |
| `BEDROCK_CONTAINER` | (Optional) Container name |

---

## ⚙️ Installation / Deployment

### Using Docker Hub

The bot is available as a Docker image on Docker Hub, which eliminates the need to install Python dependencies manually.  
Simply set the environment variables and start the container.

```bash
docker run -d \
  -e BOT_TOKEN="your_token" \
  -e APPLY_CHANNEL=1234567890 \
  -e APPROVE_CHANNEL=1234567890 \
  -e ADMIN_ROLE=1234567890 \
  -e BEDROCK_NAMESPACE="minecraft" \
  -e BEDROCK_POD="bedrock-server" \
  maron/bedrock-discord-whitelist:latest
