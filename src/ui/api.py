import os
import hmac
import hashlib
import json
import logging
from urllib.parse import parse_qsl

from aiohttp import web
from src.db.client import db_context
from src.db.queries import get_group, update_group, list_slots, add_slot, remove_slot

logger = logging.getLogger(__name__)

def validate_init_data(init_data: str, bot_token: str) -> bool:
    """Validate Telegram Web App init data."""
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return False
            
        received_hash = parsed_data.pop("hash")
        
        # Sort keys
        sorted_keys = sorted(parsed_data.keys())
        data_check_string = "\n".join(f"{k}={parsed_data[k]}" for k in sorted_keys)
        
        # Calculate secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_hash, received_hash)
    except Exception:
        logger.exception("Failed to validate init_data")
        return False

def verify_auth(request: web.Request) -> bool:
    """Extract and verify authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("tma "):
        return False
        
    init_data = auth_header[4:]
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return False
        
    # In a real app we might also decode the user data and verify the user
    # is an admin of the group. For this prototype we assume any valid TMA
    # token from our bot means the user clicked the inline button we sent them.
    return validate_init_data(init_data, bot_token)

async def get_group_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    if not group_id_str:
        return web.json_response({"error": "Missing group_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        async with db_context():
            group = await get_group(group_id)
            if not group:
                # Create the group row with defaults if it doesn't exist
                from src.db.queries import upsert_group
                await upsert_group(group_id)
                group = await get_group(group_id)
            
        if not group:
            return web.json_response({"error": "Group not found"}, status=404)
            
        group_dict = dict(group)
        
        # Add the OAuth URL so frontend can use it if disconnected
        from src.youtube.oauth import build_auth_url
        group_dict["yt_auth_url"] = build_auth_url(group_id)
            
        return web.json_response(group_dict)
    except ValueError:
        return web.json_response({"error": "Invalid group_id"}, status=400)
    except Exception as e:
        logger.exception("Failed to get group")
        return web.json_response({"error": str(e)}, status=500)

async def update_group_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    if not group_id_str:
        return web.json_response({"error": "Missing group_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        data = await request.json()
        
        async with db_context():
            await update_group(
                group_id,
                timezone=data.get("timezone"),
                reminder_hours=data.get("reminder_hours"),
                check_window_hours=data.get("check_window_hours"),
                auto_create=data.get("auto_create"),
                broadcast_privacy=data.get("broadcast_privacy"),
                broadcast_description=data.get("broadcast_description"),
                broadcast_made_for_kids=data.get("broadcast_made_for_kids")
            )
            
        return web.json_response({"status": "success"})
    except ValueError:
        return web.json_response({"error": "Invalid input"}, status=400)
    except Exception as e:
        logger.exception("Failed to update group")
        return web.json_response({"error": str(e)}, status=500)

async def get_slots_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    if not group_id_str:
        return web.json_response({"error": "Missing group_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        async with db_context():
            slots = await list_slots(group_id)
            
        return web.json_response([dict(s) for s in slots])
    except ValueError:
        return web.json_response({"error": "Invalid group_id"}, status=400)
    except Exception as e:
        logger.exception("Failed to get slots")
        return web.json_response({"error": str(e)}, status=500)

async def add_slot_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    if not group_id_str:
        return web.json_response({"error": "Missing group_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        data = await request.json()
        
        # Validations
        day_of_week = int(data.get("day_of_week", -1))
        local_time = data.get("local_time", "")
        title_template = data.get("title_template", "")
        custom_message = data.get("custom_message", "")
        
        if day_of_week < 0 or day_of_week > 6 or not local_time:
            return web.json_response({"error": "Invalid day or time"}, status=400)
            
        async with db_context():
            # The original add_slot uses (group_id, day_of_week, local_time, title_template)
            slot_id = await add_slot(group_id, day_of_week, local_time, title_template)
            if custom_message:
                from src.db.queries import update_slot
                await update_slot(slot_id, group_id, custom_message=custom_message)
            
        return web.json_response({"status": "success", "slot_id": slot_id})
    except ValueError:
        return web.json_response({"error": "Invalid input"}, status=400)
    except Exception as e:
        logger.exception("Failed to add slot")
        return web.json_response({"error": str(e)}, status=500)

async def delete_slot_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    slot_id_str = request.query.get("slot_id")
    
    if not group_id_str or not slot_id_str:
        return web.json_response({"error": "Missing group_id or slot_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        slot_id = int(slot_id_str)
        
        async with db_context():
            await remove_slot(slot_id, group_id)
            
        return web.json_response({"status": "success"})
    except ValueError:
        return web.json_response({"error": "Invalid input"}, status=400)
    except Exception as e:
        logger.exception("Failed to remove slot")
        return web.json_response({"error": str(e)}, status=500)

async def disconnect_youtube_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    if not group_id_str:
        return web.json_response({"error": "Missing group_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        async with db_context():
            await update_group(
                group_id,
                yt_access_token=None,
                yt_refresh_token=None,
                yt_token_expiry=None,
                yt_channel_id=None,
            )
            
        return web.json_response({"status": "success"})
    except ValueError:
        return web.json_response({"error": "Invalid group_id"}, status=400)
    except Exception as e:
        logger.exception("Failed to disconnect youtube")
        return web.json_response({"error": str(e)}, status=500)

async def get_streams_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    if not group_id_str:
        return web.json_response({"error": "Missing group_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        from src.db.queries import list_active_streams
        async with db_context():
            streams = await list_active_streams(group_id)
            
        return web.json_response([dict(s) for s in streams])
    except ValueError:
        return web.json_response({"error": "Invalid group_id"}, status=400)
    except Exception as e:
        logger.exception("Failed to get streams")
        return web.json_response({"error": str(e)}, status=500)

async def sync_youtube_handler(request: web.Request) -> web.Response:
    if not verify_auth(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    group_id_str = request.query.get("group_id")
    if not group_id_str:
        return web.json_response({"error": "Missing group_id"}, status=400)
        
    try:
        group_id = int(group_id_str)
        bot = request.app.get("bot")
        if not bot:
            return web.json_response({"error": "Bot instance not found"}, status=500)
            
        from src.engine import run_polling_cycle
        await run_polling_cycle(bot, group_id=group_id)
            
        return web.json_response({"status": "success"})
    except ValueError:
        return web.json_response({"error": "Invalid group_id"}, status=400)
    except Exception as e:
        logger.exception("Failed to sync youtube")
        return web.json_response({"error": str(e)}, status=500)

def setup_routes(app: web.Application) -> None:
    app.router.add_get('/api/group', get_group_handler)
    app.router.add_patch('/api/group', update_group_handler)
    app.router.add_get('/api/slots', get_slots_handler)
    app.router.add_post('/api/slots', add_slot_handler)
    app.router.add_delete('/api/slots', delete_slot_handler)
    app.router.add_post('/api/youtube/disconnect', disconnect_youtube_handler)
    app.router.add_get('/api/streams', get_streams_handler)
    app.router.add_post('/api/sync', sync_youtube_handler)
    
    # Serve static files for the UI
    ui_static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.router.add_static('/ui/', ui_static_dir, name='ui')
