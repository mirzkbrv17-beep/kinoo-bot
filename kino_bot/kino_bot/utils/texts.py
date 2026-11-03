"""Ko'p tilli matnlar (uz / ru) va menyu elementlari."""

LANGS = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский"}

# (kalit, zaxira emoji) — foydalanuvchi menyusi tartibi
MENU = [
    ("search", "🔍"), ("favorites", "❤️"), ("vip", "👑"),
    ("genres", "🎭"), ("series", "📺"), ("cartoons", "🧸"),
    ("random", "🎲"), ("stats", "📊"), ("request", "✉️"),
    ("history", "🕘"), ("recs", "⭐"), ("language", "🌐"),
    ("news", "📰"), ("invite", "👥"), ("help", "❓"),
    ("contact", "💬"), ("settings", "⚙️"),
]
MENU_FALLBACK = dict(MENU)

T = {
    "uz": {
        "menu_search": "Kino qidirish", "menu_favorites": "Sevimlilar", "menu_vip": "VIP kinolar",
        "menu_genres": "Janrlar", "menu_series": "Seriallar", "menu_cartoons": "Multfilmlar",
        "menu_random": "Tasodifiy kino", "menu_stats": "Statistika", "menu_request": "Kino so'rash",
        "menu_history": "Ko'rish tarixi", "menu_recs": "Tavsiyalar", "menu_language": "Tilni o'zgartirish",
        "menu_news": "Yangiliklar", "menu_invite": "Do'st taklif qilish", "menu_help": "Yordam",
        "menu_contact": "Admin bilan bog'lanish", "menu_settings": "Sozlamalar",
        "welcome": "👋 Salom, <b>{name}</b>!\n\n🎬 Kino botga xush kelibsiz.\n🔑 Kino <b>kodini</b> yuboring — kino darhol keladi.\n🔍 Yoki kino nomini yozing.",
        "menu_hint": "Menyudan tanlang 👇",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Til o'zgartirildi.",
        "sub_required": "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, so'ng «Obunani tekshirish» tugmasini bosing:",
        "sub_check": "✅ Obunani tekshirish",
        "sub_not_yet": "❌ Siz hali barcha kanallarga obuna bo'lmagansiz!",
        "sub_ok": "✅ Rahmat! Obuna tasdiqlandi.",
        "banned": "🚫 Siz botdan foydalanishdan chetlatilgansiz.",
        "not_found": "😔 Bunday kod yoki nomdagi kino topilmadi.\n\nKodni to'g'ri yozing yoki «Kino qidirish» orqali nom bilan qidiring.",
        "search_prompt": "🔍 Kino <b>nomini</b> yoki <b>kodini</b> yozing:",
        "search_results": "🔍 «{q}» bo'yicha natijalar:",
        "empty": "📭 Hozircha bo'sh.",
        "fav_added": "❤️ Sevimlilarga qo'shildi", "fav_removed": "💔 Sevimlilardan o'chirildi",
        "fav_title": "❤️ <b>Sevimlilar</b>", "hist_title": "🕘 <b>Ko'rish tarixi</b>",
        "vip_locked": "👑 Bu <b>VIP</b> kontent. Ko'rish uchun VIP obuna kerak.",
        "vip_on": "👑 VIP faol: <b>{date}</b> gacha ({days} kun qoldi)",
        "vip_off": "👑 Sizda VIP obuna yo'q.",
        "vip_title": "👑 <b>VIP kinolar</b>",
        "vip_buy": "💳 {days} kun — {stars} ⭐",
        "vip_no_plans": "To'lov hozircha sozlanmagan. Admin bilan bog'laning.",
        "vip_thanks": "🎉 To'lov qabul qilindi! VIP {date} gacha faol.",
        "vip_expired": "⌛ VIP obunangiz muddati tugadi.",
        "genres_title": "🎭 Janrni tanlang:", "series_title": "📺 <b>Seriallar</b>",
        "cartoons_title": "🧸 <b>Multfilmlar</b>", "seasons_title": "📋 Faslni tanlang:",
        "episodes_title": "▶️ Qismni tanlang:", "genre_list": "🎭 <b>{name}</b>",
        "stats_title": "📊 <b>Statistika</b>", "total_movies": "🎞 Jami kinolar: <b>{n}</b>",
        "st_all": "🏆 TOP 10", "st_today": "📅 Bugun", "st_week": "🗓 Hafta", "st_month": "📆 Oy", "st_vip": "👑 VIP TOP",
        "req_prompt": "✉️ Qidirayotgan kino nomini yozing (yili bo'lsa ham yozing):",
        "req_sent": "✅ So'rovingiz adminlarga yuborildi.",
        "req_ok": "✅ So'rovingiz qabul qilindi: <b>{title}</b>. Tez orada qo'shiladi!",
        "req_no": "❌ Afsuski, «{title}» so'rovi rad etildi.",
        "contact_prompt": "💬 Adminga xabaringizni yozing:", "contact_sent": "✅ Xabaringiz adminlarga yuborildi.",
        "admin_reply": "💬 <b>Admin javobi:</b>\n\n{text}",
        "hist_line": "{title} — {date} ({n} marta)",
        "recs_title": "⭐ <b>Siz uchun tavsiyalar</b>", "rec_pref": "🎭 Tanlagan janrlaringiz bo'yicha",
        "rec_hist": "🕘 Ko'rganlaringizga o'xshash", "rec_rand": "🎲 Tasodifiy tavsiyalar",
        "invite_text": "👥 <b>Do'st taklif qilish</b>\n\nSizning havolangiz:\n<code>{link}</code>\n\n✅ Tasdiqlangan takliflar: <b>{ok}</b>\n⏳ Kutilayotgan: <b>{wait}</b>\n🎁 Har {every} ta tasdiqlangan taklif uchun {days} kun VIP beriladi.",
        "ref_joined": "🎉 Siz taklif qilgan do'st botga qo'shildi!", "ref_reward": "🎁 Taklif uchun mukofot: +{days} kun VIP!",
        "help_text": "❓ <b>Yordam</b>\n\n🔑 Kino kodini yuboring — kino keladi.\n🔍 Nom bilan qidirish uchun «Kino qidirish».\n❤️ Yoqqan kinolarni sevimlilarga qo'shing.\n👑 VIP kontent uchun VIP obuna oling.\n✉️ Topilmagan kinoni «Kino so'rash» orqali so'rang.\n💬 Savollar uchun adminga yozing.\n\n/start — bosh menyu\n/cancel — bekor qilish",
        "settings_title": "⚙️ <b>Sozlamalar</b>", "set_lang": "🌐 Til", "set_genres": "🎭 Sevimli janrlar",
        "set_promo": "🎁 Promo-kod", "set_vip": "👑 VIP holati", "set_admin": "🛠 Admin panel",
        "genres_pick": "🎭 Yoqtirgan janrlaringizni belgilang (tavsiyalar uchun):",
        "promo_prompt": "🎁 Promo-kodni yuboring:", "promo_ok": "✅ Promo-kod faollashdi: +{days} kun VIP!",
        "promo_bad": "❌ Promo-kod noto'g'ri, muddati o'tgan yoki ishlatilgan.",
        "news_empty": "📰 Hozircha yangilik yo'q.", "news_btn": "📢 Kanalga o'tish",
        "random_title": "🎲 Tasodifiy kino", "again": "🎲 Yana",
        "back": "⬅️", "next": "➡️", "watch": "▶️ Tomosha qilish", "trailer": "🎞 Treyler",
        "add_fav": "🤍 Sevimlilarga", "rem_fav": "💔 Sevimlilardan olish", "buy_vip": "👑 VIP olish",
        "seasons": "📋 Qismlar", "open_app": "📱 Mini App", "cancel": "❌ Bekor qilish",
        "cancelled": "❌ Bekor qilindi.", "locked": "🔒", "watched": "✅",
        "f_code": "Kod", "f_country": "Davlat", "f_genre": "Janr", "f_duration": "Davomiyligi",
        "f_age": "Yosh", "f_imdb": "IMDb", "f_views": "Ko'rishlar", "f_vip": "VIP",
        "season": "{n}-fasl", "episode": "{n}-qism", "no_access": "⛔ Ruxsat yo'q.",
        "error": "⚠️ Xatolik yuz berdi. Qayta urinib ko'ring.", "only_text": "Matn yuboring.",
        "movie_label": "🎬", "series_label": "📺",
    },
    "ru": {
        "menu_search": "Поиск фильма", "menu_favorites": "Избранное", "menu_vip": "VIP фильмы",
        "menu_genres": "Жанры", "menu_series": "Сериалы", "menu_cartoons": "Мультфильмы",
        "menu_random": "Случайный фильм", "menu_stats": "Статистика", "menu_request": "Заказать фильм",
        "menu_history": "История просмотров", "menu_recs": "Рекомендации", "menu_language": "Сменить язык",
        "menu_news": "Новости", "menu_invite": "Пригласить друга", "menu_help": "Помощь",
        "menu_contact": "Связь с админом", "menu_settings": "Настройки",
        "welcome": "👋 Привет, <b>{name}</b>!\n\n🎬 Добро пожаловать в кино-бот.\n🔑 Отправьте <b>код</b> фильма — он придёт сразу.\n🔍 Или напишите название.",
        "menu_hint": "Выберите в меню 👇",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Язык изменён.",
        "sub_required": "📢 Чтобы пользоваться ботом, подпишитесь на каналы ниже и нажмите «Проверить подписку»:",
        "sub_check": "✅ Проверить подписку",
        "sub_not_yet": "❌ Вы ещё не подписались на все каналы!",
        "sub_ok": "✅ Спасибо! Подписка подтверждена.",
        "banned": "🚫 Вам закрыт доступ к боту.",
        "not_found": "😔 Фильм с таким кодом или названием не найден.\n\nПроверьте код или воспользуйтесь поиском по названию.",
        "search_prompt": "🔍 Напишите <b>название</b> или <b>код</b> фильма:",
        "search_results": "🔍 Результаты по «{q}»:",
        "empty": "📭 Пока пусто.",
        "fav_added": "❤️ Добавлено в избранное", "fav_removed": "💔 Удалено из избранного",
        "fav_title": "❤️ <b>Избранное</b>", "hist_title": "🕘 <b>История просмотров</b>",
        "vip_locked": "👑 Это <b>VIP</b> контент. Нужна VIP подписка.",
        "vip_on": "👑 VIP активен до <b>{date}</b> (осталось {days} дн.)",
        "vip_off": "👑 У вас нет VIP подписки.",
        "vip_title": "👑 <b>VIP фильмы</b>",
        "vip_buy": "💳 {days} дн. — {stars} ⭐",
        "vip_no_plans": "Оплата пока не настроена. Свяжитесь с админом.",
        "vip_thanks": "🎉 Оплата принята! VIP активен до {date}.",
        "vip_expired": "⌛ Срок вашей VIP подписки истёк.",
        "genres_title": "🎭 Выберите жанр:", "series_title": "📺 <b>Сериалы</b>",
        "cartoons_title": "🧸 <b>Мультфильмы</b>", "seasons_title": "📋 Выберите сезон:",
        "episodes_title": "▶️ Выберите серию:", "genre_list": "🎭 <b>{name}</b>",
        "stats_title": "📊 <b>Статистика</b>", "total_movies": "🎞 Всего фильмов: <b>{n}</b>",
        "st_all": "🏆 TOP 10", "st_today": "📅 Сегодня", "st_week": "🗓 Неделя", "st_month": "📆 Месяц", "st_vip": "👑 VIP TOP",
        "req_prompt": "✉️ Напишите название нужного фильма (и год, если знаете):",
        "req_sent": "✅ Ваш запрос отправлен админам.",
        "req_ok": "✅ Запрос принят: <b>{title}</b>. Скоро добавим!",
        "req_no": "❌ К сожалению, запрос «{title}» отклонён.",
        "contact_prompt": "💬 Напишите сообщение админу:", "contact_sent": "✅ Сообщение отправлено админам.",
        "admin_reply": "💬 <b>Ответ админа:</b>\n\n{text}",
        "hist_line": "{title} — {date} ({n} раз)",
        "recs_title": "⭐ <b>Рекомендации для вас</b>", "rec_pref": "🎭 По вашим любимым жанрам",
        "rec_hist": "🕘 Похожее на просмотренное", "rec_rand": "🎲 Случайные рекомендации",
        "invite_text": "👥 <b>Пригласить друга</b>\n\nВаша ссылка:\n<code>{link}</code>\n\n✅ Подтверждённых приглашений: <b>{ok}</b>\n⏳ В ожидании: <b>{wait}</b>\n🎁 За каждые {every} подтверждённых — {days} дн. VIP.",
        "ref_joined": "🎉 Приглашённый вами друг присоединился к боту!", "ref_reward": "🎁 Награда за приглашения: +{days} дн. VIP!",
        "help_text": "❓ <b>Помощь</b>\n\n🔑 Отправьте код фильма — он придёт.\n🔍 Для поиска по названию — «Поиск фильма».\n❤️ Добавляйте понравившиеся в избранное.\n👑 Для VIP контента нужна VIP подписка.\n✉️ Нет фильма? Закажите через «Заказать фильм».\n💬 Вопросы — пишите админу.\n\n/start — главное меню\n/cancel — отмена",
        "settings_title": "⚙️ <b>Настройки</b>", "set_lang": "🌐 Язык", "set_genres": "🎭 Любимые жанры",
        "set_promo": "🎁 Промокод", "set_vip": "👑 Статус VIP", "set_admin": "🛠 Админ панель",
        "genres_pick": "🎭 Отметьте любимые жанры (для рекомендаций):",
        "promo_prompt": "🎁 Отправьте промокод:", "promo_ok": "✅ Промокод активирован: +{days} дн. VIP!",
        "promo_bad": "❌ Промокод неверный, просрочен или уже использован.",
        "news_empty": "📰 Пока новостей нет.", "news_btn": "📢 Перейти в канал",
        "random_title": "🎲 Случайный фильм", "again": "🎲 Ещё",
        "back": "⬅️", "next": "➡️", "watch": "▶️ Смотреть", "trailer": "🎞 Трейлер",
        "add_fav": "🤍 В избранное", "rem_fav": "💔 Убрать из избранного", "buy_vip": "👑 Купить VIP",
        "seasons": "📋 Серии", "open_app": "📱 Mini App", "cancel": "❌ Отмена",
        "cancelled": "❌ Отменено.", "locked": "🔒", "watched": "✅",
        "f_code": "Код", "f_country": "Страна", "f_genre": "Жанр", "f_duration": "Длительность",
        "f_age": "Возраст", "f_imdb": "IMDb", "f_views": "Просмотры", "f_vip": "VIP",
        "season": "Сезон {n}", "episode": "Серия {n}", "no_access": "⛔ Нет доступа.",
        "error": "⚠️ Произошла ошибка. Попробуйте ещё раз.", "only_text": "Отправьте текст.",
        "movie_label": "🎬", "series_label": "📺",
    },
}


def t(lang: str, key: str, **kw) -> str:
    lang = lang if lang in T else "uz"
    text = T[lang].get(key) or T["uz"].get(key) or key
    return text.format(**kw) if kw else text


def menu_label(lang: str, key: str) -> str:
    return t(lang, f"menu_{key}")


def menu_key(text: str):
    """Tugma matnidan menyu kalitini topadi (emoji bilan yoki emojisiz)."""
    if not text:
        return None
    text = text.strip()
    for lang in T:
        for key, fb in MENU:
            label = T[lang][f"menu_{key}"]
            if text == label or text == f"{fb} {label}":
                return key
    return None


def is_menu_text(text: str) -> bool:
    return menu_key(text) is not None
