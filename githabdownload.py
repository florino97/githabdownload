import os
import re
import math
import base64
import requests
import sqlite3
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from github import Github

BOT_TOKEN = "TOKEN_BOT_FROM_BOTFATHER"
ADMIN_ID = 123456679 #یوزر ایدی اکانت تلگرامتان از @userinfobot بگیرید اینجا بذارید
CHUNK_SIZE = 45 * 1024 * 1024
ASK_PAT, ASK_REPO = range(2)

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, pat TEXT, repo TEXT, shorten INTEGER DEFAULT 0, banned INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('template', 'https://github.com/iphoenixon/youtube-sandbox')")
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else ""

def set_setting(key, value):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT pat, repo, shorten, banned FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res

def save_user(user_id, pat, repo):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, pat, repo, shorten, banned) VALUES (?, ?, ?, COALESCE((SELECT shorten FROM users WHERE user_id = ?), 0), COALESCE((SELECT banned FROM users WHERE user_id = ?), 0))", (user_id, pat, repo, user_id, user_id))
    conn.commit()
    conn.close()

def update_user_pref(user_id, field, value):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    res = c.fetchall()
    conn.close()
    return [row[0] for row in res]

def shorten_url(url):
    try:
        api_url = f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}"
        resp = requests.get(api_url, timeout=5)
        if resp.status_code == 200:
            return resp.text
    except:
        pass
    return url

def extract_package_name(play_url):
    match = re.search(r'id=([\w.]+)', play_url)
    return match.group(1) if match else None

def download_apk_from_google_play(play_url):
    pkg = extract_package_name(play_url)
    if not pkg:
        raise ValueError("Invalid Google Play URL")
    download_page = f"https://apkcombo.com/downloader/{pkg}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(download_page, headers=headers, timeout=30)
    resp.raise_for_status()
    direct_link_match = re.search(r'href="(https://download\.apkcombo\.com/.*?)"', resp.text)
    if not direct_link_match:
        raise Exception("APK download link not found")
    direct_url = direct_link_match.group(1).replace("&amp;", "&")
    apk_resp = requests.get(direct_url, headers=headers, timeout=300, stream=True)
    apk_resp.raise_for_status()
    return f"{pkg}.apk", apk_resp.content

def upload_single_file(repo, path, content_bytes, commit_msg, shorten=False):
    content_b64 = base64.b64encode(content_bytes).decode()
    repo.create_file(path, commit_msg, content_b64, branch="main")
    raw_url = f"https://raw.githubusercontent.com/{repo.full_name}/main/{path}"
    return shorten_url(raw_url) if shorten else raw_url

def upload_file_chunked(repo, base_path, content_bytes, commit_msg, shorten=False):
    total_size = len(content_bytes)
    chunk_count = math.ceil(total_size / CHUNK_SIZE)
    raw_urls = []
    for i in range(chunk_count):
        start = i * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, total_size)
        chunk = content_bytes[start:end]
        part_path = f"{base_path}.part{i+1:03d}"
        url = upload_single_file(repo, part_path, chunk, f"{commit_msg} part {i+1}/{chunk_count}", shorten)
        raw_urls.append(url)
    return raw_urls, chunk_count

def upload_to_github(pat, repo_name, file_name, content_bytes, shorten=False):
    g = Github(pat)
    repo = g.get_repo(repo_name)
    base_path = f"downloads/{file_name}"
    total_size = len(content_bytes)
    if total_size <= CHUNK_SIZE:
        return upload_single_file(repo, base_path, content_bytes, f"Upload {file_name}", shorten), None
    else:
        return upload_file_chunked(repo, base_path, content_bytes, f"Upload {file_name}", shorten)

