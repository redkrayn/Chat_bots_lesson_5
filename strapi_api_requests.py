import requests


def get_products(strapi_token):
    headers = {
        'Authorization': f'Bearer {strapi_token}'
    }
    params = {
        'populate': 'picture'
    }
    response = requests.get(
        f'http://localhost:1337/api/products',
        headers=headers,
        params=params
    )
    response.raise_for_status()

    return response.json()


def get_or_create_cart(chat_id, strapi_token):
    headers = {
        'Authorization': f'Bearer {strapi_token}'
    }

    params = {
        'filters[chat_id][$eq]': str(chat_id),
        'populate': 'cart_items'
    }

    response = requests.get(
        'http://localhost:1337/api/carts',
        headers=headers,
        params=params
    )
    response.raise_for_status()

    carts = response.json()

    if carts['data']:
        return carts['data'][0]['id']

    else:
        cart_data = {
            'data': {
                'chat_id': str(chat_id),
                'cart_items': []
            }
        }

        response = requests.post(
            'http://localhost:1337/api/carts',
            headers=headers,
            json=cart_data
        )
        response.raise_for_status()

        cart = response.json()
        return cart['data']['id']


def add_product_to_cart(cart_id, product_id, strapi_token):
    headers = {
        'Authorization': f'Bearer {strapi_token}',
    }

    cart_item_data = {
        'data': {
            'product': product_id,
            'cart': cart_id
        }
    }

    response = requests.post(
        'http://localhost:1337/api/cart-items',
        headers=headers,
        json=cart_item_data
    )
    response.raise_for_status()

    return response.json()


def get_cart_with_items(cart_id, strapi_token):
    headers = {
        'Authorization': f'Bearer {strapi_token}'
    }

    params = {
        'populate[cart_items][populate]': 'product'
    }

    response = requests.get(
        f'http://localhost:1337/api/carts/{cart_id}',
        headers=headers,
        params=params
    )
    response.raise_for_status()

    return response.json()


def clear_cart(cart_id, strapi_token):
    cart = get_cart_with_items(cart_id, strapi_token)
    cart_items = cart['data']['attributes']['cart_items']['data']

    headers = {
        'Authorization': f'Bearer {strapi_token}',
    }

    for item in cart_items:
        response = requests.delete(
            f'http://localhost:1337/api/cart-items/{item['id']}',
            headers=headers
        )
        response.raise_for_status()

    return True


def create_strapi_user(email, chat_id, cart_id, strapi_token):
    url = 'http://localhost:1337/api/users'

    headers = {
        'Authorization': f'Bearer {strapi_token}',
        'Content-Type': 'application/json'
    }

    data = {
        'username': str(chat_id),
        'email': email,
        'password': str(chat_id),
        'confirmed': True,
        'blocked': False,
        'cart': cart_id,
        'role': 1
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    return response.json()


