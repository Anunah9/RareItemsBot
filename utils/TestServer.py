import requests


def get_item_float_and_stickers(inspect_link):
    url = 'http://192.168.0.14:80/'
    params_ = {
        'url': inspect_link
    }
    response = requests.get(url, params=params_)
    response = response.json()
    print(response)

    iteminfo = response['iteminfo']
    float_item = iteminfo['floatvalue']
    stickers = iteminfo['stickers']
    stickers_result = []
    for sticker in stickers:
        if 'wear' in sticker:
            continue
        stickers_result.append({'slot': sticker['slot'], 'name': 'Sticker | ' + sticker['name']})

    return float_item, stickers_result


if __name__ == '__main__':
    inspect_link = 'steam://rungame/730/76561202255233023/+csgo_econ_action_preview%20S76561198187797831A39443035501D4802781983538079519'
    get_item_float_and_stickers(inspect_link)