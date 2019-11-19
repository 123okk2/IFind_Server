import json
import requests

webhook_url = "https://hooks.slack.com/services/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"
content = "WebHook Test"
payload = {"text": content}

requests.post(
    webhook_url, data=json.dumps(payload),
    headers={'Content-Type': 'application/json'}
)