async def check_ban(update: Update):
    user = get_user(update.effective_user.id)
    if user and user[3] == 1:
        await update.message.reply_text("You are banned from using this bot.")
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    user = get_user(update.effective_user.id)
    if user:
        await update.message.reply_text("You are already set up. Send a file or link.\nCommands:\n/setup, /files, /delete, /status, /rename, /shorten")
        return ConversationHandler.END
    template_link = get_setting("template")
    await update.message.reply_text(f"Welcome!\n1. Fork this repository: {template_link}\n2. Go to Settings > Actions > General > Workflow permissions > Read and write permissions.\n\nNow, send your GitHub Personal Access Token (PAT):")
    return ASK_PAT

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    await update.message.reply_text("Send your GitHub Personal Access Token (PAT):")
    return ASK_PAT

async def ask_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pat'] = update.message.text.strip()
    await update.message.reply_text("Now, send your repository name (format: username/repo):")
    return ASK_REPO

async def save_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo = update.message.text.strip()
    pat = context.user_data.get('pat')
    save_user(update.effective_user.id, pat, repo)
    await update.message.reply_text("Setup complete! You can now send files or links.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Setup cancelled.")
    return ConversationHandler.END

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    user = get_user(update.effective_user.id)
    if not user: return await update.message.reply_text("Use /setup first.")
    pat, repo_name, shorten_opt, _ = user
    msg = await update.message.reply_text("Fetching files...")
    try:
        g = Github(pat)
        repo = g.get_repo(repo_name)
        try:
            contents = repo.get_contents("downloads")
        except:
            contents = repo.get_contents("")
        files = [f.name for f in contents if f.type == "file"]
        if not files:
            await msg.edit_text("No files found.")
            return
        text = "\n".join([f"- {f}" for f in files])
        await msg.edit_text(f"Files in repository:\n{text}\n\nUse /delete <filename> to remove a file.")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    if not context.args: return await update.message.reply_text("Usage: /delete <filename>")
    user = get_user(update.effective_user.id)
    if not user: return await update.message.reply_text("Use /setup first.")
    pat, repo_name, _, _ = user
    filename = " ".join(context.args)
    msg = await update.message.reply_text("Deleting...")
    try:
        g = Github(pat)
        repo = g.get_repo(repo_name)
        try:
            file_obj = repo.get_contents(f"downloads/{filename}")
        except:
            file_obj = repo.get_contents(filename)
        repo.delete_file(file_obj.path, f"Delete {filename}", file_obj.sha, branch="main")
        await msg.edit_text(f"Deleted {filename} successfully.")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")

async def repo_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    user = get_user(update.effective_user.id)
    if not user: return await update.message.reply_text("Use /setup first.")
    pat, repo_name, _, _ = user
    msg = await update.message.reply_text("Fetching status...")
    try:
        g = Github(pat)
        repo = g.get_repo(repo_name)
        size_mb = repo.size / 1024
        await msg.edit_text(f"Repo: {repo.full_name}\nSize: {size_mb:.2f} MB\nVisibility: {repo.visibility}")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")

