# Email integration status and plan

**Current state: Demo only.** No real mailbox is connected. `InboxConnection` rows for Gmail / Microsoft show *Disconnected*; `POST inbox/connections/{id}/connect/` always refuses (409) because the OAuth flow is not implemented.

The seam is `backend/apps/inbox/providers.py`: implement `fetch_new_messages()` returning `RawMessage` objects. `inbox/services.py::import_message` already de-duplicates by `(provider, external_id)` per message and `(message, attachment id)` per attachment, and flags repeated attachment content (SHA-256) as *Duplicate*.

## Gmail API
1. Google Cloud project → enable Gmail API → OAuth consent screen → OAuth client (Web). Scope `gmail.readonly`.
2. Put `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` in `backend/.env`.
3. Implement the consent redirect/callback, store the refresh token encrypted (not in source or plain DB), then in `GmailProvider`: `users.messages.list(q="has:attachment in:inbox")`, `users.messages.get(format="full")`, `users.messages.attachments.get`.

## Microsoft Graph
1. Azure app registration → API permission `Mail.Read` → client secret.
2. Set `MS_GRAPH_CLIENT_ID`, `MS_GRAPH_CLIENT_SECRET`, `MS_GRAPH_TENANT_ID`.
3. Implement OAuth, then `GET /me/mailFolders/inbox/messages?$filter=hasAttachments eq true&$expand=attachments` in `MicrosoftGraphProvider`.

After a provider is implemented set `INBOX_MODE=live` and update the connection state only once a token has been obtained.
