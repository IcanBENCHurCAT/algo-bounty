# Interface Contracts: GitHub App Integration & Trustless Payout Validation

## Endpoint: Webhook Receiver
Receive webhook notifications from GitHub.

* **Path:** `POST /webhooks/github`
* **Headers:**
  - `X-GitHub-Event`: Event type (e.g. `pull_request`, `issues`)
  - `X-GitHub-Delivery`: Unique webhook invocation UUID
  - `X-Signature-256`: Signature string `sha256=<hmac>`
* **Payload Examples:**
  - **PR Merge Payload:**
    ```json
    {
      "action": "closed",
      "pull_request": {
        "number": 104,
        "title": "Fix bug #ALGO-42",
        "body": "Resolves issue.",
        "merged": true,
        "html_url": "https://github.com/org/repo/pull/104"
      }
    }
    ```
* **Response:**
  - `200 OK` with JSON `{"status": "accepted", "delivery_id": "<uuid>"}`
