import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Файл для зберігання даних
DATA_FILE = 'matches.json'

# Команди (список назв) – ви можете змінити на свої
TEAMS = ["Олишівка", "Ріпки", "Любеч", "Куликівка", "М.К"]

# Допоміжна функція для завантаження матчів з файлу
def load_matches():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Допоміжна функція для збереження матчів
def save_matches(matches):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(matches, f, ensure_ascii=False, indent=4)

# Функція для обчислення очок за матч
def calculate_points(sets):
    team1_sets = 0
    team2_sets = 0
    for set_score in sets:
        parts = set_score.split('/')
        if len(parts) != 2:
            return None
        try:
            s1 = int(parts[0])
            s2 = int(parts[1])
        except ValueError:
            return None
        if s1 > s2:
            team1_sets += 1
        elif s2 > s1:
            team2_sets += 1

    if team1_sets == team2_sets:
        return None

    winner_sets = max(team1_sets, team2_sets)
    loser_sets = min(team1_sets, team2_sets)

    if winner_sets - loser_sets >= 2:
        pts_winner = 3
        pts_loser = 0
    else:
        pts_winner = 2
        pts_loser = 1

    if team1_sets > team2_sets:
        return (pts_winner, pts_loser, team1_sets, team2_sets)
    else:
        return (pts_loser, pts_winner, team1_sets, team2_sets)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Вітаю! Це бот для турнірної таблиці.\n\n"
        "Команди:\n"
        "/addmatch – додати результат матчу\n"
        "/table – показати турнірну таблицю\n"
        "/reset – очистити всі результати\n\n"
        "Формат додавання матчу:\n"
        "/addmatch Команда1 Команда2 25/20 20/25 15/10\n"
        "Сетів може бути 3, 4 або 5."
    )

# Команда /addmatch
async def addmatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace('/addmatch', '').strip()
    if not text:
        await update.message.reply_text("Будь ласка, вкажіть дані матчу. Наприклад:\n/addmatch Динамо Шахтар 25/20 20/25 15/10")
        return

    parts = text.split()
    if len(parts) < 4:
        await update.message.reply_text("Недостатньо даних. Потрібно: назва1 назва2 сет1 сет2 ...")
        return

    team1 = parts[0]
    team2 = parts[1]
    sets = parts[2:]

    if team1 not in TEAMS or team2 not in TEAMS:
        await update.message.reply_text(f"Команди мають бути зі списку: {', '.join(TEAMS)}")
        return

    result = calculate_points(sets)
    if result is None:
        await update.message.reply_text("Помилка у форматі сетів. Кожен сет має бути у вигляді 'число/число', наприклад 25/20.")
        return

    pts1, pts2, sets1, sets2 = result

    matches = load_matches()
    match = {
        'team1': team1,
        'team2': team2,
        'sets': sets,
        'team1_sets': sets1,
        'team2_sets': sets2,
        'team1_pts': pts1,
        'team2_pts': pts2
    }
    matches.append(match)
    save_matches(matches)

    await update.message.reply_text(
        f"Матч додано!\n"
        f"{team1} - {team2} {sets1}:{sets2}\n"
        f"Очки: {team1} {pts1}, {team2} {pts2}"
    )

# Команда /table
async def table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = load_matches()
    if not matches:
        await update.message.reply_text("Ще не додано жодного матчу.")
        return

    stats = {team: {
        'games': 0,
        'wins': 0,
        'losses': 0,
        'sets_for': 0,
        'sets_against': 0,
        'points': 0
    } for team in TEAMS}

    for match in matches:
        t1 = match['team1']
        t2 = match['team2']
        s1 = match['team1_sets']
        s2 = match['team2_sets']
        p1 = match['team1_pts']
        p2 = match['team2_pts']

        stats[t1]['games'] += 1
        stats[t1]['sets_for'] += s1
        stats[t1]['sets_against'] += s2
        stats[t1]['points'] += p1
        if p1 > p2:
            stats[t1]['wins'] += 1
        else:
            stats[t1]['losses'] += 1

        stats[t2]['games'] += 1
        stats[t2]['sets_for'] += s2
        stats[t2]['sets_against'] += s1
        stats[t2]['points'] += p2
        if p2 > p1:
            stats[t2]['wins'] += 1
        else:
            stats[t2]['losses'] += 1

    table_rows = []
    for team, data in stats.items():
        sets_diff = data['sets_for'] - data['sets_against']
        table_rows.append((
            team,
            data['games'],
            data['wins'],
            data['losses'],
            data['sets_for'],
            data['sets_against'],
            sets_diff,
            data['points']
        ))

    table_rows.sort(key=lambda x: (x[7], x[6]), reverse=True)

    msg = "🏆 *Турнірна таблиця*\n\n"
    msg += "```\n"
    header = f"{'Команда':<10} {'І':<2} {'В':<2} {'П':<2} {'СЗ':<3} {'СП':<3} {'РС':<3} {'О':<2}"
    msg += header + "\n"
    msg += "-" * 40 + "\n"
    for row in table_rows:
        team, g, w, l, sf, sa, sd, pts = row
        msg += f"{team:<10} {g:<2} {w:<2} {l:<2} {sf:<3} {sa:<3} {sd:<3} {pts:<2}\n"
    msg += "```"
    await update.message.reply_text(msg, parse_mode='Markdown')

# Команда /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Так, очистити", callback_data='confirm_reset')],
        [InlineKeyboardButton("Ні, скасувати", callback_data='cancel_reset')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Ви впевнені, що хочете видалити всі результати?", reply_markup=reply_markup)

# Обробник натискання кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'confirm_reset':
        save_matches([])
        await query.edit_message_text(text="Усі результати видалено.")
    else:
        await query.edit_message_text(text="Скасовано.")

# Головна функція
def main():
    # ВСТАВТЕ СВІЙ ТОКЕН СЮДИ!
    TOKEN = '8641112268:AAGCy3v1HA3jToARcrKRtZMEAPwpws7F-bQ'

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addmatch", addmatch))
    application.add_handler(CommandHandler("table", table))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(MessageHandler(filters.Text(), button_handler))

    print("Бот запущено...")
    application.run_polling()

if __name__ == '__main__':
    main()