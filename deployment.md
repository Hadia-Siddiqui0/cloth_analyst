# Deploying for real

This gets the app onto real URLs, so the CEO opens a link in his browser.
No Docker, no install, nothing for him to run.

Two pieces, deployed separately: the FastAPI backend on Render, the
Next.js frontend on Vercel. Both have free tiers. Do the backend first,
you need its URL for step 2.

---

## 0. Push to GitHub first

Both Render and Vercel deploy by connecting to a GitHub repo, not by
uploading files directly. If you haven't already:

```bash
bash scripts/init_repo.sh
# then create an empty repo on GitHub and follow the printed instructions
```

---

## 1. Backend on Render

1. Go to render.com, sign up / log in, connect your GitHub account.
2. **New +** → **Blueprint** → pick this repo. Render reads `render.yaml`
   at the repo root automatically and sets up both the web service and
   the Postgres database from it.
3. Click **Apply**. Render will build and deploy. First build takes a
   few minutes.
4. Once live, copy the backend's URL from the Render dashboard, it'll
   look like `https://textile-bi-backend.onrender.com`. You need this
   for step 2.
5. **Known limitation, read this:** the free Render plan has no
   persistent disk. Uploaded files are saved to local disk in
   `app/api/uploads.py` (`settings.UPLOAD_DIR`) so they can be
   re-parsed on `/confirm` — on Render's free tier, that file
   disappears on every restart/redeploy. The _data_ is safe (it's
   written into Postgres on confirm), but the original uploaded file
   itself is not kept long-term. Fine for now; if you need the raw
   files kept permanently later, that means either a Render paid
   persistent disk or moving storage to something like S3 — don't
   build that until it's actually needed.

---

## 2. Frontend on Vercel

1. Go to vercel.com, sign up / log in, connect GitHub.
2. **Add New** → **Project** → pick this repo.
3. Vercel will ask for the root directory, set it to `frontend`
   (this repo has the frontend in a subfolder, not at the repo root).
   `frontend/vercel.json` handles the rest.
4. Before deploying, add an environment variable:
   - `NEXT_PUBLIC_API_URL` = the Render backend URL from step 1
     (e.g. `https://textile-bi-backend.onrender.com`, no trailing slash)
5. Deploy. Copy the resulting Vercel URL, e.g.
   `https://textile-bi.vercel.app`.

---

## 3. Connect them: update CORS on the backend

Right now the backend only trusts `http://localhost:3000`. Go back to
Render, open the backend service → **Environment**, and update:

- `CORS_ORIGINS` = `["https://textile-bi.vercel.app"]`
  (use your real Vercel URL from step 2, keep the brackets and quotes,
  it's parsed as JSON)

Save, Render redeploys automatically. Without this step, the frontend
will load but every API call will fail with a CORS error, so don't
skip it.

---

## 4. Test it yourself before he sees it

Open the Vercel URL and click through, in order:

1. Sign up (creates a company + your user)
2. Upload the sample file, or a real one
3. Confirm the import
4. Check the dashboard renders with real numbers

If any step fails, check the Render logs (Render dashboard → your
service → **Logs**) — that's where backend errors actually show up.

---

## A note on the free tiers

Render's free web service **spins down after 15 minutes of no traffic**
and takes 30-50 seconds to wake back up on the next request. If you're
demoing this live to the CEO, open the link a minute or two before he
looks at it, so it's already warm. This is a free-tier limitation, not
a bug, upgrading to a paid Render plan removes it whenever it's worth
the cost.
