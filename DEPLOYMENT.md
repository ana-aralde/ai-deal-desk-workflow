# Easiest Deployment Path

## Local test

1. Install Python 3.12 or another currently supported version.
2. Open a terminal in the project folder.
3. Create a virtual environment: `python -m venv .venv`.
4. Activate it.
5. Run `pip install -r requirements.txt`.
6. Run `streamlit run app.py`.
7. Open the local URL shown by Streamlit.
8. Click **Load fictional demo data** to test the workflow without using real information.

## Enable the AI locally

1. Create an OpenAI API key in your own API project.
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
3. Paste your key in `OPENAI_API_KEY`.
4. Keep `ALLOW_PUBLIC_AI = false`.
5. Set an `APP_PASSWORD`.
6. Run the app again and test the AI Review tab using only fictional data.

## Publish the code on GitHub

1. Create a GitHub repository.
2. Upload all project files except `.streamlit/secrets.toml`.
3. Confirm `.gitignore` is present before any commit containing secrets.
4. Keep the repository public if you want recruiters to inspect the code.
5. Add screenshots and the live Streamlit link to the README after deployment.

## Deploy on Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud with GitHub.
2. Choose **Create app**.
3. Select the repository, branch and `app.py`.
4. Open **Advanced settings / Secrets**.
5. Paste the real secret values there; do not put them in GitHub.
6. Deploy.
7. Test the live URL using fictional demo data.

## Recommended public-portfolio configuration

The safest public configuration is:

- fictional data only;
- `APP_PASSWORD` set if AI is enabled;
- `ALLOW_PUBLIC_AI = false`;
- low `MAX_AI_CALLS_PER_SESSION`;
- no persistent database;
- no real customer documents;
- a visible disclaimer that outputs are drafts and human approval is mandatory.

For production organizational data, move to an authenticated private environment and implement the controls in `SECURITY_PRIVACY.md`.
