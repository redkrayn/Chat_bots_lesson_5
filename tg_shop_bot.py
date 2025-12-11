import re
import requests

from io import BytesIO
from environs import Env

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from utils import setup_logging, launch_redis
from strapi_api_requests import get_products, get_or_create_cart, add_product_to_cart, get_cart_with_items, \
    clear_cart, create_strapi_user


def show_cart(update, context):
    query = update.callback_query
    query.answer()

    chat_id = query.message.chat_id
    strapi_token = context.bot_data['strapi_token']

    cart_id = get_or_create_cart(chat_id, strapi_token)

    cart = get_cart_with_items(cart_id, strapi_token)

    if not cart['data']['attributes']['cart_items']['data']:
        message = 'В корзине пуфто...'
        keyboard = [
            [InlineKeyboardButton('В меню', callback_data='back_to_menu')]
        ]
    else:
        message = 'Ваша корзина!\n\n'
        total_price = 0

        for item in cart['data']['attributes']['cart_items']['data']:
            product = item['attributes']['product']['data']
            product_name = product['attributes']['title']
            product_price = product['attributes']['price']

            message += f'• {product_name} - {product_price} руб.\n'
            total_price += product_price

        message += f'\nИтого: {total_price} руб.'

        keyboard = [
            [InlineKeyboardButton('Оплатить', callback_data='pay')],
            [InlineKeyboardButton('Очистить корзину', callback_data='clear_cart')],
            [InlineKeyboardButton('В меню', callback_data='back_to_menu')]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=chat_id,
        text=message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    query.delete_message()


def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton('Моя корзина', callback_data='my_cart')
        ],
    ]
    products = context.bot_data['products']

    for product in products['data']:

        button = InlineKeyboardButton(product['attributes']['title'], callback_data=product['id'])
        keyboard.append([button])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)

    return 'HANDLE_MENU'


def handle_menu(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'my_cart':
        show_cart(update, context)

        return 'HANDLE_CART'

    product_id = query.data
    products = context.bot_data['products']
    context.user_data['current_product_id'] = product_id

    base_url = 'http://localhost:1337/'

    for product in products['data']:
        if str(product['id']) == product_id:
            message = (
                f'{product['attributes']['title']} ({product['attributes']['price']} руб за кг.)\n\n'
                f'{product['attributes']['description']}'
            )

            response = requests.get(base_url + product['attributes']['picture']['data']['attributes']['url'])
            response.raise_for_status()

            keyboard = [
                [
                    InlineKeyboardButton('Добавить товар', callback_data='add_product'),
                ],
                [
                    InlineKeyboardButton('Моя корзина', callback_data='my_cart')
                ],
                [
                    InlineKeyboardButton('Назад', callback_data='back_to_menu')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=BytesIO(response.content),
                caption=message,
                reply_markup=reply_markup
            )

    query.delete_message()

    return 'HANDLE_DESCRIPTION'


def handle_description(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'back_to_menu':
        keyboard = [
            [
                InlineKeyboardButton('Моя корзина', callback_data='my_cart')
            ],
        ]

        products = context.bot_data['products']

        for product in products['data']:
            button = InlineKeyboardButton(product['attributes']['title'], callback_data=product['id'])
            keyboard.append([button])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.message.reply_text('Пожалуйста, выберите:', reply_markup=reply_markup)
        query.delete_message()

        return 'HANDLE_MENU'

    elif query.data == 'add_product':
        chat_id = query.message.chat_id
        strapi_token = context.bot_data['strapi_token']

        cart_id = get_or_create_cart(chat_id, strapi_token)
        product_id = context.user_data.get('current_product_id')

        add_product_to_cart(cart_id, product_id, strapi_token)
        query.message.reply_text('Товар успешно добавлен в корзину!')

        return 'HANDLE_DESCRIPTION'

    elif query.data == 'my_cart':
        show_cart(update, context)
        return 'HANDLE_CART'

    return 'HANDLE_DESCRIPTION'


def handle_cart(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'pay':
        query.delete_message()

        message = (
            'Для оформления заказа, пожалуйста, укажите вашу электронную почту.\n'
            'Наш менеджер свяжется с вами для подтверждения заказа и оплаты.'
        )

        keyboard = [
            [InlineKeyboardButton('Назад', callback_data='back_to_cart')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return 'WAITING_EMAIL'

    if query.data == 'clear_cart':
        chat_id = query.message.chat_id
        strapi_token = context.bot_data['strapi_token']

        cart_id = get_or_create_cart(chat_id, strapi_token)
        clear_cart(cart_id, strapi_token)

        query.delete_message()
        message = 'Корзина очищена!'

        keyboard = [
            [InlineKeyboardButton('В меню', callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return 'HANDLE_CART'

    elif query.data == 'back_to_menu':
        chat_id = query.message.chat_id

        keyboard = [
            [
                InlineKeyboardButton('Моя корзина', callback_data='my_cart')
            ],
        ]

        products = context.bot_data['products']

        for product in products['data']:
            button = InlineKeyboardButton(product['attributes']['title'], callback_data=product['id'])
            keyboard.append([button])

        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=chat_id,
            text='Please choose:',
            reply_markup=reply_markup
        )

        query.delete_message()

        return 'HANDLE_MENU'

    return 'HANDLE_CART'


def handle_email(update, context):
    if update.callback_query:
        query = update.callback_query
        query.answer()

        if query.data == 'back_to_cart':
            show_cart(update, context)
            return 'HANDLE_CART'

    elif update.message:
        user_email = update.message.text.strip()
        chat_id = update.message.chat_id
        strapi_token = context.bot_data['strapi_token']
        cart_id = get_or_create_cart(chat_id, strapi_token)

        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

        if re.match(email_pattern, user_email):
            create_strapi_user(user_email, chat_id, cart_id, strapi_token)

            keyboard = [
                [InlineKeyboardButton('В меню', callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                'Ваш email сохранен!\n\n'
                'Позже с вами свяжутся наши менеджеры!.',
                reply_markup=reply_markup
            )

            return 'HANDLE_DESCRIPTION'
        else:
            update.message.reply_text(
                'Пожалуйста, введите корректный email адрес.\n'
                'Пример: example@domain.com'
            )

            return 'WAITING_EMAIL'


def handle_users_reply(update, context):
    db = context.bot_data['redis_db']

    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_email,
        'HANDLE_DESCRIPTION': handle_description
    }
    state_handler = states_functions[user_state]

    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


if __name__ == '__main__':
    env = Env()
    env.read_env()

    redis_host = env('REDIS_HOST', 'localhost')
    redis_port = env.int('REDIS_PORT', 6379)
    redis_password = env('REDIS_PASSWORD', None)
    redis_db = env.int('REDIS_DB', 0)

    telegram_bot_token = env('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = env('TELEGRAM_CHAT_ID')

    strapi_token = env('STRAPI_TOKEN')

    updater = Updater(telegram_bot_token)
    dp = updater.dispatcher

    dp.bot_data['redis_db'] = launch_redis(redis_host, redis_port, redis_password, redis_db)
    dp.bot_data['products'] = get_products(strapi_token)
    dp.bot_data['strapi_token'] = strapi_token

    logger_name = 'tg_echo_bot'
    logger = setup_logging(logger_name, updater.bot, telegram_chat_id)

    dp.add_handler(CallbackQueryHandler(handle_users_reply))
    dp.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dp.add_handler(CommandHandler('start', handle_users_reply))

    logger.info('Бот запущен')

    updater.start_polling()
    updater.idle()

