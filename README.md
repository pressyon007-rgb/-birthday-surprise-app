# Monalisa | Emerald Memories — deploy-ready project

This bundle starts from the supplied full `app.py` and keeps its existing login, countdown/date lock, quiz, animated photo gallery, Photo Studio, per-photo settings, background customization, letter, and birthday reveal. The update adds portable settings save/load, static-file audio delivery (rather than Base64-embedding the whole song), a visible browser audio player, a publish/share panel, and secret-based password configuration.

## 1. Add your assets before publishing

Copy your own photos into `assets/photos/`, your song into `assets/audio/tamil-birthday-song.mp3`, and optional backgrounds into `assets/backgrounds/`. The `.gitkeep` files only preserve empty folders; they are not photos or music.

After changing settings locally, click **Save all customizations** in the sidebar. Commit `monalisa_settings.json` plus the chosen photos/backgrounds/song to your GitHub repository if you want the deployed version to start with those same settings and assets.

## 2. Local Windows setup

Open PowerShell in this project folder:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:MONALISA_TEST_MODE = "1"
python -m streamlit run app.py
```

If `.venv` does not exist yet, create it once:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The local preview switch only works when production mode is false. The real birthday unlock is fixed at **3 November 2026, 12:00 AM IST**. To test the actual lock, close the terminal and start again without setting `MONALISA_TEST_MODE`:

```powershell
Remove-Item Env:MONALISA_TEST_MODE -ErrorAction SilentlyContinue
python -m streamlit run app.py
```

## 3. Local secrets

For local development, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set a unique password. Keep `.streamlit/secrets.toml` out of GitHub; it is ignored by `.gitignore`.

```toml
APP_PASSWORD = "choose-a-long-unique-password"
PRODUCTION_MODE = false
```

Do not use the local test environment variable in production. In Streamlit Community Cloud, set these values in the app's **Settings / Secrets** panel:

```toml
APP_PASSWORD = "choose-a-long-unique-password"
PRODUCTION_MODE = true
```

With `PRODUCTION_MODE = true`, `MONALISA_TEST_MODE` is ignored. Do not put the app password in the Python source or show it on screen. A single shared password is basic access control, not strong per-person authentication.

## 4. Deploy to Streamlit Community Cloud

1. Create/sign in to GitHub and create a repository for this app.
2. Add `app.py`, `requirements.txt`, `.streamlit/config.toml`, `monalisa_settings.json`, and your chosen assets. Do **not** add `.venv/` or `.streamlit/secrets.toml`.
3. Commit and push the files to the repository's `main` branch.
4. Open <https://share.streamlit.io/> and sign in with GitHub.
5. Choose **Create app**, select the repository, branch `main`, and main file path `app.py`.
6. In Advanced settings, select Python 3.12 (or another supported version), and add the secrets shown above. Save and deploy.
7. Wait for the deployment to finish, then open the URL Streamlit provides. Only that real URL should be entered in the sidebar's **Public app URL** field and shared.
8. Test the deployed link in a private/incognito browser and on a phone before sending it to Monalisa.

No public URL is prefilled because a real URL only exists after you deploy the repository successfully.

## 5. Storage and uploaded assets

`monalisa_settings.json` is saved on the running filesystem. Streamlit Community Cloud does **not** guarantee that files uploaded or generated while the app is running persist across sessions or restarts. The reliable simple workflow is to customize locally, save settings, include the final JSON and assets in GitHub, and then deploy. If you want visitors to upload files or the owner to edit settings on the live cloud app and have those changes survive restarts, add external persistent storage (for example, an object-storage bucket or database); this bundle does not pretend local cloud writes are durable.

## 6. Audio limitations

The app now serves the audio file through Streamlit's static file serving, avoiding a huge Base64 string in each page rerun. The player attempts autoplay and loops, with visible controls for Play/Pause/volume. Chrome, Safari, and mobile browsers may block autoplay with sound until the visitor taps Play. Streamlit reruns can recreate the component, so uninterrupted playback through every navigation rerun cannot be guaranteed; the player attempts to restore the previous timestamp.

## 7. Before sharing checklist

- [ ] `assets/audio/tamil-birthday-song.mp3` is present and committed.
- [ ] Correct photos and background files are committed.
- [ ] Click **Save all customizations** and commit `monalisa_settings.json`.
- [ ] `APP_PASSWORD` and `PRODUCTION_MODE = true` are configured in Cloud secrets.
- [ ] The deployed app displays the countdown before 3 November 2026 at midnight IST.
- [ ] Music works after one Play tap on mobile.
- [ ] Login, quiz, gallery, Photo Studio, reveal, and letter work.
- [ ] Use only the URL shown by Streamlit after successful deployment.
