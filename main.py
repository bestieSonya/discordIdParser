import asyncio
import discord
import requests

intents = discord.Intents.all()
client = discord.Client(intents=intents)

DISCORD_SENSOR_API = "https://discord-sensor.com/api/functions/get-role-members"

def get_role_members(source_guild_id: str, role_id: str, page: int = 1, limit: int = 1000):
    url = f"{DISCORD_SENSOR_API}/{source_guild_id}/{role_id}"
    params = {"page": page, "limit": limit}
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка API запроса: {e}")
        return None


@client.event
async def on_ready():
    if client.user:
        print(f"✅ Бот запущен как {client.user} ({client.user.id})")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$start"):
        args = message.content.split()
        if len(args) != 4:
            await message.channel.send("Неверный формат команды.\nПример: `$start <source_guild_id> <role_id> <role_name>`")
            return

        source_guild_id = args[1]
        role_id = args[2]
        role_name = args[3]

        await message.channel.send(f"Получаю участников роли `{role_name}` из гильдии `{source_guild_id}`...")

        target_guild = message.guild
        if not target_guild:
            await message.channel.send("Не удалось определить гильдию назначения.")
            return

        data = get_role_members(source_guild_id, role_id)
        if not data or not data.get("success"):
            await message.channel.send("Не удалось получить участников роли.")
            return

        users = data.get("users", [])
        if not users:
            await message.channel.send("Нет пользователей в этой роли.")
            return

        await message.channel.send(f"Найдено {len(users)} участников. Создаю категории и каналы...")

        group_size = 50
        user_groups = [users[i:i + group_size] for i in range(0, len(users), group_size)]

        for index, group in enumerate(user_groups, start=1):
            suffix = f"_{index}" if len(user_groups) > 1 else ""
            category_name = f"role-{role_name}{suffix}"

            category = discord.utils.get(target_guild.categories, name=category_name)
            if not category:
                category = await target_guild.create_category_channel(category_name)
                print(f"Создана категория: {category_name}")
            else:
                print(f"Категория уже существует: {category_name}")

            for user_data in group:
                try:
                    user_id = int(user_data["id"])
                    username = user_data.get("username", "user")

                    member = target_guild.get_member(user_id)
                    channel_name = f"{username}-{user_id}"

                    existing_channel = discord.utils.get(category.text_channels, name=channel_name)
                    if existing_channel:
                        print(f"🔄 Канал уже есть: {channel_name}")
                        continue

                    overwrites = {
                        target_guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    }
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                    else:
                        print(f"⚠️ Участник {user_id} не найден на сервере.")

                    channel = await target_guild.create_text_channel(
                        name=channel_name,
                        category=category,
                        overwrites=overwrites,
                        reason=f"Канал для {username} из роли {role_id}",
                    )
                    print(f"✅ Создан канал: {channel.name}")

                    msg = await channel.send(
                        f"https://discord-tracker.com/tracker/user/{user_id}\n"
                        f"https://discord-sensor.com/members/{user_id}"
                    )
                    await msg.edit(suppress=True)

                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"❌ Ошибка при создании канала для {user_data}: {e}")

        await message.channel.send(f"✅ Все каналы для `{role_name}` созданы. Кто не воркает — тот лох 🐒")

if __name__ == "__main__":
    TOKEN = ""
    client.run(TOKEN)
    print("Debug ########### bot started")