async def toggle_shorten(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    user = get_user(update.effective_user.id)
    if not user: return await update.message.reply_text("Use /setup first.")
    new_val = 1 if user[2] == 0 else 0
    update_user_pref(update.effective_user.id, "shorten", new_val)
    status = "ON" if new_val == 1 else "OFF"
    await update.message.reply_text(f"URL Shortening is now {status}.")

async def handle_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    if not context.args or not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a file with /rename <new_name.ext>")
    context.user_data['custom_name'] = " ".join(context.args)
    await handle_file(update.message.reply_to_message, context, is_rename=True)

async def handle_file(update_or_msg, context: ContextTypes.DEFAULT_TYPE, is_rename=False):
    if isinstance(update_or_msg, Update):
        if await check_ban(update_or_msg): return
        message = update_or_msg.message
        user_id = update_or_msg.effective_user.id
    else:
        message = update_or_msg
        user_id = message.from_user.id

    user = get_user(user_id)
    if not user: return await message.reply_text("Use /setup first.")
    pat, repo_name, shorten_opt, _ = user

    file_obj = message.document or message.video or message.audio or (message.photo[-1] if message.photo else None)
    if not file_obj: return await message.reply_text("Unsupported file type.")

    msg = await message.reply_text("Downloading from Telegram...")
    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        file_name = context.user_data.pop('custom_name', getattr(file_obj, 'file_name', f"file_{file_obj.file_id}"))
        resp = requests.get(tg_file.file_path)
        content = resp.content
        await msg.edit_text("Uploading to GitHub...")
        result, chunk_count = upload_to_github(pat, repo_name, file_name, content, shorten=bool(shorten_opt))
        if chunk_count is None:
            await msg.edit_text(f"Success!\n\nLink:\n{result}")
        else:
            parts_text = "\n".join([f"Part {i+1}: {url}" for i, url in enumerate(result)])
            await msg.edit_text(f"Success! (split into {chunk_count} parts)\n\n{parts_text}")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}\n\n(Note: Telegram bots have a 20MB file download limit without a local server).")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_ban(update): return
    user = get_user(update.effective_user.id)
    if not user: return await update.message.reply_text("Use /setup first.")
    pat, repo_name, shorten_opt, _ = user
    link = update.message.text.strip()
    msg = await update.message.reply_text("Processing link...")

    if "play.google.com" in link:
        try:
            file_name, content = download_apk_from_google_play(link)
            await msg.edit_text("Uploading APK to GitHub...")
            result, chunk_count = upload_to_github(pat, repo_name, file_name, content, shorten=bool(shorten_opt))
            if chunk_count is None:
                await msg.edit_text(f"Success!\n\nLink:\n{result}")
            else:
                parts_text = "\n".join([f"Part {i+1}: {url}" for i, url in enumerate(result)])
                await msg.edit_text(f"Success! (split into {chunk_count} parts)\n\n{parts_text}")
        except Exception as e:
            await msg.edit_text(f"Error: {str(e)}")
    else:
        try:
            g = Github(pat)
            repo = g.get_repo(repo_name)
            try:
                readme = repo.get_contents("README.md")
                new_content = readme.decoded_content.decode() + " \n"
                repo.update_file(readme.path, f"download: {link}", new_content, readme.sha, branch="main")
            except:
                repo.create_file("README.md", f"download: {link}", "Init", branch="main")
            await msg.edit_text("Action triggered via commit!\nCheck your GitHub Actions tab. Use /files later to retrieve it.")
        except Exception as e:
            await msg.edit_text(f"Error: {str(e)}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    users = get_all_users()
    await update.message.reply_text(f"Total users: {len(users)}")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return await update.message.reply_text("Usage: /broadcast <message>")
    message_text = " ".join(context.args)
    users = get_all_users()
    sent = 0
    msg = await update.message.reply_text("Broadcasting...")
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=message_text)
            sent += 1
        except: pass
    await msg.edit_text(f"Sent to {sent}/{len(users)} users.")

async def admin_set_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return await update.message.reply_text("Usage: /settemplate <url>")
    set_setting("template", context.args[0])
    await update.message.reply_text("Template updated.")

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return await update.message.reply_text("Usage: /ban <user_id>")
    update_user_pref(int(context.args[0]), "banned", 1)
    await update.message.reply_text(f"User {context.args[0]} banned.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return await update.message.reply_text("Usage: /unban <user_id>")
    update_user_pref(int(context.args[0]), "banned", 0)
    await update.message.reply_text(f"User {context.args[0]} unbanned.")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("setup", setup)],
        states={
            ASK_PAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_repo)],
            ASK_REPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_credentials)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("files", list_files))
    app.add_handler(CommandHandler("delete", delete_file))
    app.add_handler(CommandHandler("status", repo_status))
    app.add_handler(CommandHandler("shorten", toggle_shorten))
    app.add_handler(CommandHandler("rename", handle_rename))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("settemplate", admin_set_template))
    app.add_handler(CommandHandler("ban", admin_ban))
    app.add_handler(CommandHandler("unban", admin_unban))
    app.add_handler(MessageHandler(filters.ATTACHMENT, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.run_polling()

if __name__ == "__main__":
    main()
