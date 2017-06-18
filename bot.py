from pprint import pprint
from string import punctuation
from telepot import Bot, glance
from telepot.helper import Answerer
from telepot.namedtuple import InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultCachedSticker, \
    Sticker

from utils import PersistedDict

with open('token') as t:
    token = t.read().strip()

bot = Bot(token)
answerer = Answerer(bot)
users = PersistedDict('data.json')


def register_user(user_id):
    changed = False
    with users.lock:
        if str(user_id) not in users.data:
            user_data = {'id': user_id, 'stickers': {}, 'words': {}, 'last_cmd': None, 'last_data': None, 'mode': True}
            users.data[str(user_id)] = user_data
            changed = True
    if changed:
        users.save()


def handle_cmd_help(chat_id, msg, text):
    bot.sendMessage(chat_id, 'This is very helpful help message')


def handle_cmd_start(chat_id, msg, text):
    if len(text.split()) > 1:
        users[chat_id]['mode'] = False
        users.save()
        handle_text(chat_id, msg, ' '.join(text.split()[1:]))
    else:
        handle_cmd_help(chat_id, msg, text)


CMDS = {'/start': handle_cmd_start}


def handle_cmd(chat_id, msg, text):
    cmd = text.split()[0]
    if cmd in CMDS:
        CMDS[cmd](chat_id, msg, text)
    else:
        handle_cmd_help(chat_id, msg, text)


def handle_text(chat_id, msg, text):
    user_data = users[chat_id]
    if user_data['mode']:
        sticker = user_data['last_data']
        if sticker is not None:
            update_user_data(sticker, text, user_data)
            answer = 'Keywords "{}" attached to last sticker'.format(text)
        else:
            answer = 'Send a sticker first'
    else:
        user_data['last_data'] = text
        answer = 'Now send some stickers you want to attach to this keywords'
    users[chat_id] = user_data
    users.save()
    bot.sendMessage(chat_id, answer)


def handle_sticker(chat_id, msg, sticker):
    user_data = users[chat_id]
    text = user_data['last_data']
    if not user_data['mode']:
        if text is not None:
            update_user_data(sticker, text, user_data)
            answer = 'Keywords "{}" attached to this sticker'.format(text)
        else:
            answer = 'Send keywords first'
    else:
        user_data['last_data'] = sticker
        answer = 'Now send some keywords you want to attach this sticker to'
    users[chat_id] = user_data
    users.save()
    bot.sendMessage(chat_id, answer)


def update_user_data(sticker, text, user_data):
    words = tokenize(text)
    stickers = user_data['stickers']
    if sticker in stickers:
        words.update(stickers[sticker])
    stickers[sticker] = list(words)

    user_words = user_data['words']
    for word in words:
        if word in user_words and sticker not in user_words[word]:
            user_words[word].append(sticker)
        else:
            user_words[word] = [sticker]


def handler(msg):
    msg_type, chat_type, chat_id = glance(msg)
    if chat_type != 'private':
        bot.sendMessage(chat_id, 'For private chats only')
        return
    register_user(chat_id)
    if msg_type == 'text':
        text = msg['text']
        if text.startswith('/'):
            handle_cmd(chat_id, msg, text)
        else:
            handle_text(chat_id, msg, text)
    elif msg_type == 'sticker':
        sticker_file_id = msg['sticker']['file_id']
        handle_sticker(chat_id, msg, sticker_file_id)
    else:
        bot.sendMessage(chat_id, 'чооо')
        # pprint(users[chat_id])


def get_user_stickers(user_id, query):
    words = tokenize(query)
    stickers = users[user_id]['words']
    return [sticker for word in words if word in stickers for sticker in stickers[word]]


def tokenize(query):
    return set(map(lambda x: x.strip(punctuation), query.lower().split()))


def inline_handler(msg):
    def compute():
        query_id, from_id, query_string = glance(msg, flavor='inline_query')

        ans = get_user_stickers(from_id, query_string)
        print(query_string, ans)
        if len(ans) > 0:
            articles = [InlineQueryResultCachedSticker(id=str(i), sticker_file_id=st,
                                                       input_message_content=Sticker(file_id=st))
                        for i, st in enumerate(ans)]
        else:
            articles = [InlineQueryResultArticle(id='1', title='You didnt add any stickers for any of this keywords',
                                                 input_message_content=InputTextMessageContent(message_text='???'))]
            return {'results': [], 'switch_pm_text': 'Add this keyword',
                    'switch_pm_parameter': query_string if len(query_string) else 'lol',
                    'cache_time': 0}

        return {'results': articles, 'is_personal': True, 'cache_time': 0}

    answerer.answer(msg, compute)


def main():
    bot.message_loop({'chat': handler, 'inline_query': inline_handler}, run_forever=True)


if __name__ == '__main__':
    main()
