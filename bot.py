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

# user_data keys
SESSION = "session"  # list of question dicts
CURRENT = "current"  # index
SCORE = "score"
POLL_MAP = "poll_map"  # poll_id -> correct_option_id


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 Ona tili metodikasi bo'yicha test!\n\n"
        "Buyruqlar:\n"
        "/quiz10 — 10 ta savol\n"
        "/quiz20 — 20 ta savol\n"
        "/quiz50 — 50 ta savol\n"
        "/quizall — barcha 310 ta savol\n"
        "/stop — testni to'xtatish"
    )


async def begin_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE, count: int):
    questions = random.sample(ALL_QUESTIONS, min(count, len(ALL_QUESTIONS)))
    ctx.user_data[SESSION] = questions
    ctx.user_data[CURRENT] = 0
    ctx.user_data[SCORE] = 0
    ctx.user_data[POLL_MAP] = {}
    await update.message.reply_text(
        f"✅ Test boshlandi! {len(questions)} ta savol.\nHar bir savolga javob bering 👇"
    )
    await send_question(update.effective_chat.id, ctx)


async def send_question(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    session = ctx.user_data.get(SESSION, [])
    idx = ctx.user_data.get(CURRENT, 0)
    if idx >= len(session):
        await finish_quiz(chat_id, ctx)
        return

    q = session[idx]
    options = [q["correct"]] + q["wrong"]
    random.shuffle(options)
    correct_idx = options.index(q["correct"])

    # Telegram poll option max 100 chars
    options = [o[:100] for o in options]

    question_text = f"❓ {idx+1}/{len(session)}\n\n{q['q']}"
    question_text = question_text[:300]

    msg = await ctx.bot.send_poll(
        chat_id=chat_id,
        question=question_text,
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_idx,
        is_anonymous=False,
        open_period=30,
    )
    ctx.user_data[POLL_MAP][msg.poll.id] = correct_idx


async def poll_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id
    poll_map = ctx.user_data.get(POLL_MAP, {})

    if poll_id not in poll_map:
        return

    correct_idx = poll_map[poll_id]
    chosen = answer.option_ids[0] if answer.option_ids else -1

    if chosen == correct_idx:
        ctx.user_data[SCORE] = ctx.user_data.get(SCORE, 0) + 1

    ctx.user_data[CURRENT] = ctx.user_data.get(CURRENT, 0) + 1
    await send_question(answer.user.id, ctx)


async def finish_quiz(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    score = ctx.user_data.get(SCORE, 0)
    total = len(ctx.user_data.get(SESSION, []))
    pct = round(score / total * 100) if total else 0

    if pct >= 86:
        emoji = "🏆"
    elif pct >= 71:
        emoji = "✅"
    elif pct >= 56:
        emoji = "📚"
    else:
        emoji = "❌"

    await ctx.bot.send_message(
        chat_id=chat_id,
        text=(
            f"{emoji} Test yakunlandi!\n\n"
            f"To'g'ri javoblar: {score}/{total}\n"
            f"Natija: {pct}%\n\n"
            "Qayta boshlash uchun /quiz10, /quiz20, /quiz50 yoki /quizall"
        )
    )
    ctx.user_data.clear()


async def stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Test to'xtatildi. Qayta boshlash uchun /start")


async def quiz10(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await begin_quiz(update, ctx, 10)

async def quiz20(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await begin_quiz(update, ctx, 20)

async def quiz50(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await begin_quiz(update, ctx, 50)

async def quizall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await begin_quiz(update, ctx, 310)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz10", quiz10))
    app.add_handler(CommandHandler("quiz20", quiz20))
    app.add_handler(CommandHandler("quiz50", quiz50))
    app.add_handler(CommandHandler("quizall", quizall))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(PollAnswerHandler(poll_answer))
    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
