import sys
import os

# Ensure src/ is on sys.path[0] so config.py computes ROOT_DIR correctly:
#   ROOT_DIR = os.path.dirname(sys.path[0])  →  project root
_src_dir = os.path.dirname(os.path.abspath(__file__))
if sys.path and sys.path[0] != _src_dir:
    sys.path.insert(0, _src_dir)
sys.path[0] = _src_dir

from flask import Flask, render_template, request, jsonify, abort  # noqa: E402
import threading  # noqa: E402
import json  # noqa: E402
from uuid import uuid4  # noqa: E402

from cache import get_accounts, add_account, remove_account, get_products, add_product  # noqa: E402
from config import ROOT_DIR, assert_folder_structure, get_ollama_model, get_openrouter_api_key, get_openrouter_model  # noqa: E402
from utils import rem_temp_files  # noqa: E402
import llm_provider  # noqa: E402

_templates = os.path.join(_src_dir, "..", "templates")
_static = os.path.join(_src_dir, "..", "static")

app = Flask(__name__, template_folder=_templates, static_folder=_static)

# ── In-memory task registry ────────────────────────────────────────────────────

_tasks: dict[str, dict] = {}


def _new_task() -> str:
    tid = str(uuid4())
    _tasks[tid] = {"status": "running", "message": "Working…"}
    return tid


def _run_in_bg(tid: str, fn, *args, **kwargs) -> None:
    def wrapper():
        try:
            msg = fn(*args, **kwargs)
            _tasks[tid] = {"status": "done", "message": msg or "Done"}
        except Exception as exc:
            _tasks[tid] = {"status": "error", "message": str(exc)}

    threading.Thread(target=wrapper, daemon=True).start()


# ── Startup init ───────────────────────────────────────────────────────────────

def _init() -> None:
    assert_folder_structure()
    try:
        rem_temp_files()
    except Exception:
        pass
    try:
        if get_openrouter_api_key():
            llm_provider.select_model(get_openrouter_model())
        else:
            model = get_ollama_model()
            if model:
                llm_provider.select_model(model)
    except Exception:
        pass


# ── API: tasks ─────────────────────────────────────────────────────────────────

@app.get("/api/task/<tid>")
def api_task(tid):
    return jsonify(_tasks.get(tid, {"status": "not_found", "message": ""}))


# ── API: accounts ──────────────────────────────────────────────────────────────

@app.get("/api/accounts/<provider>")
def api_get_accounts(provider):
    if provider not in ("youtube", "twitter"):
        abort(400)
    return jsonify(get_accounts(provider))


@app.post("/api/accounts/<provider>")
def api_add_account(provider):
    if provider not in ("youtube", "twitter"):
        abort(400)
    data = request.get_json(force=True)
    data["id"] = str(uuid4())
    if provider == "youtube":
        data.setdefault("videos", [])
    else:
        data.setdefault("posts", [])
    add_account(provider, data)
    return jsonify({"id": data["id"]})


@app.delete("/api/accounts/<provider>/<account_id>")
def api_delete_account(provider, account_id):
    if provider not in ("youtube", "twitter"):
        abort(400)
    remove_account(provider, account_id)
    return jsonify({"ok": True})


# ── API: videos / posts ────────────────────────────────────────────────────────

@app.get("/api/videos/<account_id>")
def api_videos(account_id):
    for acc in get_accounts("youtube"):
        if acc["id"] == account_id:
            return jsonify(acc.get("videos", []))
    return jsonify([])


@app.get("/api/posts/<account_id>")
def api_posts(account_id):
    for acc in get_accounts("twitter"):
        if acc["id"] == account_id:
            return jsonify(acc.get("posts", []))
    return jsonify([])


# ── API: products ──────────────────────────────────────────────────────────────

@app.get("/api/products")
def api_get_products():
    return jsonify(get_products())


@app.post("/api/products")
def api_add_product():
    data = request.get_json(force=True)
    data["id"] = str(uuid4())
    add_product(data)
    return jsonify({"id": data["id"]})


# ── API: config ────────────────────────────────────────────────────────────────

@app.get("/api/config")
def api_get_config():
    cfg_path = os.path.join(ROOT_DIR, "config.json")
    if not os.path.exists(cfg_path):
        return jsonify({})
    with open(cfg_path) as f:
        return jsonify(json.load(f))


@app.post("/api/config")
def api_save_config():
    data = request.get_json(force=True)
    cfg_path = os.path.join(ROOT_DIR, "config.json")
    with open(cfg_path, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"ok": True})


# ── API: Ollama models ─────────────────────────────────────────────────────────

@app.get("/api/models")
def api_models():
    try:
        return jsonify(llm_provider.list_models())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 503


