import os
import requests
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from github import Github

BOT_TOKEN = "Your_token_bot_from_botfather"
ADMIN_ID = 123456678 #آیدی عددی خودتون از بات @userinfobot بگیرید اینجا بذارید.=

ASK_PAT, ASK_REPO = range(2)

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, pat TEXT, repo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('template', 'https://github.com/maanimis/github-sandbox')")
    conn.commit()
    conn.close()

def get_template_link():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='template'")
    res = c.fetchone()
    conn.close()
    return res[0] if res else ""

def set_template_link(link):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value) VALUES ('template', ?)", (link,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT pat, repo FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res

def save_user(user_id, pat, repo):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("REPLACE INTO users (user_id, pat, repo) VALUES (?, ?, ?)", (user_id, pat, repo))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    res = c.fetchall()
    conn.close()
    return [row[0] for row in res]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user:
        await update.message.reply_text("You are already set up. Send a file or link.\nUse /setup to update credentials.")
        return ConversationHandler.END
    
    template_link = get_template_link()
    await update.message.reply_text(
        f"Welcome!\nFirst, please fork this repository:\n{template_link}\n\n"
        "Now, send your GitHub Personal Access Token (PAT):"
    )
    return ASK_PAT

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please use /setup first.")
        return

    pat, repo_name = user
    message = update.message

    if message.document:
        file_obj = message.document
    elif message.video:
        file_obj = message.video
    elif message.audio:
        file_obj = message.audio
    elif message.photo:
        file_obj = message.photo[-1]
    else:
        await update.message.reply_text("Unsupported file type.")
        return

    msg = await update.message.reply_text("Downloading from Telegram...")

    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        file_name = getattr(file_obj, 'file_name', f"file_{file_obj.file_id}")
        
        resp = requests.get(tg_file.file_path)
        content = resp.content

        await msg.edit_text("Uploading to GitHub...")

        g = Github(pat)
        repo = g.get_repo(repo_name)
        file_path = f"downloads/{file_name}"
        
        try:
            repo.get_contents(file_path)
            await msg.edit_text("File already exists on GitHub.")
            return
        except:
            pass

        repo.create_file(file_path, f"Upload {file_name}", content, branch="main")
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/{file_path}"
        await msg.edit_text(f"Success!\n\nLink:\n{raw_url}")

    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Please use /setup first.")
        return

    pat, repo_name = user
    link = update.message.text.strip()
    msg = await update.message.reply_text("Triggering GitHub Action...")
    
    try:
        g = Github(pat)
        repo = g.get_repo(repo_name)
        
        readme = repo.get_contents("README.md")
        new_content = readme.decoded_content.decode() + " "
        
        repo.update_file(
            readme.path,
            f"download: {link}",
            new_content,
            readme.sha,
            branch="main"
        )
        await msg.edit_text("Action triggered via commit! File will be downloaded to repo soon.")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = get_all_users()
    await update.message.reply_text(f"Total users: {len(users)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
        
    message_text = " ".join(context.args)
    users = get_all_users()
    sent = 0
    
    msg = await update.message.reply_text("Broadcasting...")
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=message_text)
            sent += 1
        except:
            pass
    await msg.edit_text(f"Message sent to {sent} out of {len(users)} users.")

async def set_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /settemplate <github_url>")
        return
    new_link = context.args[0]
    set_template_link(new_link)
    await update.message.reply_text("Template link updated successfully.")

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
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("settemplate", set_template))
    app.add_handler(MessageHandler(filters.ATTACHMENT, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    app.run_polling()

if __name__ == "__main__":
    main()
