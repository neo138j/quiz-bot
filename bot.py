import os
import json
import random
import logging
from telegram import Update, Poll
from telegram.ext import (
    Application, CommandHandler, PollAnswerHandler, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")

with open("questions.json", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

BLOCKS = {
    "b1": ALL_QUESTIONS[0:50],
    "b2": ALL_QUESTIONS[50:100],
    "b3": ALL_QUESTIONS[100:150],
    "b4": ALL_QUESTIONS[150:200],
    "b5": ALL_QUESTIONS[200:250],
    "b6": ALL_QUESTIONS[250:310],
}

BLOCK_NAMES = {
    "b1": "Blok 1 (1-50)",
    "b2": "Blok 2 (51-100)",
    "b3": "Blok 3 (101-150)",
    "b4": "Blok 4 (151-200)",
    "b5": "Blok 5 (201-250)",
    "b6": "Blok 6 (251-310)",
}

# Таблица лидеров: {user_id: {"name": str, "best_pct": int, "title": str}}
LEADERBOARD = {}


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 Ona tili metodikasi bo'yicha test!\n\n"
        "📦 Bloklar bo'yicha (50 ta savol):\n"
        "/quiz_b1 — Blok 1 (1-50)\n"
        "/quiz_b2 — Blok 2 (51-100)\n"
        "/quiz_b3 — Blok 3 (101-150)\n"
        "/quiz_b4 — Blok 4 (151-200)\n"
        "/quiz_b5 — Blok 5 (201-250)\n"
        "/quiz_b6 — Blok 6 (251-310)\n\n"
        "🎲 Aralash:\n"
        "/quiz10 — 10 ta savol\n"
        "/quiz20 — 20 ta savol\n"
        "/quiz50 — 50 ta savol\n"
        "/quizall — barcha 310 ta savol\n\n"
        "🏆 /top — liderlar jadvali\n"
        "/stop — testni to'xtatish"
    )


async def begin_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE, questions: list, title: str):
    ctx.user_data["session"] = questions
    ctx.user_data["current"] = 0
    ctx.user_data["score"] = 0
    ctx.user_data["poll_map"] = {}
    ctx.user_data["title"] = title
    await update.message.reply_text(f"✅ {title}\n{len(questions)} ta savol. Boshlandi! 👇")
    await send_question(update.effective_chat.id, ctx)