@app.post("/api/models/select")
def api_select_model():
    model = request.get_json(force=True).get("model")
    if not model:
        abort(400)
    llm_provider.select_model(model)
    return jsonify({"active": model})


@app.get("/api/models/active")
def api_active_model():
    return jsonify({"model": llm_provider.get_active_model()})


# ── API: dashboard stats ───────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats():
    yt_accounts = get_accounts("youtube")
    tw_accounts = get_accounts("twitter")
    total_videos = sum(len(a.get("videos", [])) for a in yt_accounts)
    total_posts = sum(len(a.get("posts", [])) for a in tw_accounts)
    return jsonify({
        "youtube_accounts": len(yt_accounts),
        "twitter_accounts": len(tw_accounts),
        "videos_generated": total_videos,
        "tweets_posted": total_posts,
        "products": len(get_products()),
    })


# ── Background task helpers ────────────────────────────────────────────────────

def _youtube_generate(account_id: str, upload: bool) -> str:
    from classes.YouTube import YouTube  # noqa: PLC0415
    from classes.Tts import TTS  # noqa: PLC0415

    accounts = get_accounts("youtube")
    acc = next((a for a in accounts if a["id"] == account_id), None)
    if not acc:
        raise ValueError(f"Account {account_id} not found")
    yt = YouTube(acc["id"], acc["nickname"], acc["firefox_profile"], acc["niche"], acc["language"])
    tts = TTS()
    yt.generate_video(tts)
    if upload:
        yt.upload_video()
    return "Video generated" + (" and uploaded" if upload else "")


def _twitter_post(account_id: str) -> str:
    from classes.Twitter import Twitter  # noqa: PLC0415

    accounts = get_accounts("twitter")
    acc = next((a for a in accounts if a["id"] == account_id), None)
    if not acc:
        raise ValueError(f"Account {account_id} not found")
    tw = Twitter(
        acc["id"],
        acc["nickname"],
        acc["firefox_profile"],
        acc["topic"],
    )
    tw.post()
    return "Tweet posted"


def _afm_run(product_id: str) -> str:
    from classes.AFM import AffiliateMarketing  # noqa: PLC0415

    products = get_products()
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        raise ValueError(f"Product {product_id} not found")
    accounts = get_accounts("twitter")
    acc = next((a for a in accounts if a["id"] == product["twitter_uuid"]), None)
    if not acc:
        raise ValueError("Linked Twitter account not found")
    afm = AffiliateMarketing(
        product["affiliate_link"],
        acc["firefox_profile"],
        acc["id"],
        acc["nickname"],
        acc["topic"],
    )
    afm.generate_pitch()
    afm.share_pitch("twitter")
    return "Pitch generated and shared"


def _outreach_run() -> str:
    from classes.Outreach import Outreach  # noqa: PLC0415

    o = Outreach()
    o.start()
    return "Outreach completed"


# ── API: action endpoints ──────────────────────────────────────────────────────

@app.post("/api/youtube/generate")
def api_youtube_generate():
    body = request.get_json(force=True)
    account_id = body.get("account_id")
    if not account_id:
        abort(400)
    tid = _new_task()
    _run_in_bg(tid, _youtube_generate, account_id, bool(body.get("upload")))
    return jsonify({"task_id": tid})


@app.post("/api/twitter/post")
def api_twitter_post():
    body = request.get_json(force=True)
    account_id = body.get("account_id")
    if not account_id:
        abort(400)
    tid = _new_task()
    _run_in_bg(tid, _twitter_post, account_id)
    return jsonify({"task_id": tid})


@app.post("/api/afm/run")
def api_afm_run():
    body = request.get_json(force=True)
    product_id = body.get("product_id")
    if not product_id:
        abort(400)
    tid = _new_task()
    _run_in_bg(tid, _afm_run, product_id)
    return jsonify({"task_id": tid})


@app.post("/api/outreach/run")
def api_outreach_run():
    tid = _new_task()
    _run_in_bg(tid, _outreach_run)
    return jsonify({"task_id": tid})


# ── Page routes ────────────────────────────────────────────────────────────────

@app.get("/")
def page_index():
    return render_template("index.html")


@app.get("/youtube")
def page_youtube():
    return render_template("youtube.html")


@app.get("/twitter")
def page_twitter():
    return render_template("twitter.html")


@app.get("/afm")
def page_afm():
    return render_template("afm.html")


@app.get("/outreach")
def page_outreach():
    return render_template("outreach.html")


@app.get("/config")
def page_config():
    return render_template("config_page.html")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _init()
    print("MoneyPrinterV2 Web UI starting on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
