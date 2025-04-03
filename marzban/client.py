import base64
import json
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

from marzban_api_client.api.user import add_user, get_user, delete_expired_users
from marzban_api_client.models import UserCreate, UserCreateProxies, UserResponse, UserCreateInbounds, UserDataLimitResetStrategy
from marzban_api_client.types import Response

from loader import marzban_client

logger = logging.getLogger(__name__)
proxies = {
#    "vmess": {},
#    "vless": {
#        "flow": ""
#    },
#    "trojan": {},
    "shadowsocks": {
        "method": "chacha20-ietf-poly1305"
    }
}
proxies = UserCreateProxies.from_dict(proxies)

inbounds = UserCreateInbounds.from_dict({
    "Shadowsocks TCP": True
})

def expire_timestamp(expire: datetime):
    new_utc_timestamp = int(expire.timestamp())
    return new_utc_timestamp


async def create_user(sub_id: str, expire: datetime) -> bool:
    exp_timestamp = expire_timestamp(expire)
    user_data = UserCreate(
        username=sub_id,
        data_limit=0,
        data_limit_reset_strategy=UserDataLimitResetStrategy.NO_RESET,
        expire=exp_timestamp,
        inbounds=inbounds,
        proxies=proxies
    )

    logger.info("📤 Создание пользователя с данными:")
    logger.info(json.dumps(user_data.to_dict(), indent=2, ensure_ascii=False))

    client = await marzban_client.get_client()
    response: Response = add_user.sync_detailed(client=client, body=user_data)

    logger.info(f"📥 Ответ от Marzban: {response.status_code}")
    if response.status_code != 200:
        logger.warning(f"⚠️ Не удалось создать пользователя: {response.content}")
        return False

    return True


async def get_marz_user(sub_id: str) -> UserResponse:
    response: Response = await get_user.asyncio_detailed(sub_id,
                                                         client=await marzban_client.get_client())
    return response.parsed


async def get_user_links(sub_id: str) -> str:
    response: UserResponse = await get_marz_user(sub_id)
    keys = []
    logger.info("%s", response.links)
    for x in response.links:
        key_data = x.split('://')
        if key_data[0] == 'vmess':
            data = json.loads(base64.b64decode(key_data[1]).decode('utf-8'))
            keys.append(
                'Протокол: <b>{protocol_type}</b>\nКлюч: <pre>{access_key}</pre>'
                .format(protocol_type=f'VMESS {data["net"]}', access_key=x)
            )
        elif (key_data[0] == 'vless') or (key_data[0] == 'trojan'):
            parsed_url = urlparse(x)
            if key_data[0] == 'vless':
                query_params = parse_qs(parsed_url.query)
                keys.append(
                    'Протокол: <b>{protocol_type}</b>\nКлюч: <pre>{access_key}</pre>'
                    .format(protocol_type=f'VLESS {query_params["type"][0]}', access_key=x)
                )
            if key_data[0] == 'trojan':
                keys.append(
                    'Протокол: <b>{protocol_type}\n</b>Ключ: <pre>{access_key}</pre>'
                    .format(protocol_type=f'Trojan WS', access_key=x)
                )
        elif key_data[0] == 'ss':
            keys.append(
                'Протокол <b>{protocol_type}\n</b>Ключ: \n<pre lang="vpn">{access_key}</pre>'.format(
                    protocol_type='Shadowsocks', access_key=x))
    return "\n\n".join(keys)


async def delete_users():
    local_utc_time = datetime.utcnow()
    response: Response = await delete_expired_users.asyncio_detailed(expired_before=local_utc_time,
                                                                     client=await marzban_client.get_client())
    logger.info(f'DELETE USERS RESPONSE: {response.parsed}')