async def send_question(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    session = ctx.user_data.get("session", [])
    idx = ctx.user_data.get("current", 0)
    if idx >= len(session):
        await finish_quiz(chat_id, ctx)
        return
    q = session[idx]
    options = [q["correct"]] + q["wrong"]
    random.shuffle(options)
    correct_idx = options.index(q["correct"])
    options = [o[:100] for o in options]
    question_text = f"❓ {idx+1}/{len(session)}\n\n{q['q']}"[:300]
    msg = await ctx.bot.send_poll(
        chat_id=chat_id,
        question=question_text,
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_idx,
        is_anonymous=False,
        open_period=30,
    )
    ctx.user_data["poll_map"][msg.poll.id] = correct_idx


async def poll_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id
    poll_map = ctx.user_data.get("poll_map", {})
    if poll_id not in poll_map:
        return
    correct_idx = poll_map[poll_id]
    chosen = answer.option_ids[0] if answer.option_ids else -1
    if chosen == correct_idx:
        ctx.user_data["score"] = ctx.user_data.get("score", 0) + 1
    ctx.user_data["current"] = ctx.user_data.get("current", 0) + 1
    await send_question(answer.user.id, ctx)


async def finish_quiz(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    score = ctx.user_data.get("score", 0)
    total = len(ctx.user_data.get("session", []))
    title = ctx.user_data.get("title", "Test")
    pct = round(score / total * 100) if total else 0
    user_id = ctx.user_data.get("user_id")
    user_name = ctx.user_data.get("user_name", "Noma'lum")

    if pct >= 86:
        emoji = "🏆"
    elif pct >= 71:
        emoji = "✅"
    elif pct >= 56:
        emoji = "📚"
    else:
        emoji = "❌"

    # Обновляем таблицу лидеров
    if user_id:
        prev = LEADERBOARD.get(user_id, {})
        if pct > prev.get("best_pct", 0):
            LEADERBOARD[user_id] = {
                "name": user_name,
                "best_pct": pct,
                "title": title,
                "score": score,
                "total": total,
            }

    await ctx.bot.send_message(
        chat_id=chat_id,
        text=(
            f"{emoji} {title} yakunlandi!\n\n"
            f"To'g'ri javoblar: {score}/{total}\n"
            f"Natija: {pct}%\n\n"
            "Qayta boshlash uchun /start\n"
            "🏆 Liderlar jadvali: /top"
        )
    )
    ctx.user_data.clear()


async def top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not LEADERBOARD:
        await update.message.reply_text("🏆 Liderlar jadvali hali bo'sh!\n\nTest topshiring va birinchi bo'ling!")
        return

    sorted_lb = sorted(LEADERBOARD.values(), key=lambda x: x["best_pct"], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    text = "🏆 TOP-10 Liderlar\n\n"
    for i, user in enumerate(sorted_lb):
        text += f"{medals[i]} {user['name']} — {user['best_pct']}% ({user['score']}/{user['total']})\n"
        text += f"   📚 {user['title']}\n"

    await update.message.reply_text(text)


async def stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Test to'xtatildi. /start")


async def begin_quiz_with_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE, questions: list, title: str):
    user = update.effective_user
    ctx.user_data["user_id"] = user.id
    ctx.user_data["user_name"] = user.full_name or user.username or "Noma'lum"
    await begin_quiz(update, ctx, questions, title)


async def quiz_b1(update, ctx): await begin_quiz_with_user(update, ctx, BLOCKS["b1"].copy(), BLOCK_NAMES["b1"])
async def quiz_b2(update, ctx): await begin_quiz_with_user(update, ctx, BLOCKS["b2"].copy(), BLOCK_NAMES["b2"])
async def quiz_b3(update, ctx): await begin_quiz_with_user(update, ctx, BLOCKS["b3"].copy(), BLOCK_NAMES["b3"])
async def quiz_b4(update, ctx): await begin_quiz_with_user(update, ctx, BLOCKS["b4"].copy(), BLOCK_NAMES["b4"])
async def quiz_b5(update, ctx): await begin_quiz_with_user(update, ctx, BLOCKS["b5"].copy(), BLOCK_NAMES["b5"])
async def quiz_b6(update, ctx): await begin_quiz_with_user(update, ctx, BLOCKS["b6"].copy(), BLOCK_NAMES["b6"])
async def quiz10(update, ctx): await begin_quiz_with_user(update, ctx, random.sample(ALL_QUESTIONS, 10), "Aralash 10 ta savol")
async def quiz20(update, ctx): await begin_quiz_with_user(update, ctx, random.sample(ALL_QUESTIONS, 20), "Aralash 20 ta savol")
async def quiz50(update, ctx): await begin_quiz_with_user(update, ctx, random.sample(ALL_QUESTIONS, 50), "Aralash 50 ta savol")
async def quizall(update, ctx): await begin_quiz_with_user(update, ctx, ALL_QUESTIONS.copy(), "Barcha 310 ta savol")


def main():
    app = Application.builder().token(TOKEN).build()
    for cmd, handler in [
        ("start", start), ("top", top),
        ("quiz_b1", quiz_b1), ("quiz_b2", quiz_b2),
        ("quiz_b3", quiz_b3), ("quiz_b4", quiz_b4),
        ("quiz_b5", quiz_b5), ("quiz_b6", quiz_b6),
        ("quiz10", quiz10), ("quiz20", quiz20),
        ("quiz50", quiz50), ("quizall", quizall),
        ("stop", stop),
    ]:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(PollAnswerHandler(poll_answer))
    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
