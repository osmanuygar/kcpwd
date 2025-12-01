## kcpwd Password Sharing Usage Examples

###  Real-World Usage Scenarios

#### Scenario 1: Emergency Production Access
**Situation:** DevOps engineer needs to give temporary database access to on-call developer at 2 AM.

```python
# DevOps creates 15-minute one-time share
import requests

auth = requests.post("http://localhost:8765/api/auth", 
    json={"secret": "devops-secret"})
token = auth.json()["token"]

share = requests.post("http://localhost:8765/api/share/create",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "key": "prod_db_password",
        "duration": "15m",
        "access_type": "once",  # Auto-delete after access
        "require_master": True,
        "master_password": "master-pass-123"
    })

# Send link via Signal/encrypted chat
print(f"Share this link: {share.json()['share_url']}")
# http://localhost:8765/s/Xy9kL2mN4pQ6rS8t

# Developer clicks link, sees password, link immediately expires
```

**Benefits:**
- ✅ No plaintext password in chat history
- ✅ Expires in 15 minutes
- ✅ One-time access only
- ✅ Audit log of access

---

#### Scenario 2: Client API Key Handoff
**Situation:** Agency delivering project to client, needs to share API credentials.

```python
# Create 3-hour share with password protection
share = requests.post("http://localhost:8765/api/share/create",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "key": "client_api_key",
        "duration": "3h",
        "access_type": "password",
        "access_password": "client-code-2024",  # Share separately
        "max_views": 3  # Client can view 3 times during setup
    })

# Share link via email, password via phone
print(f"Link: {share.json()['share_url']}")
print("Password: Share verbally via phone/video call")
```

**Benefits:**
- ✅ Two-factor sharing (link + password)
- ✅ Client has time to set up their system
- ✅ Multiple views allowed for troubleshooting
- ✅ Auto-expires after 3 hours

---

#### Scenario 3: Team Onboarding
**Situation:** New developer joining team, needs initial credentials.

```python
# HR creates shares for all onboarding credentials
credentials = [
    {"key": "gitlab_initial_token", "duration": "1h"},
    {"key": "vpn_temp_password", "duration": "1h"},
    {"key": "internal_wiki_password", "duration": "1h"}
]

onboarding_links = []
for cred in credentials:
    share = requests.post("http://localhost:8765/api/share/create",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "key": cred["key"],
            "duration": cred["duration"],
            "access_type": "once",  # Must change after first login
            "max_views": 1
        })
    onboarding_links.append({
        "service": cred["key"],
        "url": share.json()["share_url"]
    })

# Send all links in welcome email
print("Onboarding Package:")
for link in onboarding_links:
    print(f"- {link['service']}: {link['url']}")
```

**Benefits:**
- ✅ All credentials expire after initial access
- ✅ Forces password changes
- ✅ No permanent credentials in email
- ✅ Audit trail of first access

---

### Scenario 4: Contractor Temporary Access
**Situation:** Contractor needs staging environment access for 2-week project.

```python
# Create longer-duration share with view limit
share = requests.post("http://localhost:8765/api/share/create",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "key": "staging_ssh_password",
        "duration": "3h",  # Recreate daily
        "access_type": "anyone",
        "max_views": 10  # Can check multiple times per day
    })

# Script to recreate daily
import schedule
import time

def create_daily_share():
    # ... create share logic ...
    # Send to contractor via Slack
    pass

# Run daily at 9 AM
schedule.every().day.at("09:00").do(create_daily_share)
```

**Benefits:**
- ✅ Short-lived credentials
- ✅ Automatic rotation
- ✅ Limited but reasonable access
- ✅ Easy to revoke

---

#### Scenario 5: Support Team Password Reset
**Situation:** Customer forgot password, support needs to share temporary reset link.

```python
# Support agent creates one-time share
temp_password = generate_password(length=12)  # Create temp password
set_password("customer_temp_reset", temp_password)

share = requests.post("http://localhost:8765/api/share/create",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "key": "customer_temp_reset",
        "duration": "30m",
        "access_type": "once",  # Must use immediately
        "max_views": 1
    })

# Send via SMS or verified email
print(f"Temporary password link (expires in 30 min): {share.json()['share_url']}")

# Customer accesses, must change password
# Link auto-deletes after viewing
```

**Benefits:**
- ✅ Short window for access
- ✅ No permanent password exposure
- ✅ Forces immediate password change
- ✅ Secure delivery method

---

### 🔧 Integration Examples

#### Example 1: Slack Bot Integration

```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

slack_token = "xoxb-your-bot-token"
client = WebClient(token=slack_token)

def share_password_to_slack(channel, password_key, duration="1h"):
    """Share password via Slack DM"""
    
    # Create share
    share = requests.post("http://localhost:8765/api/share/create",
        headers={"Authorization": f"Bearer {kcpwd_token}"},
        json={
            "key": password_key,
            "duration": duration,
            "access_type": "once"
        })
    
    share_url = share.json()["share_url"]
    expires_at = share.json()["expires_at"]
    
    # Send to Slack
    try:
        client.chat_postMessage(
            channel=channel,
            text=f"🔐 Secure Password Share",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Password:* `{password_key}`\n*Expires:* {expires_at}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔗 <{share_url}|Click here to access> (one-time use)"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "⚠️ Link expires after viewing or in {duration}"
                        }
                    ]
                }
            ]
        )
    except SlackApiError as e:
        print(f"Error: {e}")

# Usage
share_password_to_slack("@john.doe", "staging_db_password", "1h")
```

---

#### Example 2: API Gateway Pattern

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI()
security = HTTPBearer()

