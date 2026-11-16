# SCAM JOSE PAUL — Web Edition

A first browser-based build of the city-based game.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run `pip install -r requirements.txt`.
4. Run `streamlit run app.py`.
5. Open the local URL Streamlit prints.

## Deploy without installing anything on your laptop

1. Upload this folder to a GitHub repository.
2. On Streamlit Community Cloud, create an app from that repository and select `app.py`.
3. Deploy. The app will run in a browser.

## Important limitations

- This is an early web MVP, not a production multiplayer service. Streamlit reruns the app and local JSON persistence is not a safe shared database for concurrent public players.
- For a real public multiplayer launch, replace JSON storage with a hosted database, add server-side authorization/rate limits, and use a realtime service for presence.
- Passwords use the existing salted SHA-256 format for compatibility with the source project; upgrade to Argon2id before real public deployment.
- Legacy single-player saves are migrated into the Global Hub when loaded. Back up your existing save before deploying.
- The web console implements core account, City, economy, career, collection, player interaction, and crew-heist commands. Some original terminal-only features and the full casino suite are not yet ported.
