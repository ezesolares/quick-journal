# Quick Journal and Task GUI for Notion, Google Tasks and Google Keep

This is a Graphical User Interface (GUI) that allows for extremely fast brain dumps to Notion, Google Tasks, and Google Keep via an Always On Top floating dialog developed with PyQt6.

## Installation and Configuration

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Backend Configuration and Integration

Copy `.env.example` to a new file named `.env` and configure your services:

#### 1. Notion
- Follow the official guide to create an internal integration and get your `NOTION_TOKEN`.
- Share the target pages with your integration.
- Copy the IDs of the respective pages.

#### 2. Google Keep (`gkeep`)
How to obtain master token:
Use the Alternative flow from https://github.com/simon-weber/gpsoauth#alternative-flow
From there, use: `docker run --rm -it --entrypoint /bin/sh python:3 -c 'pip install gpsoauth; python3 -c '\''print(__import__("gpsoauth").exchange_token(input("Email: "), input("OAuth Token: "), input("Android ID: ")))'\'`

If you are lucky, the other way is:
- Use your Gmail email.
- **Important**: Requires a **Master Token**. 
- **How to get it**: We have included a tool for this. Run:
  ```bash
  python tools/get_gkeep_token.py
  ```
- Follow the instructions and copy the resulting token into your `.env`.
- Alternatively, you can use `GOOGLE_KEEP_PASSWORD` with an **App Password**.

#### 3. Google Tasks (`gtasks`)
- This is the most secure and modern method (uses OAuth 2.0).
- You need a `credentials.json` file from the Google Cloud Console.
- The first time you run it, it will open a browser to authorize access.
- It will save a `token.pickle` for future sessions.

---

### OpenDeck Integration
In your OpenDeck software, assign these actions to different buttons:
- **Journal**: `pythonw diario_pro.py --journal`
- **Tasks**: `pythonw diario_pro.py --task`

(Note: `pythonw` prevents a console window from opening).

## Flow and Usability
- **Dynamic Modes**: 
  - **Journal** mode appears with green borders.
  - **Task** mode appears with blue borders and a specific title.
- **Task Formatting**: In Task mode, each line entered is saved as an individual task (checkbox/to-do).
- **Simultaneous Backends**: You can configure multiple backends separated by commas (e.g., `DIARIO_BACKEND="notion,local"`).
- **Offline Cache**: If a save fails or you are offline, it saves to `offline_cache.json` and will attempt to sync the next time a successful save occurs.