# Your service that needs temporary password access
@app.post("/request-access/{service_name}")
async def request_temporary_access(
    service_name: str,
    duration: str = "1h",
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Request temporary access to a service"""
    
    # Verify requester is authorized
    user = verify_user_token(credentials.credentials)
    
    # Create kcpwd share
    share = requests.post("http://kcpwd-server:8765/api/share/create",
        headers={"Authorization": f"Bearer {kcpwd_token}"},
        json={
            "key": f"{service_name}_password",
            "duration": duration,
            "access_type": "once",
            "max_views": 1
        })
    
    # Log the request
    log_access_request(user, service_name, share.json()["share_id"])
    
    return {
        "share_url": share.json()["share_url"],
        "expires_at": share.json()["expires_at"],
        "message": f"Access granted to {service_name} for {duration}"
    }

# Usage:
# POST /request-access/production-db
# Authorization: Bearer user-token
# Response: { "share_url": "...", "expires_at": "..." }
```

---

#### Example 3: Automated Testing with Temporary Credentials

```python
import pytest
import requests

class PasswordShareFixture:
    """Pytest fixture for temporary test credentials"""
    
    def __init__(self):
        self.shares = []
    
    def create_test_credential(self, key, duration="30m"):
        """Create temporary credential for test"""
        share = requests.post("http://localhost:8765/api/share/create",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "key": key,
                "duration": duration,
                "access_type": "anyone",
                "max_views": 100  # Multiple test runs
            })
        
        self.shares.append(share.json()["share_id"])
        return share.json()["share_url"]
    
    def cleanup(self):
        """Delete all test shares"""
        for share_id in self.shares:
            requests.delete(f"http://localhost:8765/api/share/{share_id}",
                headers={"Authorization": f"Bearer {test_token}"})

@pytest.fixture
def test_credentials():
    """Fixture providing temporary test credentials"""
    fixture = PasswordShareFixture()
    
    # Create test credentials
    api_key_url = fixture.create_test_credential("test_api_key")
    db_password_url = fixture.create_test_credential("test_db_password")
    
    # Access and return actual passwords
    api_key = requests.post(f"{api_key_url}/access").json()["password"]
    db_password = requests.post(f"{db_password_url}/access").json()["password"]
    
    yield {"api_key": api_key, "db_password": db_password}
    
    # Cleanup
    fixture.cleanup()

# Use in tests
def test_api_with_credentials(test_credentials):
    response = requests.get("https://api.example.com/data",
        headers={"Authorization": f"Bearer {test_credentials['api_key']}"})
    assert response.status_code == 200
```

---

#### Example 4: CI/CD Pipeline Secret Sharing

```yaml
# .github/workflows/deploy.yml
name: Deploy with Temporary Credentials

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Request Deployment Credentials
        id: creds
        run: |
          # Request share from kcpwd server
          SHARE_RESPONSE=$(curl -X POST "https://kcpwd.company.com/api/share/create" \
            -H "Authorization: Bearer ${{ secrets.KCPWD_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{
              "key": "production_deploy_key",
              "duration": "15m",
              "access_type": "once"
            }')
          
          SHARE_URL=$(echo $SHARE_RESPONSE | jq -r '.share_url')
          
          # Access the password
          PASSWORD=$(curl -X POST "${SHARE_URL}/access" | jq -r '.password')
          
          echo "::add-mask::$PASSWORD"
          echo "DEPLOY_PASSWORD=$PASSWORD" >> $GITHUB_OUTPUT
      
      - name: Deploy
        env:
          DEPLOY_PASSWORD: ${{ steps.creds.outputs.DEPLOY_PASSWORD }}
        run: |
          # Use password for deployment
          ./deploy.sh --password "$DEPLOY_PASSWORD"
          
      - name: Verify Share Expired
        run: |
          # Share should be auto-deleted after access
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SHARE_URL")
          if [ "$STATUS" != "404" ]; then
            echo "Warning: Share link still active!"
            exit 1
          fi
```

---

### 📊 Monitoring and Analytics

#### Track Share Usage

```python
import pandas as pd
from datetime import datetime, timedelta

def analyze_share_usage():
    """Generate share usage report"""
    
    # Get all stats
    stats = requests.get("http://localhost:8765/api/shares/stats",
        headers={"Authorization": f"Bearer {token}"}).json()
    
    # Get active shares
    shares = requests.get("http://localhost:8765/api/shares",
        headers={"Authorization": f"Bearer {token}"}).json()
    
    # Create report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_shares": stats["total_shares"],
        "active_shares": stats["active_shares"],
        "total_views": stats["total_views"],
        "by_access_type": stats["by_access_type"],
        "active_share_details": shares["shares"]
    }
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(shares["shares"])
    
    print(f"📊 Share Usage Report - {report['timestamp']}")
    print(f"   Active: {report['active_shares']}")
    print(f"   Total Views: {report['total_views']}")
    print(f"   By Type: {report['by_access_type']}")
    
    if not df.empty:
        print(f"\n   Top Shared Passwords:")
        print(df["key_name"].value_counts().head())
        
        print(f"\n   Average Views per Share: {df['view_count'].mean():.2f}")
    
    return report

# Run daily
schedule.every().day.at("00:00").do(analyze_share_usage)
```

---

These scenarios demonstrate the flexibility and security of kcpwd's password sharing feature. The key principles are:

1. **Short-lived:** Always use minimum necessary duration
2. **One-time when possible:** Reduce exposure window
3. **Additional security layers:** Use password protection for sensitive data
4. **Audit trails:** Log all access for compliance
5. **Automation:** Integrate with existing workflows

The feature enables secure, temporary password sharing without compromising security or leaving permanent traces in insecure channels.